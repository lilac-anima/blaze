import test from 'node:test';
import assert from 'node:assert/strict';
import { rebuild } from './projector.js';

const event = (event_type, event_id, object_id, author, payload, created_at) => ({
  event_type, event_id, object_id, author, payload, created_at, parents: [],
});

test('camp projection applies creation, membership, role changes, update and tombstone', () => {
  const owner = 'did:owner';
  const member = 'did:member';
  const camp = event('camp.created', 'e1', 'camp:one', owner, { owner_id: owner, name: 'Camp One' }, '2026-01-01T00:00:00Z');
  const joined = event('camp.member.joined', 'e2', 'camp:one', member, { member_id: member }, '2026-01-01T00:01:00Z');
  const granted = event('camp.role.granted', 'e3', 'camp:one', owner, { member_id: member, role: 'moderator' }, '2026-01-01T00:02:00Z');
  const updated = event('camp.updated', 'e4', 'camp:one', owner, { name: 'Camp Two' }, '2026-01-01T00:03:00Z');
  const left = event('camp.member.left', 'e5', 'camp:one', member, { member_id: member }, '2026-01-01T00:04:00Z');
  const state = rebuild([left, updated, granted, joined, camp]);
  assert.equal(state.camps['camp:one'].name, 'Camp Two');
  assert.equal(state.camps['camp:one'].members[member], undefined);
  assert.equal(state.camps['camp:one'].tombstoned, false);
});

test('camp projection ignores unauthorized mutations and converges regardless of delivery order', () => {
  const camp = event('camp.created', 'e1', 'camp:one', 'did:owner', { owner_id: 'did:owner', name: 'Camp One' }, '2026-01-01T00:00:00Z');
  const forged = event('camp.updated', 'e2', 'camp:one', 'did:other', { name: 'Forged' }, '2026-01-01T00:01:00Z');
  const tombstone = event('camp.tombstoned', 'e3', 'camp:one', 'did:owner', {}, '2026-01-01T00:02:00Z');
  const first = rebuild([forged, tombstone, camp]);
  const second = rebuild([camp, tombstone, forged]);
  assert.deepEqual(first, second);
  assert.equal(first.camps['camp:one'].name, 'Camp One');
  assert.equal(first.camps['camp:one'].tombstoned, true);
});
