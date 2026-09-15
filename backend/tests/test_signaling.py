from dataclasses import dataclass

import pytest

from backend.app.sync.signaling import (
    SignalingEnvelope,
    SignalingRoomManager,
)


@dataclass
class FakeSocket:
    sent: list[dict]

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


@pytest.mark.asyncio
async def test_join_returns_current_peers_without_persisting_payloads():
    manager = SignalingRoomManager()
    first = FakeSocket([])
    second = FakeSocket([])

    assert await manager.join("room-1", "peer-a", first) == []
    assert await manager.join("room-1", "peer-b", second) == ["peer-a"]
    assert await manager.peers("room-1") == ["peer-a", "peer-b"]
    assert manager.room_count == 1


@pytest.mark.asyncio
async def test_join_notifies_existing_peers_when_a_peer_arrives():
    manager = SignalingRoomManager()
    first = FakeSocket([])
    second = FakeSocket([])

    await manager.join("room-1", "peer-a", first)
    await manager.join("room-1", "peer-b", second)

    assert first.sent == [{"type": "peer_joined", "peer_id": "peer-b"}]
    assert second.sent == []


@pytest.mark.asyncio
async def test_relay_targets_one_peer_and_does_not_send_to_sender():
    manager = SignalingRoomManager()
    first = FakeSocket([])
    second = FakeSocket([])
    await manager.join("room-1", "peer-a", first)
    await manager.join("room-1", "peer-b", second)
    first.sent.clear()
    second.sent.clear()

    message = SignalingEnvelope(
        type="offer",
        room_id="room-1",
        peer_id="peer-a",
        target_peer_id="peer-b",
        payload={"sdp": "opaque"},
    )
    delivered = await manager.relay(message)

    assert delivered == 1
    assert first.sent == []
    assert second.sent == [message.model_dump()]


@pytest.mark.asyncio
async def test_leave_notifies_remaining_peer_and_removes_empty_room():
    manager = SignalingRoomManager()
    first = FakeSocket([])
    second = FakeSocket([])
    await manager.join("room-1", "peer-a", first)
    await manager.join("room-1", "peer-b", second)
    first.sent.clear()
    second.sent.clear()

    await manager.leave("room-1", "peer-a")
    assert first.sent == []
    assert second.sent == [{"type": "peer_left", "peer_id": "peer-a"}]
    assert await manager.peers("room-1") == ["peer-b"]

    await manager.leave("room-1", "peer-b")
    assert manager.room_count == 0


def test_signaling_envelope_rejects_social_data_and_invalid_targets():
    with pytest.raises(ValueError):
        SignalingEnvelope(
            type="offer",
            room_id="room-1",
            peer_id="peer-a",
            target_peer_id="peer-a",
            payload={"event": {"event_id": "social-data"}},
        )

    with pytest.raises(ValueError):
        SignalingEnvelope(
            type="unknown",
            room_id="room-1",
            peer_id="peer-a",
            payload={},
        )
