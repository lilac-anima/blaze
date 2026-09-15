"""Ephemeral WebRTC signaling coordination.

This service relays negotiation metadata only. It never stores or interprets
signed social events; peers exchange those over their authenticated data
channel after the WebRTC connection is established.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


SignalingType = Literal["join", "offer", "answer", "ice", "leave"]


class SocketSender(Protocol):
    async def send_json(self, message: dict[str, Any]) -> None: ...


class SignalingEnvelope(BaseModel):
    """Bounded, routable WebRTC negotiation message."""

    model_config = ConfigDict(extra="forbid")

    type: SignalingType
    room_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    peer_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    target_peer_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_routing_and_payload(self) -> "SignalingEnvelope":
        if self.target_peer_id == self.peer_id:
            raise ValueError("target peer must differ from sender")
        if self.type in {"offer", "answer", "ice"} and not self.target_peer_id:
            raise ValueError("negotiation messages require a target peer")
        if self.type in {"join", "leave"} and self.payload:
            raise ValueError("join and leave messages cannot carry payloads")
        if _contains_social_event(self.payload):
            raise ValueError("signaling payload cannot contain social events")
        return self


class SignalingRoomManager:
    """In-memory room registry; room contents disappear when the process stops."""

    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, SocketSender]] = {}
        self._lock = asyncio.Lock()

    @property
    def room_count(self) -> int:
        return len(self._rooms)

    async def join(self, room_id: str, peer_id: str, sender: SocketSender) -> list[str]:
        async with self._lock:
            room = self._rooms.setdefault(room_id, {})
            existing = sorted(peer for peer in room if peer != peer_id)
            recipients = [room[peer] for peer in existing]
            room[peer_id] = sender
        await _send_all(recipients, {"type": "peer_joined", "peer_id": peer_id})
        return existing

    async def peers(self, room_id: str) -> list[str]:
        async with self._lock:
            return sorted(self._rooms.get(room_id, {}))

    async def leave(self, room_id: str, peer_id: str) -> None:
        async with self._lock:
            room = self._rooms.get(room_id)
            if not room:
                return
            room.pop(peer_id, None)
            recipients = list(room.values())
            if not room:
                self._rooms.pop(room_id, None)
        notification = {"type": "peer_left", "peer_id": peer_id}
        await _send_all(recipients, notification)

    async def relay(self, message: SignalingEnvelope) -> int:
        async with self._lock:
            room = self._rooms.get(message.room_id, {})
            if message.peer_id not in room:
                return 0
            if message.target_peer_id:
                recipients = [room[message.target_peer_id]] if message.target_peer_id in room else []
            else:
                recipients = [sender for peer, sender in room.items() if peer != message.peer_id]
        return await _send_all(recipients, message.model_dump(exclude_none=True))


async def _send_all(recipients: list[SocketSender], message: dict[str, Any]) -> int:
    delivered = 0
    for sender in recipients:
        try:
            await sender.send_json(message)
            delivered += 1
        except Exception:
            # A disconnect is cleaned up by the websocket owner.
            continue
    return delivered


def _contains_social_event(value: Any) -> bool:
    if isinstance(value, dict):
        if any(key in value for key in ("event", "events", "event_id", "author", "signature")):
            return True
        return any(_contains_social_event(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_social_event(item) for item in value)
    return False


signaling_manager = SignalingRoomManager()
