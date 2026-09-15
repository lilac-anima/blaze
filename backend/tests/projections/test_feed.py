from datetime import datetime

from backend.app.protocol.events import Event
from backend.app.protocol.identity import generate_identity
from backend.app.projections.feed import FeedProjection, project_feed


def event(identity, event_type, object_id, created_at, payload):
    return Event.create(identity, event_type, object_id, created_at, payload)


def test_feed_is_deterministic_and_deduplicates_replayed_events():
    identity = generate_identity()
    events = [
        event(identity, "post.created", "post-b", "2026-01-01T00:00:02Z", {"author_id": "alice", "content": "B", "visibility": "public"}),
        event(identity, "post.created", "post-a", "2026-01-01T00:00:02Z", {"author_id": "alice", "content": "A", "visibility": "public"}),
    ]
    projection = FeedProjection(events + [events[0]])

    first = projection.feed_for("viewer", limit=20)
    second = projection.feed_for("viewer", limit=20)

    assert [item["post_id"] for item in first] == ["post-a", "post-b"]
    assert first == second
    assert len(first) == 2


def test_feed_filters_social_camp_group_and_private_visibility():
    identity = generate_identity()
    events = [
        event(identity, "friend.accepted", "friendship-1", "2026-01-01T00:00:00Z", {"user_a": "viewer", "user_b": "friend"}),
        event(identity, "camp.membership.added", "camp-member-1", "2026-01-01T00:00:00Z", {"camp_id": "camp-1", "user_id": "viewer"}),
        event(identity, "post.created", "public", "2026-01-01T00:00:01Z", {"author_id": "stranger", "content": "public", "visibility": "public"}),
        event(identity, "post.created", "social", "2026-01-01T00:00:02Z", {"author_id": "friend", "content": "social", "visibility": "social"}),
        event(identity, "post.created", "camp", "2026-01-01T00:00:03Z", {"author_id": "stranger", "content": "camp", "visibility": "camp", "camp_id": "camp-1"}),
        event(identity, "post.created", "private", "2026-01-01T00:00:04Z", {"author_id": "stranger", "content": "private", "visibility": "private"}),
    ]

    ids = [item["post_id"] for item in project_feed(events, "viewer")]

    assert ids == ["camp", "social", "public"]


def test_feed_applies_updates_and_tombstones_and_cursor():
    identity = generate_identity()
    events = [
        event(identity, "post.created", "post-1", "2026-01-01T00:00:01Z", {"author_id": "viewer", "content": "old", "visibility": "public"}),
        event(identity, "post.updated", "post-1", "2026-01-01T00:00:02Z", {"content": "new"}),
        event(identity, "post.created", "post-2", "2026-01-01T00:00:03Z", {"author_id": "viewer", "content": "second", "visibility": "public"}),
    ]

    items = project_feed(events, "viewer", limit=1)
    assert items[0]["post_id"] == "post-2"
    assert items[0]["content"] == "second"
    assert project_feed(events, "viewer", cursor=items[0]["sort_key"])[0]["post_id"] == "post-1"

    deleted = events + [event(identity, "post.tombstoned", "post-1", "2026-01-01T00:00:04Z", {})]
    assert [item["post_id"] for item in project_feed(deleted, "viewer")] == ["post-2"]
