const ROLE_ORDER = Object.freeze({ member: 0, moderator: 1, lead: 2 });
const UPDATE_FIELDS = ['name', 'description', 'location_on_playa', 'event_id'];

function copyCamp(camp) {
  return { ...camp, members: Object.fromEntries(Object.entries(camp.members || {}).map(([id, member]) => [id, { ...member }])) };
}
function isLead(camp, author) { return camp?.members?.[author]?.role === 'lead' || camp?.created_by === author; }
function targetMember(event) { return event.payload?.member_id || event.payload?.user_id; }

/** Return whether an event may mutate the current camp projection. */
export function isAuthorizedCampEvent(event, camp) {
  if (event.event_type === 'camp.created') return !camp && (event.payload?.created_by || event.payload?.owner_id) === event.author;
  if (!camp || camp.tombstoned) return false;
  const member = targetMember(event);
  switch (event.event_type) {
    case 'camp.updated':
    case 'camp.tombstoned':
      return isLead(camp, event.author);
    case 'camp.membership.added':
    case 'camp.membership.joined':
    case 'camp.member.joined':
      return member === event.author || isLead(camp, event.author);
    case 'camp.membership.removed':
    case 'camp.member.left':
      return member === event.author || isLead(camp, event.author);
    case 'camp.role.granted':
    case 'camp.role.revoked':
      return isLead(camp, event.author) && member !== camp.created_by;
    default:
      return false;
  }
}

export function projectCamp(state, event) {
  const camps = state.camps || {};
  const current = camps[event.object_id];
  if (!isAuthorizedCampEvent(event, current)) return state;
  if (event.event_type === 'camp.created') {
    const payload = event.payload || {};
    const createdBy = payload.created_by || payload.owner_id || event.author;
    const created = { ...payload, id: event.object_id, created_by: createdBy, created_at: event.created_at, event_id: event.event_id, tombstoned: false, members: { [createdBy]: { member_id: createdBy, role: 'lead', event_id: event.event_id, created_at: event.created_at } } };
    return { ...state, camps: { ...camps, [event.object_id]: created } };
  }
  const camp = copyCamp(current);
  const payload = event.payload || {};
  if (event.event_type === 'camp.updated') {
    for (const field of UPDATE_FIELDS) if (Object.prototype.hasOwnProperty.call(payload, field)) camp[field] = payload[field];
    camp.updated_at = event.created_at;
    camp.updated_event_id = event.event_id;
  } else if (event.event_type === 'camp.tombstoned') {
    camp.tombstoned = true;
    camp.tombstone_reason = payload.reason || null;
    camp.tombstone_event_id = event.event_id;
  } else if (event.event_type === 'camp.membership.added' || event.event_type === 'camp.membership.joined' || event.event_type === 'camp.member.joined') {
    const member = targetMember(event);
    if (!camp.members[member]) camp.members[member] = { member_id: member, role: 'member', event_id: event.event_id, created_at: event.created_at };
  } else if (event.event_type === 'camp.membership.removed' || event.event_type === 'camp.member.left') {
    delete camp.members[targetMember(event)];
  } else if (event.event_type === 'camp.role.granted') {
    const member = targetMember(event);
    if (camp.members[member] && ROLE_ORDER[payload.role] !== undefined && payload.role !== 'lead') camp.members[member] = { ...camp.members[member], role: payload.role, event_id: event.event_id, updated_at: event.created_at };
  } else if (event.event_type === 'camp.role.revoked') {
    const member = targetMember(event);
    if (camp.members[member] && camp.members[member].role === payload.role) camp.members[member] = { ...camp.members[member], role: 'member', event_id: event.event_id, updated_at: event.created_at };
  }
  return { ...state, camps: { ...camps, [event.object_id]: camp } };
}

export function materializeCamps(state) {
  return Object.values(state.camps || {}).filter(camp => !camp.tombstoned).map(camp => ({ ...camp, member_count: Object.keys(camp.members || {}).length }));
}
