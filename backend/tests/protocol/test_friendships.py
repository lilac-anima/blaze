from __future__ import annotations

import pytest

from backend.app.protocol.events import Event, EventValidationError
from backend.app.protocol.friendships import (
    FriendshipProjection,
    FriendshipEventError,
    friend_event,
)
from backend.app.protocol.identity import generate_identity


CREATED = "2026-01-01T00:00:00Z"


def identities():
    return {name: generate_identity() for name in ("alice", "bob", "mallory")}


def test_request_accept_projects_friendship_and_authorization():
    keys = identities()
    projection = FriendshipProjection({name: identity.public_key_encoded() for name, identity in keys.items()})
    requested = friend_event(keys["alice"], "friend.requested", "request-1", CREATED, {
        "request_id": "request-1", "from_user_id": "alice", "to_user_id": "bob", "message": "hi",
    })
    accepted = friend_event(keys["bob"], "friend.accepted", "request-1", CREATED, {
        "request_id": "request-1", "from_user_id": "alice", "to_user_id": "bob",
    }, parents=(requested.event_id,))

    assert projection.apply(requested) == "applied"
    assert projection.apply(accepted) == "applied"
    assert projection.friends("alice") == {"bob"}
    assert projection.request_status("request-1") == "accepted"

    forged = friend_event(keys["mallory"], "friend.accepted", "request-1", CREATED, {
        "request_id": "request-1", "from_user_id": "alice", "to_user_id": "bob",
    })
    with pytest.raises(FriendshipEventError, match="recipient"):
        projection.apply(forged)


def test_rejected_request_does_not_create_friendship_and_removed_is_tombstone():
    keys = identities()
    projection = FriendshipProjection({name: identity.public_key_encoded() for name, identity in keys.items()})
    requested = friend_event(keys["alice"], "friend.requested", "request-2", CREATED, {
        "request_id": "request-2", "from_user_id": "alice", "to_user_id": "bob",
    })
    rejected = friend_event(keys["bob"], "friend.rejected", "request-2", CREATED, {
        "request_id": "request-2", "from_user_id": "alice", "to_user_id": "bob",
    })
    assert projection.apply(rejected) == "deferred"
    assert projection.apply(requested) == "applied"
    assert projection.apply(rejected) == "applied"
    assert projection.friends("alice") == set()
    assert projection.request_status("request-2") == "rejected"

    accepted = friend_event(keys["bob"], "friend.accepted", "request-3", CREATED, {
        "request_id": "request-3", "from_user_id": "alice", "to_user_id": "bob",
    })
    requested3 = friend_event(keys["alice"], "friend.requested", "request-3", CREATED, {
        "request_id": "request-3", "from_user_id": "alice", "to_user_id": "bob",
    })
    removed = friend_event(keys["alice"], "friend.removed", "friendship:alice:bob", CREATED, {
        "from_user_id": "alice", "to_user_id": "bob",
    })
    assert projection.apply(requested3) == "applied"
    assert projection.apply(accepted) == "applied"
    assert projection.apply(removed) == "applied"
    assert projection.friends("alice") == set()
    assert projection.friendship_status("alice", "bob") == "removed"


def test_tampered_or_wrong_author_events_are_rejected():
    keys = identities()
    projection = FriendshipProjection({name: identity.public_key_encoded() for name, identity in keys.items()})
    event = friend_event(keys["alice"], "friend.requested", "request-4", CREATED, {
        "request_id": "request-4", "from_user_id": "alice", "to_user_id": "bob",
    })
    data = event.to_dict()
    data["payload"]["from_user_id"] = "mallory"
    with pytest.raises(EventValidationError):
        projection.apply(Event.from_dict(data))


def test_two_replicas_merge_same_events_idempotently_out_of_order():
    keys = identities()
    key_map = {name: identity.public_key_encoded() for name, identity in keys.items()}
    a, b = FriendshipProjection(key_map), FriendshipProjection(key_map)
    requested = friend_event(keys["alice"], "friend.requested", "request-5", CREATED, {
        "request_id": "request-5", "from_user_id": "alice", "to_user_id": "bob",
    })
    accepted = friend_event(keys["bob"], "friend.accepted", "request-5", "2026-01-02T00:00:00Z", {
        "request_id": "request-5", "from_user_id": "alice", "to_user_id": "bob",
    }, parents=(requested.event_id,))
    for replica, events in ((a, (accepted, requested, accepted)), (b, (requested, accepted, requested))):
        for event in events:
            replica.apply(event)
    assert a.snapshot() == b.snapshot()
    assert a.friends("bob") == {"alice"}
