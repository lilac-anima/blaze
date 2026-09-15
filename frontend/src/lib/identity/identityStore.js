const keyring = new Map();
const encoder = new TextEncoder();
const toBase64 = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const fromBase64 = value => Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4)), c => c.charCodeAt(0));
const publicKeyId = publicKey => `did:key:z${publicKey}`;
const privateKeys = new WeakMap();

function defaultStorage() {
  if (typeof localStorage !== 'undefined') return localStorage;
  return new Map();
}
function get(storage, key) { return storage.get ? storage.get(key) : storage.getItem(key); }
function set(storage, key, value) { return storage.set ? storage.set(key, value) : storage.setItem(key, value); }

export async function generateIdentity() {
  const pair = await crypto.subtle.generateKey({ name: 'Ed25519' }, true, ['sign', 'verify']);
  const rawPublic = await crypto.subtle.exportKey('raw', pair.publicKey);
  const publicKey = toBase64(rawPublic);
  const keyRef = crypto.randomUUID();
  keyring.set(keyRef, pair.privateKey);
  const identity = Object.freeze({ id: publicKeyId(publicKey), publicKey, keyRef, createdAt: new Date().toISOString() });
  privateKeys.set(identity, pair.privateKey);
  return identity;
}

export function createIdentityStore({ storage = defaultStorage(), storageKey = 'burner.local.identity.v1' } = {}) {
  let current;
  return {
    async initialize() {
      if (current) return current;
      const saved = get(storage, storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        const privateKey = keyring.get(parsed.keyRef);
        if (privateKey) { current = Object.freeze(parsed); privateKeys.set(current, privateKey); return current; }
      }
      current = await generateIdentity();
      set(storage, storageKey, JSON.stringify(current));
      return current;
    },
    async rotate() {
      current = await generateIdentity();
      set(storage, storageKey, JSON.stringify(current));
      return current;
    },
    getCurrent() { return current; },
    getPrivateKey(identity = current) { return identity ? privateKeys.get(identity) || keyring.get(identity.keyRef) : undefined; },
  };
}

export async function exportPrivateKey(identity, store) {
  const key = store?.getPrivateKey(identity) || privateKeys.get(identity);
  if (!key) throw new Error('identity key is unavailable');
  return toBase64(await crypto.subtle.exportKey('pkcs8', key));
}

export { encoder, fromBase64, toBase64, privateKeys };
