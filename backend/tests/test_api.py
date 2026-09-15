"""SQLite-first API integration coverage."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.database import SQLiteRepository, get_session
from backend.app.main import app


@pytest.fixture
async def client():
    repo = SQLiteRepository(":memory:")

    async def override_session():
        yield repo

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_session, None)
        await repo.close()


async def register(client, username="alice", email="alice@example.test"):
    response = await client.post("/api/auth/register", json={
        "email": email,
        "username": username,
        "burner_name": username.title(),
        "password": "password123",
    })
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_health_is_ok_without_neo4j(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["neo4j_connected"] is False


@pytest.mark.asyncio
async def test_openapi_exposes_social_routes(client):
    paths = (await client.get("/openapi.json")).json()["paths"]
    for path in ("/events", "/camps", "/groups", "/posts", "/feed/{user_id}", "/users/{user_id}"):
        assert path in paths


@pytest.mark.asyncio
async def test_auth_register_login_and_profile_round_trip(client):
    await register(client)
    login = await client.post("/api/auth/login", json={"login": "alice", "password": "password123"})
    assert login.status_code == 200
    profile = await client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["burner"]["playa_name"] == "Alice"


@pytest.mark.asyncio
async def test_users_events_camps_groups_and_posts_crud(client):
    user = await client.post("/users?username=alice&email=alice@example.test")
    assert user.status_code == 201
    user_id = user.json()["user_id"]

    event = await client.post(f"/events?created_by={user_id}", json={"name": "Sunrise", "date": "2026-09-01"})
    assert event.status_code == 201
    assert (await client.get("/events")).json()[0]["event_id"] == event.json()["event_id"]

    camp = await client.post(f"/camps?created_by={user_id}", json={"name": "Dusty Camp"})
    assert camp.status_code == 201
    group = await client.post(f"/groups?created_by={user_id}", json={"name": "Artists"})
    assert group.status_code == 201

    post = await client.post("/posts", json={"author_id": user_id, "content": "hello playa"})
    assert post.status_code == 201
    post_id = post.json()["post_id"]
    updated = await client.patch(f"/posts/{post_id}", json={"content": "updated"})
    assert updated.status_code == 200
    assert (await client.get(f"/posts/{post_id}")).json()["content"] == "updated"
    assert (await client.delete(f"/posts/{post_id}")).status_code == 200
    assert (await client.get(f"/posts/{post_id}")).status_code == 404
    assert (await client.get(f"/camps/{camp.json()['camp_id']}")).status_code == 200
    assert (await client.get(f"/groups/{group.json()['group_id']}")).status_code == 200


@pytest.mark.asyncio
async def test_social_membership_and_reactions_persist(client):
    first = await client.post("/users?username=alice&email=alice@example.test")
    second = await client.post("/users?username=bob&email=bob@example.test")
    alice, bob = first.json()["user_id"], second.json()["user_id"]
    group = await client.post(f"/groups?created_by={alice}", json={"name": "Open", "is_public": True})
    group_id = group.json()["group_id"]
    assert (await client.post(f"/groups/{group_id}/join?user_id={bob}")).status_code == 200
    members = await client.get(f"/groups/{group_id}/members")
    assert members.status_code == 200
    assert len(members.json()) == 2

    post = await client.post("/posts", json={"author_id": alice, "content": "like me"})
    post_id = post.json()["post_id"]
    assert (await client.post(f"/posts/{post_id}/like?user_id={bob}")).status_code == 200
    assert (await client.get(f"/posts/{post_id}?current_user_id={bob}")).json()["is_liked_by_me"] is True


@pytest.mark.asyncio
async def test_missing_resources_return_not_found(client):
    for path in ("/users/missing", "/events/missing", "/camps/missing", "/groups/missing", "/posts/missing", "/feed/missing"):
        assert (await client.get(path)).status_code == 404
