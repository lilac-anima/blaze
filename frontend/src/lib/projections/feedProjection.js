const FRIEND_EVENT_TYPES = new Set(['friend.accepted', 'friendship.created', 'friend.created']);
const REMOVE_FRIEND_EVENT_TYPES = new Set(['friend.removed', 'friendship.removed', 'friend.deleted']);

function pair(a, b) { return [String(a), String(b)].sort().join('|'); }
function endpoint(payload, names) {
  for (const name of names) if (payload?.[name] != null) return payload[name];
  return null;
}
function relationshipFor(state, left, right) { return Boolean(state.relationships?.[pair(left, right)]); }
function membershipFor(state, viewer, scope) { return scope != null && Boolean(state.memberships?.[`${viewer}|${scope}`]); }

function canSee(post, state, viewerId) {
  const visibility = post.visibility || 'public';
  if (visibility === 'public') return true;
  if (!viewerId) return false;
  if (viewerId === post.author) return true;
  if (visibility === 'friends') return relationshipFor(state, viewerId, post.author);
  if (visibility === 'group' || visibility === 'camp') {
    return membershipFor(state, viewerId, post.group_id || post.camp_id || post.scope_id);
  }
  return false;
}

/** Apply graph membership/friend events without changing their wire schemas. */
export function projectFeedGraph(state, event) {
  if (typeof event.event_type !== 'string') return state;
  const payload = event.payload || {};
  const left = endpoint(payload, ['requester', 'from', 'user_id', 'author']);
  const right = endpoint(payload, ['recipient', 'to', 'peer_id', 'target_user_id']);
  if (FRIEND_EVENT_TYPES.has(event.event_type) && left != null && right != null) {
    return { ...state, relationships: { ...state.relationships, [pair(left, right)]: true } };
  }
  if (REMOVE_FRIEND_EVENT_TYPES.has(event.event_type) && left != null && right != null) {
    const relationships = { ...state.relationships };
    delete relationships[pair(left, right)];
    return { ...state, relationships };
  }
  if (event.event_type.endsWith('.member.added') || event.event_type === 'membership.created') {
    const member = endpoint(payload, ['member_id', 'user_id', 'subject']) || event.author;
    const scope = endpoint(payload, ['group_id', 'camp_id', 'scope_id', 'object_id']) || event.object_id;
    return { ...state, memberships: { ...state.memberships, [`${member}|${scope}`]: true } };
  }
  if (event.event_type.endsWith('.member.removed') || event.event_type === 'membership.removed') {
    const member = endpoint(payload, ['member_id', 'user_id', 'subject']) || event.author;
    const scope = endpoint(payload, ['group_id', 'camp_id', 'scope_id', 'object_id']) || event.object_id;
    const memberships = { ...state.memberships };
    delete memberships[`${member}|${scope}`];
    return { ...state, memberships };
  }
  return state;
}

export function materializeFeed(state, { viewerId = null, limit = 50 } = {}) {
  return Object.values(state.posts || {})
    .filter(post => canSee(post, state, viewerId))
    .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.event_id.localeCompare(a.event_id))
    .slice(0, Math.max(0, Math.min(500, limit)));
}
