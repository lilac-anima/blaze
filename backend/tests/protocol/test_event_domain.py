from backend.app.protocol.event_store import (
    AuthorizationError,
    EventProjector,
    EventStore,
    DuplicateEvent,
)
from backend.app.protocol.events import Event
from backend.app.protocol.identity import generate_identity


def make(identity, event_type, object_id, payload, created_at="2026-01-01T00:00:00Z", parents=()):
    return Event.create(identity, event_type, object_id, created_at, payload, parents)


def test_event_lifecycle_and_tombstone_projection():
    host = generate_identity()
    created = make(host, "event.created", "evt-1", {"name": "Sunrise", "date": "2026-09-01"})
    updated = make(host, "event.updated", "evt-1", {"name": "Sunset"}, "2026-01-01T00:00:01Z", (created.event_id,))
    deleted = make(host, "event.tombstoned", "evt-1", {"reason": "cancelled"}, "2026-01-01T00:00:02Z", (updated.event_id,))

    projection = EventProjector()
    for event in (created, updated, deleted):
        projection.apply(event)

    assert projection.events["evt-1"].name == "Sunset"
    assert projection.events["evt-1"].tombstoned is True
    assert projection.events["evt-1"].tombstone_reason == "cancelled"


def test_rsvp_and_scoped_organizer_authorization():
    host = generate_identity()
    guest = generate_identity()
    outsider = generate_identity()
    created = make(host, "event.created", "evt-2", {"name": "Dance", "date": "2026-09-02"})
    host_rsvp = make(host, "event.rsvp.updated", "evt-2", {"status": "going", "user_id": host.public_key_encoded()}, parents=(created.event_id,))
    guest_rsvp = make(guest, "event.rsvp.updated", "evt-2", {"status": "maybe", "user_id": guest.public_key_encoded()}, parents=(host_rsvp.event_id,))
    granted = make(host, "event.role.granted", "evt-2", {"user_id": guest.public_key_encoded(), "role": "organizer"}, parents=(guest_rsvp.event_id,))
    bad = make(outsider, "event.role.granted", "evt-2", {"user_id": outsider.public_key_encoded(), "role": "organizer"}, parents=(created.event_id,))

    projection = EventProjector()
    for event in (created, host_rsvp, guest_rsvp, granted):
        projection.apply(event)
    assert projection.events["evt-2"].rsvps[guest.public_key_encoded()] == "maybe"
    assert guest.public_key_encoded() in projection.events["evt-2"].organizers
    try:
        projection.apply(bad)
    except AuthorizationError:
        pass
    else:
        raise AssertionError("non-organizer granted a scoped role")


def test_store_is_idempotent_and_replicates_missing_signed_events():
    identity = generate_identity()
    event = make(identity, "event.created", "evt-3", {"name": "Campfire", "date": "2026-09-03"})
    source = EventStore()
    target = EventStore()
    assert source.append(event) == "accepted"
    assert source.append(event) == "duplicate"
    assert target.receive(source.export()) == {"accepted": 1, "duplicate": 0, "rejected": 0}
    assert target.projector.events["evt-3"].name == "Campfire"
    assert target.receive(source.export()) == {"accepted": 0, "duplicate": 1, "rejected": 0}


def test_out_of_order_events_wait_for_parent_and_then_apply():
    identity = generate_identity()
    created = make(identity, "event.created", "evt-4", {"name": "Art", "date": "2026-09-04"})
    update = make(identity, "event.updated", "evt-4", {"name": "Art 2"}, "2026-01-01T00:00:01Z", (created.event_id,))
    store = EventStore()
    assert store.receive([update.to_dict()]) == {"accepted": 0, "duplicate": 0, "rejected": 0}
    assert store.pending_ids == {update.event_id}
    assert store.receive([created.to_dict()]) == {"accepted": 2, "duplicate": 0, "rejected": 0}
    assert store.projector.events["evt-4"].name == "Art 2"
