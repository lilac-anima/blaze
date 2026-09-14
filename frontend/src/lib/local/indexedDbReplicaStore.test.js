import test from 'node:test';
import assert from 'node:assert/strict';
import 'fake-indexeddb/auto';
import { createIndexedDbReplicaStore } from './indexedDbReplicaStore.js';

const event = (id, parents = []) => ({ event_id: id, event_type: 'post.created', object_id: id, parents, created_at: '2026-01-01T00:00:00Z' });
const dbName = () => `replica-test-${Date.now()}-${Math.random()}`;

test('IndexedDB persists events and cursors across store reopen', async () => {
  const name = dbName();
  const first = createIndexedDbReplicaStore(name);
  assert.equal(await first.appendEvent(event('one')), true);
  await first.setPeerCursor('peer', 'one');
  const second = createIndexedDbReplicaStore(name);
  assert.equal(await second.hasEvent('one'), true);
  assert.equal(await second.getPeerCursor('peer'), 'one');
});

test('IndexedDB append is duplicate-safe and reads are bounded after filtering', async () => {
  const store = createIndexedDbReplicaStore(dbName());
  assert.equal(await store.appendEvent(event('one')), true);
  assert.equal(await store.appendEvent(event('one')), false);
  await store.appendEvent(event('two'));
  assert.deepEqual((await store.getEventsAfter(null, { limit: 1 })).map(x => x.event_id), ['one']);
});

test('IndexedDB isolates quarantined events and reports missing parents', async () => {
  const store = createIndexedDbReplicaStore(dbName());
  await store.appendEvent(event('child', ['parent']));
  await store.quarantineEvent(event('bad'), 'invalid signature');
  assert.deepEqual(await store.getMissingParents(['child']), ['parent']);
  assert.deepEqual(await store.getEventsAfter(null), [event('child', ['parent'])]);
  assert.equal((await store.getQuarantinedEvents()).length, 1);
});
