import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { createIdentityStore } from './identityStore.js';
import { exportRecoveryBundle, importRecoveryBundle } from './recovery.js';

if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

test('first use creates a stable identity without exposing private key in public identity', async () => {
  const store = createIdentityStore({ storage: new Map() });
  const identity = await store.initialize();
  assert.match(identity.id, /^did:key:/);
  assert.equal(identity.privateKey, undefined);
  assert.equal((await store.initialize()).id, identity.id);
});

test('encrypted recovery round trips and rejects a wrong passphrase', async () => {
  const store = createIdentityStore({ storage: new Map() });
  const identity = await store.initialize();
  const bundle = await exportRecoveryBundle(identity, 'correct horse');
  const restored = await importRecoveryBundle(bundle, 'correct horse');
  assert.equal(restored.publicKey, identity.publicKey);
  await assert.rejects(() => importRecoveryBundle(bundle, 'wrong passphrase'));
});

test('rotating identity does not retain the old identity', async () => {
  const store = createIdentityStore({ storage: new Map() });
  const first = await store.initialize();
  const second = await store.rotate();
  assert.notEqual(second.id, first.id);
  assert.notEqual(second.publicKey, first.publicKey);
});
