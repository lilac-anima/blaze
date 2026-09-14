import json
from pathlib import Path

import pytest

from backend.app.protocol.events import Event, EventValidationError
from backend.app.protocol.identity import generate_identity


def test_event_round_trip_and_deterministic_id() -> None:
    identity = generate_identity()
    event = Event.create(
        identity=identity,
        event_type="post.created",
        object_id="post-1",
        created_at="2026-01-01T00:00:00Z",
        payload={"body": "hello"},
    )
    parsed = Event.from_dict(event.to_dict())
    assert parsed.event_id == event.event_id
    assert parsed.verify()


def test_event_tampering_and_malformed_inputs_are_rejected() -> None:
    identity = generate_identity()
    event = Event.create(identity, "profile.updated", "profile-1", "2026-01-01T00:00:00Z", {"name": "A"})
    data = event.to_dict()
    data["payload"]["name"] = "B"
    with pytest.raises(EventValidationError):
        Event.from_dict(data).verify()
    missing = event.to_dict()
    del missing["signature"]
    with pytest.raises(EventValidationError):
        Event.from_dict(missing)


def test_event_rejects_unsupported_version_and_oversized_payload() -> None:
    identity = generate_identity()
    event = Event.create(identity, "post.created", "post-1", "2026-01-01T00:00:00Z", {"body": "x"})
    unsupported = event.to_dict()
    unsupported["protocol_version"] = 99
    with pytest.raises(EventValidationError):
        Event.from_dict(unsupported)
    oversized = event.to_dict()
    oversized["payload"] = {"body": "x" * 100_001}
    with pytest.raises(EventValidationError):
        Event.from_dict(oversized)


def test_published_vectors_are_accepted() -> None:
    vectors = json.loads(Path("protocol/test-vectors/events.json").read_text(encoding="utf-8"))
    valid = [item for item in vectors["vectors"] if item["expectation"] == "valid"]
    assert len(valid) >= 2
    for item in valid:
        assert Event.from_dict(item["event"]).verify()
