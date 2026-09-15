"""Focused coverage for the SQLite compatibility persistence boundary."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.auth.utils import hash_password
from backend.app.database import SQLiteRepository, get_session
from backend.app.main import app
from backend.app.protocol.event_store import EventStore
from backend.app.protocol.events import Event
from backend.app.protocol.identity import generate_identity


@pytest.mark.asyncio
async def test_sqlite_repository_persists_auth_profile_and_event(tmp_path):
    repo = SQLiteRepository(str(tmp_path / "blaze.db"))
    await repo.create_user(user_id="u1", username="alice", email="a@example.test",
                           password_hash=hash_password("password"), created_at="now",
                           profile_id="p1", burner_name="Alice")
    assert (await repo.find_user("alice"))["user_id"] == "u1"
    assert (await repo.get_profile("u1"))["playa_name"] == "Alice"
    event = {"event_id": "e1", "type": "profile.updated", "author": "id1",
             "object_id": "u1", "created_at": "now", "payload": {}}
    assert await repo.append_event(event, "now") == "accepted"
    assert await repo.append_event(event, "now") == "duplicate"
    await repo.close()


@pytest.mark.asyncio
async def test_auth_routes_use_sqlite_repository(tmp_path):
    repo = SQLiteRepository(str(tmp_path / "routes.db"))

    async def override_session():
        yield repo

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            registered = await client.post("/api/auth/register", json={
                "email": "alice@example.test", "username": "alice",
                "burner_name": "Alice", "password": "password123",
            })
            assert registered.status_code == 201
            logged_in = await client.post("/api/auth/login", json={
                "login": "alice", "password": "password123",
            })
            assert logged_in.status_code == 200
            profile = await client.get("/api/users/me", headers={
                "Authorization": f"Bearer {logged_in.json()['access_token']}"
            })
            assert profile.status_code == 200
            assert profile.json()["burner"]["playa_name"] == "Alice"
    finally:
        app.dependency_overrides.pop(get_session, None)
        await repo.close()


@pytest.mark.asyncio
async def test_sqlite_identity_projection_and_event_reload(tmp_path):
    path = str(tmp_path / "reload.db")
    repo = SQLiteRepository(path)
    assert await repo.save_identity(identity_id="id1", public_key="pub1", created_at="now") == "accepted"
    await repo.save_projection("profile", "u1", {"username": "alice"}, "now")
    event = {"event_id": "e1", "type": "profile.updated", "author": "id1",
             "object_id": "u1", "created_at": "now", "payload": {"username": "alice"}}
    await repo.append_event(event, "now")
    await repo.close()

    reopened = SQLiteRepository(path)
    assert (await reopened.get_identity("pub1"))["identity_id"] == "id1"
    assert await reopened.get_projection("profile", "u1") == {"username": "alice"}
    assert (await reopened.list_events(object_id="u1"))[0]["event_id"] == "e1"
    tables = {row["name"] for row in reopened.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"identities", "signed_events", "projections", "graph_nodes"} <= tables
    await reopened.close()


@pytest.mark.asyncio
async def test_compatibility_writes_emit_replayable_event_and_projection():
    repo = SQLiteRepository(":memory:")
    result = await repo.run(
        "CREATE (e:Event {event_id: $event_id, name: $name, created_by: $created_by}) RETURN e",
        event_id="evt-1", name="Sunrise", created_by="u1",
    )
    assert (await result.single())["e"]["event_id"] == "evt-1"
    assert (await repo.list_events(object_id="evt-1"))[0]["type"] == "event.created"
    assert (await repo.get_projection("event", "evt-1"))["name"] == "Sunrise"
    await repo.close()


def test_protocol_event_store_uses_repository_and_reloads(tmp_path):
    path = str(tmp_path / "protocol.db")
    repo = SQLiteRepository(path)
    event = Event.create(generate_identity(), "event.created", "evt-protocol", "2026-01-01T00:00:00Z", {"name": "Protocol event"})
    store = EventStore(repository=repo)
    assert store.append(event) == "accepted"
    assert store.export()[0]["event_id"] == event.event_id
    assert repo.db.execute("SELECT 1 FROM projections WHERE projection='event' AND object_id='evt-protocol'").fetchone()
    store.close()
    import asyncio
    asyncio.run(repo.close())

    reopened = SQLiteRepository(path)
    reloaded = EventStore(repository=reopened)
    assert event.event_id in reloaded.projector.applied_ids
    assert reloaded.projector.events["evt-protocol"].name == "Protocol event"
    reloaded.close()
    asyncio.run(reopened.close())


@pytest.mark.asyncio
async def test_compatibility_update_and_delete_emit_durable_changes():
    repo = SQLiteRepository(":memory:")
    await repo.run(
        "CREATE (e:Event {event_id: $event_id, name: $name, created_by: $created_by}) RETURN e",
        event_id="evt-change", name="Before", created_by="u1",
    )
    await repo.run("MATCH (e:Event {event_id: $event_id}) SET e.name = $name", event_id="evt-change", name="After")
    await repo.run("MATCH (e:Event {event_id: $event_id}) DETACH DELETE e", event_id="evt-change")
    events = await repo.list_events(object_id="evt-change")
    assert [item["type"] for item in events] == ["event.created", "event.updated", "event.deleted"]
    assert events[-1]["payload"]["tombstoned"] is True
    assert (await repo.get_projection("event", "evt-change"))["tombstoned"] is True
    await repo.close()
