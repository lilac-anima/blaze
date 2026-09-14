import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateAndStore, validateEvent } from './validateEvent.js';
import { createMemoryReplicaStore } from '../local/replicaStore.js';

if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });
const vectors = JSON.parse(await readFile(new URL('../../../../protocol/test-vectors/events.json', import.meta.url), 'utf8')).vectors;

test('browser validator accepts the published signed event vectors', async () => {
  for (const vector of vectors.filter(item => item.expectation === 'valid')) {
    assert.equal((await validateEvent(vector.event, { now: Date.parse('2026-01-01T00:00:00Z') })).valid, true, vector.name);
  }
});

test('browser validator rejects tampering and quarantines instead of appending', async () => {
  const valid = vectors.find(item => item.name === 'valid-post').event;
  const tampered = { ...valid, payload: { body: 'tampered' } };
  const store = createMemoryReplicaStore();
  const result = await validateAndStore(tampered, store, { now: Date.parse(valid.created_at) });
  assert.equal(result.valid, false);
  assert.equal(await store.hasEvent(valid.event_id), false);
  assert.equal((await store.getQuarantinedEvents()).length, 1);
});

test('browser validator enforces version, required fields, and timestamp policy', async () => {
  const valid = vectors.find(item => item.name === 'valid-post').event;
  assert.match((await validateEvent({ ...valid, protocol_version: 99 }, { now: Date.parse(valid.created_at) })).reason, /version/);
  const { signature, ...missing } = valid;
  assert.match((await validateEvent(missing, { now: Date.parse(valid.created_at) })).reason, /malformed/);
  assert.match((await validateEvent(valid, { now: Date.parse(valid.created_at) + 10 * 60 * 1000 })).reason, /timestamp/);
});
