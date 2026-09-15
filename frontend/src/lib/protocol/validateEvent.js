import { canonicalJson, utf8 } from './canonical.js';
import { validateFriendEvent } from './friendEvents.js';
const ID_RE = /^[A-Za-z0-9._:-]{1,256}$/;
export const MAX_EVENT_BYTES = 128000;
export const MAX_PAYLOAD_BYTES = 100000;
function decodeBase64(value) { if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value)) throw new Error('invalid encoding'); const raw = atob(value.replace(/-/g,'+').replace(/_/g,'/') + '='.repeat((4-value.length%4)%4)); return Uint8Array.from(raw, c=>c.charCodeAt(0)); }
async function sha256(value) { const bytes = new Uint8Array(await crypto.subtle.digest('SHA-256', utf8(canonicalJson(value)))); return [...bytes].map(x=>x.toString(16).padStart(2,'0')).join(''); }
export async function validateEvent(event, { now = Date.now(), maxClockSkewMs = 5 * 60 * 1000 } = {}) {
  try {
    const requiredKeys = ['author', 'created_at', 'event_id', 'event_type', 'object_id', 'payload', 'parents', 'protocol_version', 'signature'];
    if (!event || typeof event !== 'object' || Array.isArray(event) || Object.keys(event).sort().join(',') !== requiredKeys.slice().sort().join(',')) throw new Error('malformed event');
    if (event.protocol_version !== 1) throw new Error('unsupported protocol version');
    if (!ID_RE.test(event.event_id) || !ID_RE.test(event.event_type) || !ID_RE.test(event.object_id)) throw new Error('invalid identifier');
    if (!Array.isArray(event.parents) || event.parents.some(x => typeof x !== 'string' || !ID_RE.test(x)) || !event.payload || typeof event.payload !== 'object' || Array.isArray(event.payload)) throw new Error('invalid object format');
    const parsed = Date.parse(event.created_at); if (!Number.isFinite(parsed) || Math.abs(now - parsed) > maxClockSkewMs) throw new Error('timestamp outside policy');
    if (utf8(canonicalJson(event.payload)).byteLength > MAX_PAYLOAD_BYTES || utf8(canonicalJson(event)).byteLength > MAX_EVENT_BYTES) throw new Error('event exceeds size limit');
    const { event_id: ignored, signature: ignoredSignature, ...unsigned } = event;
    if (event.event_type === 'comment.created') {
      if (typeof event.payload.post_id !== 'string' || !ID_RE.test(event.payload.post_id) ||
          typeof event.payload.content !== 'string' || !event.payload.content.trim()) throw new Error('invalid comment payload');
    }
    if (event.event_type === 'post.liked' || event.event_type === 'post.unliked') {
      if (event.payload.post_id !== event.object_id) throw new Error('reaction target mismatch');
    }
    if (await sha256(unsigned) !== event.event_id) throw new Error('event ID mismatch');
    const key = await crypto.subtle.importKey('raw', decodeBase64(event.author), { name: 'Ed25519' }, false, ['verify']);
    const valid = await crypto.subtle.verify({ name: 'Ed25519' }, key, decodeBase64(event.signature), utf8(canonicalJson({ event_id: event.event_id, ...unsigned })));
    if (!valid) throw new Error('invalid signature');
    const authorization = validateFriendEvent(event);
    if (!authorization.valid) throw new Error(authorization.reason);
    return { valid: true, event };
  } catch (error) { return { valid: false, reason: error.message, event }; }
}
export async function validateAndStore(event, store, options) { const result = await validateEvent(event, options); if (result.valid) await store.appendEvent(event); else await store.quarantineEvent(event, result.reason); return result; }
