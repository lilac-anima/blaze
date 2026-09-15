import assert from 'node:assert/strict';
import test from 'node:test';

import { createMemoryReplicaStore } from '../local/replicaStore.js';
import { generateIdentity } from '../identity/identityStore.js';
import {
  createEventEvent,
  updateEventEvent,
  tombstoneEvent,
  createRsvpEvent,
  grantOrganizerEvent,
} from './eventEvents.js';
import { rebuild } from '../projections/projector.js';

const at = '2026-01-01T00:00:00.000Z';

test('event lifecycle and RSVP events are signed with object-scoped parents', async () => {
  const identity = await generateIdentity();
  const store = createMemoryReplicaStore();
  const created = await createEventEvent(identity, { id: 'event:1', name: 'Sunrise', date: '2026-09-01' }, store, at);
  const updated = await updateEventEvent(identity, created.object_id, { name: 'Sunset' }, store, [created.event_id], at);
  const rsvp = await createRsvpEvent(identity, created.object_id, 'going', store, [updated.event_id], at);
  const tombstone = await tombstoneEvent(identity, created.object_id, store, [updated.event_id], at);

  assert.equal(created.event_type, 'event.created');
  assert.deepEqual(updated.parents, [created.event_id]);
  assert.equal(rsvp.payload.attendee_id, identity.publicKey);
  assert.equal(tombstone.event_type, 'event.tombstoned');
  assert.notEqual(created.signature, updated.signature);
});

test('projection rejects unauthorized updates and organizer grants', async () => {
  const organizer = await generateIdentity();
  const stranger = await generateIdentity();
  const store = createMemoryReplicaStore();
  const created = await createEventEvent(organizer, { id: 'event:2', name: 'Campout', date: '2026-09-02' }, store, at);
  const unauthorized = await updateEventEvent(stranger, created.object_id, { name: 'Hijacked' }, store, [created.event_id], at);
  const strangerRsvp = await createRsvpEvent(stranger, created.object_id, 'going', store, [created.event_id], at);
  const grant = await grantOrganizerEvent(organizer, created.object_id, stranger.publicKey, store, [created.event_id, strangerRsvp.event_id], at);
  const authorized = await updateEventEvent(stranger, created.object_id, { name: 'Shared' }, store, [grant.event_id], at);

  const state = rebuild([created, unauthorized, strangerRsvp, grant, authorized]);
  assert.equal(state.events[created.object_id].name, 'Shared');
  assert.equal(state.events[created.object_id].organizers.includes(stranger.publicKey), true);
  assert.equal(state.events[created.object_id].rejected_event_ids.includes(unauthorized.event_id), true);
});

test('two memory peers exchange event lifecycle without duplicating projection', async () => {
  const identity = await generateIdentity();
  const a = createMemoryReplicaStore();
  const b = createMemoryReplicaStore();
  const created = await createEventEvent(identity, { id: 'event:3', name: 'Peer Event', date: '2026-09-03' }, a, at);
  const rsvp = await createRsvpEvent(identity, created.object_id, 'maybe', a, [created.event_id], at);
  await b.appendEvent(created);
  await b.appendEvent(rsvp);
  await b.appendEvent(rsvp);
  const state = rebuild([created, rsvp]);
  assert.equal(Object.keys(state.events).length, 1);
  assert.equal(state.events[created.object_id].rsvps[identity.publicKey].status, 'maybe');
  assert.equal(await b.hasEvent(rsvp.event_id), true);
});
