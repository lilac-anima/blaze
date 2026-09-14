import test from 'node:test';
import assert from 'node:assert/strict';
import { createMemoryReplicaStore } from './replicaStore.js';

test('replica store appends idempotently and reads bounded events', async () => {
  const store = createMemoryReplicaStore();
  const event = { event_id: 'e1', parents: [], created_at: '2026-01-01T00:00:00Z' };
  assert.equal(await store.appendEvent(event), true);
  assert.equal(await store.appendEvent(event), false);
  assert.deepEqual(await store.getEventsAfter(null, { limit: 1 }), [event]);
  assert.equal(await store.hasEvent('e1'), true);
});

test('replica store persists cursors and isolates quarantined events', async () => {
  const store = createMemoryReplicaStore();
  await store.setPeerCursor('peer-a', 'cursor-1');
  await store.quarantineEvent({ event_id: 'bad' }, 'invalid signature');
  assert.equal(await store.getPeerCursor('peer-a'), 'cursor-1');
  assert.deepEqual(await store.getEventsAfter(null), []);
  assert.equal((await store.getQuarantinedEvents()).length, 1);
});

test('replica store reports missing parents', async () => {
  const store = createMemoryReplicaStore();
  await store.appendEvent({ event_id: 'child', parents: ['parent'] });
  assert.deepEqual(await store.getMissingParents(['child']), ['parent']);
});
