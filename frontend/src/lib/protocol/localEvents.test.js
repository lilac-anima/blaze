import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { createIdentityStore } from '../identity/identityStore.js';
import { createMemoryReplicaStore } from '../local/replicaStore.js';
import { createProfileEvent } from './profileEvents.js';
import { createPostEvent } from './postEvents.js';
import { appendLocalEvent } from '../local/localFirst.js';

if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

test('profile and post events are signed and exclude private key material', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const profile = await createProfileEvent(identity, { display_name: 'Dusty' });
  const post = await createPostEvent(identity, { content: 'hello', visibility: 'public' });
  assert.equal(profile.event_type, 'profile.updated');
  assert.equal(post.event_type, 'post.created');
  assert.ok(profile.signature && post.signature);
  assert.equal(JSON.stringify(profile).includes('privateKey'), false);
});

test('local append immediately projects profile and post, while rejected events are quarantined', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const store = createMemoryReplicaStore();
  const profile = await createProfileEvent(identity, { display_name: 'Dusty' });
  const post = await createPostEvent(identity, { content: 'hello' });
  const profileResult = await appendLocalEvent(store, profile);
  const postResult = await appendLocalEvent(store, post);
  assert.equal(profileResult.status, 'local');
  assert.equal(postResult.status, 'local');
  assert.equal((await store.getProjection('root')).posts[post.object_id].content, 'hello');
  const rejected = { ...post, event_id: 'bad' };
  const result = await appendLocalEvent(store, rejected);
  assert.equal(result.status, 'rejected');
  assert.equal((await store.getQuarantinedEvents()).length, 1);
});

test('local append works without network APIs', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const store = createMemoryReplicaStore();
  const post = await createPostEvent(identity, { content: 'offline' });
  const result = await appendLocalEvent(store, post);
  assert.equal(result.status, 'local');
});
