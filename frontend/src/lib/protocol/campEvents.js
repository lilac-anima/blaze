import { signLocalEvent, newObjectId } from './localEvent.js';

const campObject = (campId) => campId || newObjectId('camp');

export function createCampEvent(identity, camp, store) {
  const objectId = campObject(camp.id || camp.camp_id);
  return signLocalEvent(identity, { ...camp, created_by: camp.created_by || identity.publicKey }, 'camp.created', objectId, store);
}

export function updateCampEvent(identity, campId, changes, store) {
  return signLocalEvent(identity, { ...changes }, 'camp.updated', campId, store);
}

export function deleteCampEvent(identity, campId, reason, store) {
  return signLocalEvent(identity, { reason: reason || null }, 'camp.tombstoned', campId, store);
}

export function joinCampEvent(identity, campId, store) {
  return signLocalEvent(identity, { member_id: identity.publicKey }, 'camp.membership.added', campId, store);
}

export function leaveCampEvent(identity, campId, store) {
  return signLocalEvent(identity, { member_id: identity.publicKey }, 'camp.membership.removed', campId, store);
}

export function grantCampRoleEvent(identity, campId, memberId, role = 'moderator', store) {
  return signLocalEvent(identity, { member_id: memberId, role }, 'camp.role.granted', campId, store);
}

export function revokeCampRoleEvent(identity, campId, memberId, role = 'moderator', store) {
  return signLocalEvent(identity, { member_id: memberId, role }, 'camp.role.revoked', campId, store);
}
