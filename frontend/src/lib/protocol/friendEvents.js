import { signLocalEvent, newObjectId } from './localEvent.js';

export function identityId(author) { return `did:key:z${author}`; }

function requireIdentity(identity) {
  if (!identity?.id || !identity.publicKey) throw new Error('identity is unavailable');
}

export function createFriendRequestEvent(identity, { requestId = newObjectId('friend-request'), toUserId, message = null } = {}, store) {
  requireIdentity(identity);
  if (!toUserId || toUserId === identity.id) throw new Error('friend request recipient is invalid');
  return signLocalEvent(identity, {
    request_id: requestId,
    from_user_id: identity.id,
    to_user_id: toUserId,
    message,
  }, 'friend.requested', requestId, store);
}

export function createFriendAcceptedEvent(identity, { requestId, fromUserId, toUserId = identity.id } = {}, store) {
  requireIdentity(identity);
  if (!requestId || !fromUserId || toUserId !== identity.id) throw new Error('friend acceptance is invalid');
  return signLocalEvent(identity, {
    request_id: requestId,
    from_user_id: fromUserId,
    to_user_id: toUserId,
  }, 'friend.accepted', requestId, store);
}

export function createFriendRejectedEvent(identity, { requestId, fromUserId, toUserId = identity.id } = {}, store) {
  requireIdentity(identity);
  if (!requestId || !fromUserId || toUserId !== identity.id) throw new Error('friend rejection is invalid');
  return signLocalEvent(identity, {
    request_id: requestId,
    from_user_id: fromUserId,
    to_user_id: toUserId,
  }, 'friend.rejected', requestId, store);
}

export function friendshipObjectId(userA, userB) {
  if (!userA || !userB || userA === userB) throw new Error('friendship participants are invalid');
  return `friendship:${[userA, userB].sort().join(':')}`;
}

export function createFriendRemovedEvent(identity, { userA, userB, friendshipId = friendshipObjectId(userA, userB) } = {}, store) {
  requireIdentity(identity);
  if (friendshipId !== friendshipObjectId(userA, userB)) throw new Error('friendship ID does not match participants');
  if (![userA, userB].includes(identity.id)) throw new Error('only a friend can remove the friendship');
  return signLocalEvent(identity, {
    friendship_id: friendshipId,
    user_a: userA,
    user_b: userB,
    removed_by: identity.id,
  }, 'friend.removed', friendshipId, store);
}

export function validateFriendEvent(event) {
  if (!event || !event.event_type?.startsWith('friend.')) return { valid: true };
  const payload = event.payload || {};
  const authorId = identityId(event.author);
  const required = (fields) => fields.every(field => typeof payload[field] === 'string' && payload[field].length > 0);
  if (event.event_type === 'friend.requested') {
    if (!required(['request_id', 'from_user_id', 'to_user_id']) || payload.from_user_id !== authorId || payload.from_user_id === payload.to_user_id || event.object_id !== payload.request_id) return { valid: false, reason: 'unauthorized friend request' };
  } else if (event.event_type === 'friend.accepted' || event.event_type === 'friend.rejected') {
    if (!required(['request_id', 'from_user_id', 'to_user_id']) || payload.to_user_id !== authorId || event.object_id !== payload.request_id) return { valid: false, reason: 'only the request recipient may change its state' };
  } else if (event.event_type === 'friend.removed') {
    let canonicalId;
    try { canonicalId = friendshipObjectId(payload.user_a, payload.user_b); } catch { return { valid: false, reason: 'invalid friendship participants' }; }
    if (!required(['friendship_id', 'user_a', 'user_b', 'removed_by']) || payload.friendship_id !== canonicalId || payload.removed_by !== authorId || ![payload.user_a, payload.user_b].includes(authorId) || event.object_id !== payload.friendship_id) return { valid: false, reason: 'only a friend may remove the friendship' };
  } else return { valid: false, reason: 'unsupported friend event' };
  return { valid: true };
}
