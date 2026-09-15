import assert from 'node:assert/strict';
import test from 'node:test';
import { webcrypto } from 'node:crypto';

import { createMemoryReplicaStore } from '../local/replicaStore.js';
import { createIdentityStore } from '../identity/identityStore.js';
import { createPostEvent } from '../protocol/postEvents.js';
import { rebuildStore } from '../projections/projector.js';
import { materializeFeed } from '../projections/feedProjection.js';
import { createSyncEngine } from './syncEngine.js';

if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

function session() {
  const handlers = [];
  return {
    sent: [],
    send(value) { this.sent.push(value); },
    onDataMessage(handler) { handlers.push(handler); },
    deliver(value) { handlers.forEach(handler => handler(value)); },
  };
}

test('sync engine announces protocol and known event ids', async () => {
  const store = createMemoryReplicaStore();
  await store.appendEvent({ event_id: 'event-a', event_type: 'post.created' });
  const peer = session();
  const engine = createSyncEngine({ store, session: peer, peerId: 'peer-a' });

  await engine.start();

  assert.deepEqual(peer.sent, [{
    type: 'hello', protocol_version: 1, peer_id: 'peer-a', known_event_ids: ['event-a'], cursor: null,
  }]);
});

test('sync engine answers hello with bounded missing event batches', async () => {
  const store = createMemoryReplicaStore();
  await store.appendEvent({ event_id: 'event-a', event_type: 'post.created' });
  await store.appendEvent({ event_id: 'event-b', event_type: 'post.created' });
  const peer = session();
  const engine = createSyncEngine({ store, session: peer, peerId: 'peer-a', batchSize: 1 });

  await engine.start();
  peer.deliver({ type: 'hello', protocol_version: 1, peer_id: 'peer-b', known_event_ids: [], cursor: null });

  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(peer.sent[1], { type: 'event_batch', cursor: 'event-a', events: [{ event_id: 'event-a', event_type: 'post.created' }] });
});

test('two peer synchronization makes a received post available to the local feed projection', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const source = createMemoryReplicaStore();
  const target = createMemoryReplicaStore();
  const event = await createPostEvent(identity, { content: 'received', visibility: 'public' });
  await source.appendEvent(event);
  const sourcePeer = session();
  const targetPeer = session();
  const sourceEngine = createSyncEngine({ store: source, session: sourcePeer, peerId: 'source' });
  const targetEngine = createSyncEngine({ store: target, session: targetPeer, peerId: 'target' });
  await sourceEngine.start();
  await targetEngine.start();

  sourcePeer.deliver(targetPeer.sent[0]);
  await new Promise(resolve => setTimeout(resolve, 20));
  targetPeer.deliver(sourcePeer.sent[1]);
  await new Promise(resolve => setTimeout(resolve, 20));

  const projection = await rebuildStore(target);
  assert.deepEqual(materializeFeed(projection).map(item => item.content), ['received']);
});
