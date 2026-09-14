from fastapi.testclient import TestClient

from backend.app.main import app


def test_signaling_websocket_joins_and_relays_negotiation_messages():
    with TestClient(app) as client:
        with client.websocket_connect("/sync/signaling/room-endpoint?peer_id=peer-a") as first:
            assert first.receive_json() == {
                "type": "joined",
                "peer_id": "peer-a",
                "peers": [],
            }
            with client.websocket_connect("/sync/signaling/room-endpoint?peer_id=peer-b") as second:
                assert second.receive_json() == {
                    "type": "joined",
                    "peer_id": "peer-b",
                    "peers": ["peer-a"],
                }
                second.send_json(
                    {
                        "type": "offer",
                        "target_peer_id": "peer-a",
                        "payload": {"sdp": "opaque"},
                    }
                )
                assert first.receive_json() == {
                    "type": "offer",
                    "room_id": "room-endpoint",
                    "peer_id": "peer-b",
                    "target_peer_id": "peer-a",
                    "payload": {"sdp": "opaque"},
                }


def test_signaling_websocket_rejects_social_event_payload():
    with TestClient(app) as client:
        with client.websocket_connect("/sync/signaling/room-invalid?peer_id=peer-a") as socket:
            socket.receive_json()
            socket.send_json(
                {
                    "type": "offer",
                    "target_peer_id": "peer-b",
                    "payload": {"event_id": "must-not-cross-signaling"},
                }
            )
            message = socket.receive()
            assert message["type"] == "websocket.close"
            assert message["code"] == 1008
