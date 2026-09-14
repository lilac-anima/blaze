import { exportPrivateKey, fromBase64, toBase64 } from './identityStore.js';

const text = new TextEncoder();
const decode = bytes => new TextDecoder().decode(bytes);

async function derive(passphrase, salt) {
  const base = await crypto.subtle.importKey('raw', text.encode(passphrase), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: 210000, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}

export async function exportRecoveryBundle(identity, passphrase, store) {
  if (!passphrase || typeof passphrase !== 'string') throw new Error('passphrase is required');
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await derive(passphrase, salt);
  const plaintext = JSON.stringify({ version: 1, id: identity.id, publicKey: identity.publicKey, privateKey: await exportPrivateKey(identity, store) });
  const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, text.encode(plaintext));
  return { version: 1, algorithm: 'PBKDF2-AES-256-GCM', salt: toBase64(salt), iv: toBase64(iv), ciphertext: toBase64(ciphertext) };
}

export async function importRecoveryBundle(bundle, passphrase) {
  if (!bundle || bundle.version !== 1 || !passphrase) throw new Error('invalid recovery bundle');
  try {
    const key = await derive(passphrase, fromBase64(bundle.salt));
    const plaintext = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: fromBase64(bundle.iv) }, key, fromBase64(bundle.ciphertext));
    const value = JSON.parse(decode(plaintext));
    if (!value.id || !value.publicKey || !value.privateKey) throw new Error('invalid recovery payload');
    return value;
  } catch { throw new Error('unable to decrypt recovery bundle'); }
}

export const recoveryLimitations = 'Recovery restores the same local identity; device loss without an exported bundle requires identity rotation and does not link the old JWT account automatically.';
