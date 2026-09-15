import assert from 'node:assert/strict';
import test from 'node:test';

import { generateIdentity } from '../identity/identityStore.js';
import { createEventEvent } from '../protocol/eventEvents.js';
import { createMemoryReplicaStore } from '../local/replicaStore.js';
import { createSyncEngine } from './syncEngine.js';

function connectedSessions() {
  const aHandlers = [];
  const bHandlers = [];
  const a = { send(message) { bHandlers.forEach(handler => handler(message)); }, onDataMessage(handler) { aHandlers.push(handler); return () => {}; } };
  const b = { send(message) { aHandlers.forEach(handler => handler(message)); }, onDataMessage(handler) { bHandlers.push(handler); return () => {}; } };
  return [a, b];
}

test('two peer sync engines validate and materialize a signed event', async () => {
  const identity = await generateIdentity();
  const aStore = createMemoryReplicaStore();
  const bStore = createMemoryReplicaStore();
  const event = await createEventEvent(identity, { id: 'event:network', name: 'Network event', date: '2026-09-04' }, aStore);
  await aStore.appendEvent(event);
  const [aSession, bSession] = connectedSessions();
  const a = createSyncEngine({ store: aStore, session: aSession, peerId: 'peer-b' });
  const b = createSyncEngine({ store: bStore, session: bSession, peerId: 'peer-a' });

  await a.start();
  await b.start();
  await new Promise(resolve => setTimeout(resolve, 50));

  assert.equal(await bStore.hasEvent(event.event_id), true, JSON.stringify(await bStore.getQuarantinedEvents()));
  assert.equal((await bStore.getQuarantinedEvents()).length, 0);
  a.close();
  b.close();
});
