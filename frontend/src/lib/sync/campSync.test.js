import assert from 'node:assert/strict';
import test from 'node:test';
import { webcrypto } from 'node:crypto';
import { createIdentityStore } from '../identity/identityStore.js';
import { createMemoryReplicaStore } from '../local/replicaStore.js';
import { appendLocalEvent } from '../local/localFirst.js';
import { createCampEvent } from '../protocol/campEvents.js';
import { createSyncEngine } from './syncEngine.js';

if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

function session() {
  const handlers = [];
  return { sent: [], send(value) { this.sent.push(value); }, onDataMessage(handler) { handlers.push(handler); }, deliver(value) { return Promise.all(handlers.map(handler => handler(value))); } };
}

test('two peer sync transfers a signed camp event into the remote projection', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const source = createMemoryReplicaStore();
  const remote = createMemoryReplicaStore();
  const event = await createCampEvent(identity, { name: 'Network Camp' });
  await appendLocalEvent(source, event);
  const sourcePeer = session();
  const remotePeer = session();
  const sourceEngine = createSyncEngine({ store: source, session: sourcePeer, peerId: 'remote' });
  const remoteEngine = createSyncEngine({ store: remote, session: remotePeer, peerId: 'source' });
  await sourceEngine.start();
  await remoteEngine.start();
  await remotePeer.deliver(sourcePeer.sent[0]);
  await sourcePeer.deliver(remotePeer.sent[0]);
  await remotePeer.deliver(sourcePeer.sent[1]);
  assert.equal((await remote.getProjection('root')).camps[event.object_id].name, 'Network Camp');
});
