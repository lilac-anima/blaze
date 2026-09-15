import { canonicalJson, utf8 } from './canonical.js';
import { toBase64, privateKeys } from '../identity/identityStore.js';

async function sha256(value) {
  const digest = await crypto.subtle.digest('SHA-256', utf8(canonicalJson(value)));
  return [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, '0')).join('');
}

export async function signLocalEvent(identity, payload, eventType, objectId, store, parents = [], options = {}) {
  const unsigned = { author: identity.publicKey, created_at: options.createdAt || new Date().toISOString(), event_type: eventType, object_id: objectId, parents, payload, protocol_version: 1 };
  const event_id = await sha256(unsigned);
  const privateKey = store?.getPrivateKey?.(identity) || privateKeys.get(identity);
  if (!privateKey) throw new Error('identity key is unavailable');
  const signature = await crypto.subtle.sign({ name: 'Ed25519' }, privateKey, utf8(canonicalJson({ event_id, ...unsigned })));
  return { ...unsigned, event_id, signature: toBase64(signature) };
}

export function newObjectId(prefix) { return `${prefix}:${crypto.randomUUID()}`; }
export { sha256 };
