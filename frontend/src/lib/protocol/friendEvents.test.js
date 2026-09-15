import assert from 'node:assert/strict';
import test from 'node:test';
import { webcrypto } from 'node:crypto';

import { createIdentityStore } from '../identity/identityStore.js';
import { createMemoryReplicaStore } from '../local/replicaStore.js';
import { appendLocalEvent } from '../local/localFirst.js';
import { rebuild } from '../projections/projector.js';
import { createSyncEngine } from '../sync/syncEngine.js';
import {
  createFriendAcceptedEvent,
  createFriendRejectedEvent,
  createFriendRemovedEvent,
  createFriendRequestEvent,
  friendshipObjectId,
  validateFriendEvent,
} from './friendEvents.js';

if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

function session() {
  const handlers = [];
  return {
    sent: [],
    send(value) { this.sent.push(value); },
    onDataMessage(handler) { handlers.push(handler); return () => handlers.splice(handlers.indexOf(handler), 1); },
    deliver(value) { return Promise.all(handlers.map(handler => handler(value))); },
  };
}

async function identities() {
  const a = await createIdentityStore({ storage: new Map() }).initialize();
  const b = await createIdentityStore({ storage: new Map() }).initialize();
  return { a, b };
}

test('friend event authorship is scoped to the relationship actor', async () => {
  const { a, b } = await identities();
  const request = await createFriendRequestEvent(a, { toUserId: b.id });
  assert.equal(validateFriendEvent(request).valid, true);
  assert.equal(validateFriendEvent({ ...request, payload: { ...request.payload, from_user_id: b.id } }).valid, false);

  const accepted = await createFriendAcceptedEvent(b, { requestId: request.object_id, fromUserId: a.id });
  assert.equal(validateFriendEvent(accepted).valid, true);
  assert.equal(validateFriendEvent({ ...accepted, author: a.publicKey }).valid, false);
});

test('friend projection merges request, accept, reject, and removal deterministically', async () => {
  const { a, b } = await identities();
  const request = await createFriendRequestEvent(a, { toUserId: b.id, message: 'hello' });
  const accepted = await createFriendAcceptedEvent(b, { requestId: request.object_id, fromUserId: a.id });
  const removed = await createFriendRemovedEvent(a, { userA: a.id, userB: b.id });
  const state = rebuild([removed, accepted, request]);
  const friendshipId = friendshipObjectId(a.id, b.id);
  assert.equal(state.friendRequests[request.object_id].status, 'accepted');
  assert.equal(state.friendships[friendshipId].status, 'removed');

  const rejectedRequest = await createFriendRequestEvent(b, { toUserId: a.id });
  const rejected = await createFriendRejectedEvent(a, { requestId: rejectedRequest.object_id, fromUserId: b.id });
  assert.equal(rebuild([rejectedRequest, rejected]).friendRequests[rejectedRequest.object_id].status, 'rejected');
});

test('friend removal cannot target a different friendship than its participants', async () => {
  const { a, b } = await identities();
  const friendshipId = friendshipObjectId(a.id, b.id);
  const request = await createFriendRequestEvent(a, { toUserId: b.id });
  const accepted = await createFriendAcceptedEvent(b, { requestId: request.object_id, fromUserId: a.id });
  const removed = await createFriendRemovedEvent(a, { userA: a.id, userB: b.id });
  assert.throws(() => createFriendRemovedEvent(a, { userA: a.id, userB: b.id, friendshipId: 'friendship:unrelated' }), /does not match participants/);
  const forged = { ...removed, object_id: 'friendship:unrelated', payload: { ...removed.payload, friendship_id: 'friendship:unrelated' } };
  assert.equal(validateFriendEvent(forged).valid, false);
  assert.equal(rebuild([request, accepted, forged]).friendships[friendshipId].status, 'active');
});

test('two peers synchronize a signed friendship and rebuild the local read model', async () => {
  const { a, b } = await identities();
  const storeA = createMemoryReplicaStore();
  const storeB = createMemoryReplicaStore();
  const request = await createFriendRequestEvent(a, { toUserId: b.id });
  const accepted = await createFriendAcceptedEvent(b, { requestId: request.object_id, fromUserId: a.id });
  await appendLocalEvent(storeA, request);

  const sessionB = session();
  const engineB = createSyncEngine({ store: storeB, session: sessionB, peerId: 'a' });
  await engineB.start();
  await sessionB.deliver({ type: 'event_batch', cursor: request.event_id, events: [request] });
  assert.equal((await storeB.getProjection('root')).friendRequests[request.object_id].status, 'pending');

  await appendLocalEvent(storeB, accepted);
  const sessionA = session();
  const engineA = createSyncEngine({ store: storeA, session: sessionA, peerId: 'b' });
  await engineA.start();
  await sessionA.deliver({ type: 'event_batch', cursor: accepted.event_id, events: [accepted] });
  const friendshipId = friendshipObjectId(a.id, b.id);
  assert.equal((await storeA.getProjection('root')).friendships[friendshipId].status, 'active');
  engineA.close();
  engineB.close();
});
