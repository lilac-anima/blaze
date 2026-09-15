import { friendshipObjectId, validateFriendEvent } from '../protocol/friendEvents.js';

function compare(a, b) {
  return a.created_at.localeCompare(b.created_at) || a.event_id.localeCompare(b.event_id);
}

function participants(request) {
  return [request.from_user_id, request.to_user_id].sort();
}

function hasActiveFriendship(state, userA, userB) {
  const id = friendshipObjectId(userA, userB);
  return state.friendships[id]?.status === 'active';
}

export function projectFriend(state, event) {
  const authorization = validateFriendEvent(event);
  if (!authorization.valid) return state;
  const payload = event.payload;
  const requests = state.friendRequests || {};
  const friendships = state.friendships || {};

  if (event.event_type === 'friend.requested') {
    const prior = requests[event.object_id];
    if (prior && compare(prior, event) >= 0) return state;
    if (hasActiveFriendship(state, payload.from_user_id, payload.to_user_id)) return state;
    return {
      ...state,
      friendRequests: {
        ...requests,
        [event.object_id]: {
          request_id: event.object_id,
          from_user_id: payload.from_user_id,
          to_user_id: payload.to_user_id,
          message: payload.message ?? null,
          status: 'pending',
          created_at: event.created_at,
          event_id: event.event_id,
        },
      },
    };
  }

  if (event.event_type === 'friend.accepted' || event.event_type === 'friend.rejected') {
    const request = requests[payload.request_id];
    if (!request || request.from_user_id !== payload.from_user_id || request.to_user_id !== payload.to_user_id) return state;
    if (request.status !== 'pending') return state;
    const status = event.event_type === 'friend.accepted' ? 'accepted' : 'rejected';
    const nextRequests = { ...requests, [payload.request_id]: { ...request, status, updated_at: event.created_at, event_id: event.event_id } };
    if (status === 'rejected') return { ...state, friendRequests: nextRequests };
    const friendshipId = friendshipObjectId(request.from_user_id, request.to_user_id);
    const current = friendships[friendshipId];
    if (current && current.status === 'removed') return { ...state, friendRequests: nextRequests };
    return {
      ...state,
      friendRequests: nextRequests,
      friendships: {
        ...friendships,
        [friendshipId]: {
          friendship_id: friendshipId,
          user_a: participants(request)[0],
          user_b: participants(request)[1],
          status: 'active',
          created_at: event.created_at,
          event_id: event.event_id,
        },
      },
    };
  }

  if (event.event_type === 'friend.removed') {
    const prior = friendships[event.object_id];
    if (!prior || prior.status !== 'active') return state;
    return {
      ...state,
      friendships: {
        ...friendships,
        [event.object_id]: { ...prior, status: 'removed', removed_at: event.created_at, event_id: event.event_id },
      },
    };
  }
  return state;
}

export function materializeFriends(state, userId) {
  return Object.values(state.friendships || {}).filter(friendship => friendship.status === 'active' && [friendship.user_a, friendship.user_b].includes(userId)).map(friendship => friendship.user_a === userId ? friendship.user_b : friendship.user_a);
}

export function materializePendingFriendRequests(state, userId, direction = 'incoming') {
  return Object.values(state.friendRequests || {}).filter(request => request.status === 'pending' && (direction === 'incoming' ? request.to_user_id === userId : request.from_user_id === userId));
}
