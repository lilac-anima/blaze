import assert from 'node:assert/strict';
import test from 'node:test';

import { createSignalingTransport } from './signalingClient.js';

class FakeWebSocket {
  static instances = [];
  constructor(url) { this.url = url; this.sent = []; FakeWebSocket.instances.push(this); }
  send(value) { this.sent.push(value); }
  close() { this.readyState = 3; this.onclose?.(); }
  open() { this.readyState = 1; this.onopen?.(); }
  receive(value) { this.onmessage?.({ data: JSON.stringify(value) }); }
}

test('signaling transport connects, sends room-scoped messages, and receives messages', async () => {
  const transport = createSignalingTransport({
    url: 'ws://localhost:8000', roomId: 'room 1', peerId: 'peer-a', WebSocketImpl: FakeWebSocket,
  });
  const received = [];
  transport.onMessage(message => received.push(message));
  const connected = transport.connect();
  const socket = FakeWebSocket.instances.at(-1);
  assert.equal(socket.url, 'ws://localhost:8000/sync/signaling/room%201?peer_id=peer-a');
  socket.open();
  await connected;
  transport.send({ type: 'offer', target_peer_id: 'peer-b', payload: { type: 'offer' } });
  assert.deepEqual(JSON.parse(socket.sent[0]), { type: 'offer', target_peer_id: 'peer-b', payload: { type: 'offer' } });
  socket.receive({ type: 'joined', peers: [] });
  assert.deepEqual(received, [{ type: 'joined', peers: [] }]);
});

test('signaling transport rejects sends before connection', () => {
  const transport = createSignalingTransport({ url: 'ws://localhost:8000', roomId: 'room', peerId: 'peer' , WebSocketImpl: FakeWebSocket });
  assert.throws(() => transport.send({ type: 'leave' }), /not connected/);
});
