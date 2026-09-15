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

test('restart replaces the connection without reporting a false disconnect', async () => {
  const transport = signaling();
  const states = [];
  const session = createPeerSession({ peerId: 'a', remotePeerId: 'b', transport, RTCPeerConnectionImpl: FakePeerConnection });
  session.onStateChange(state => states.push(state));
  const before = FakePeerConnection.instances.length;
  await session.start({ initiator: true });
  await session.restart({ initiator: true });
  assert.equal(FakePeerConnection.instances.length, before + 2);
  assert.equal(states.includes('disconnected'), false);
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

test('receiver queues ICE candidates that arrive before the offer', async () => {
  const transport = signaling();
  const session = createPeerSession({ peerId: 'b', remotePeerId: 'a', transport, RTCPeerConnectionImpl: FakePeerConnection });
  await session.start({ initiator: false });
  const connection = FakePeerConnection.instances.at(-1);

  transport.deliver({ type: 'ice', peer_id: 'a', target_peer_id: 'b', payload: { candidate: 'early-candidate' } });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(connection.candidate, undefined);

  transport.deliver({ type: 'offer', peer_id: 'a', target_peer_id: 'b', payload: { type: 'offer', sdp: 'remote-offer' } });
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(connection.candidate, { candidate: 'early-candidate' });
});

test('initiator renegotiates when the remote peer joins after startup', async () => {
  const transport = signaling();
  const session = createPeerSession({ peerId: 'a', remotePeerId: 'b', transport, RTCPeerConnectionImpl: FakePeerConnection });
  await session.start({ initiator: true });
  transport.sent.length = 0;

  transport.deliver({ type: 'peer_joined', peer_id: 'b' });
  await new Promise(resolve => setImmediate(resolve));

  assert.deepEqual(transport.sent[0], { type: 'offer', target_peer_id: 'b', payload: { type: 'offer', sdp: 'offer-sdp' } });
});

test('connection state does not report connected before the data channel opens', async () => {
  const transport = signaling();
  const states = [];
  const session = createPeerSession({ peerId: 'a', remotePeerId: 'b', transport, RTCPeerConnectionImpl: FakePeerConnection });
  session.onStateChange(state => states.push(state));
  await session.start({ initiator: true });

  const connection = FakePeerConnection.instances.at(-1);
  connection.connectionState = 'connected';
  connection.onconnectionstatechange();

  assert.equal(states.includes('connected'), false);
  session.channel.open();
  assert.equal(states.at(-1), 'connected');
});
