"""WebSocket signaling endpoint for Phase 2 peer connections."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from backend.app.sync.signaling import SignalingEnvelope, signaling_manager

router = APIRouter(prefix="/sync", tags=["sync"])


@router.websocket("/signaling/{room_id}")
async def signaling_socket(websocket: WebSocket, room_id: str, peer_id: str) -> None:
    """Relay WebRTC negotiation messages without persisting social data."""
    await websocket.accept()
    joined = False
    try:
        peers = await signaling_manager.join(room_id, peer_id, websocket)
        joined = True
        await websocket.send_json({"type": "joined", "peer_id": peer_id, "peers": peers})
        while True:
            raw = await websocket.receive_json()
            try:
                message = SignalingEnvelope.model_validate({**raw, "room_id": room_id, "peer_id": peer_id})
            except (ValidationError, TypeError, ValueError):
                await websocket.close(code=1008, reason="invalid signaling message")
                return
            if message.type == "leave":
                return
            await signaling_manager.relay(message)
    except WebSocketDisconnect:
        return
    finally:
        if joined:
            await signaling_manager.leave(room_id, peer_id)
