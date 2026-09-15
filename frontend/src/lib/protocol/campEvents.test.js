import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { createIdentityStore } from '../identity/identityStore.js';
import { createCampEvent, updateCampEvent, deleteCampEvent, joinCampEvent, leaveCampEvent, grantCampRoleEvent, revokeCampRoleEvent } from './campEvents.js';

if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

test('camp event helpers create signed domain events with stable payloads', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const camp = await createCampEvent(identity, { name: 'Dust Camp' });
  assert.equal(camp.event_type, 'camp.created');
  assert.equal(camp.payload.created_by, identity.publicKey);
  assert.equal(camp.payload.name, 'Dust Camp');
  const update = await updateCampEvent(identity, camp.object_id, { name: 'New Camp' });
  assert.equal(update.event_type, 'camp.updated');
  const deleted = await deleteCampEvent(identity, camp.object_id, 'closed');
  assert.equal(deleted.event_type, 'camp.tombstoned');
  const joined = await joinCampEvent(identity, camp.object_id);
  assert.equal(joined.payload.member_id, identity.publicKey);
  const left = await leaveCampEvent(identity, camp.object_id);
  assert.equal(left.event_type, 'camp.membership.removed');
  const granted = await grantCampRoleEvent(identity, camp.object_id, 'member-key', 'moderator');
  assert.equal(granted.payload.role, 'moderator');
  const revoked = await revokeCampRoleEvent(identity, camp.object_id, 'member-key', 'moderator');
  assert.equal(revoked.event_type, 'camp.role.revoked');
});
