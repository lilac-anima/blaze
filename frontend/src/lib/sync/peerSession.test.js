import assert from 'node:assert/strict';
import test from 'node:test';

import { createPeerSession } from './peerSession.js';

class FakeChannel {
  constructor() { this.sent = []; this.readyState = 'connecting'; }
  send(value) { this.sent.push(value); }
  open() { this.readyState = 'open'; this.onopen?.(); }
  receive(value) { this.onmessage?.({ data: value }); }
  close() { this.readyState = 'closed'; this.onclose?.(); }
}

class FakePeerConnection {
  static instances = [];
  constructor() { this.channel = new FakeChannel(); this.localDescription = null; this.remoteDescription = null; FakePeerConnection.instances.push(this); }
  createDataChannel() { return this.channel; }
  async createOffer() { return { type: 'offer', sdp: 'offer-sdp' }; }
  async createAnswer() { return { type: 'answer', sdp: 'answer-sdp' }; }
  async setLocalDescription(value) { this.localDescription = value; }
  async setRemoteDescription(value) { this.remoteDescription = value; }
  async addIceCandidate(value) { this.candidate = value; }
  close() { this.connectionState = 'closed'; }
}

function signaling() {
  const handlers = [];
  return {
    sent: [],
    send(message) { this.sent.push(message); },
    onMessage(handler) { handlers.push(handler); return () => handlers.splice(handlers.indexOf(handler), 1); },
    deliver(message) { handlers.forEach(handler => handler(message)); },
  };
}

test('initiator creates an offer and sends bounded JSON data frames', async () => {
  const transport = signaling();
  const session = createPeerSession({ peerId: 'a', remotePeerId: 'b', transport, RTCPeerConnectionImpl: FakePeerConnection });
  await session.start({ initiator: true });
  assert.deepEqual(transport.sent[0], { type: 'offer', target_peer_id: 'b', payload: { type: 'offer', sdp: 'offer-sdp' } });
  const messages = [];
  session.onDataMessage(message => messages.push(message));
  session.channel.open();
  session.send({ type: 'hello', payload: { cursor: null } });
  assert.deepEqual(session.channel.sent, [JSON.stringify({ type: 'hello', payload: { cursor: null } })]);
  session.channel.receive(JSON.stringify({ type: 'hello', payload: { cursor: 'x' } }));
  assert.deepEqual(messages, [{ type: 'hello', payload: { cursor: 'x' } }]);
});

test('receiver answers offers and applies ICE candidates', async () => {
  const transport = signaling();
  const session = createPeerSession({ peerId: 'b', remotePeerId: 'a', transport, RTCPeerConnectionImpl: FakePeerConnection });
  await session.start({ initiator: false });
  transport.deliver({ type: 'offer', peer_id: 'a', target_peer_id: 'b', payload: { type: 'offer', sdp: 'remote-offer' } });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(FakePeerConnection.instances.at(-1).remoteDescription.sdp, 'remote-offer');
  assert.deepEqual(transport.sent.at(-1), { type: 'answer', target_peer_id: 'a', payload: { type: 'answer', sdp: 'answer-sdp' } });
  transport.deliver({ type: 'ice', peer_id: 'a', target_peer_id: 'b', payload: { candidate: 'candidate' } });
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(FakePeerConnection.instances.at(-1).candidate, { candidate: 'candidate' });
});
