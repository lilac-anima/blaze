import assert from 'node:assert/strict';
import test from 'node:test';

import { createMemoryReplicaStore } from '../local/replicaStore.js';
import { createSyncEngine } from './syncEngine.js';

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
