function rejected(state, event) {
  const current = state.events[event.object_id];
  return { ...state, events: { ...state.events, [event.object_id]: { ...current, rejected_event_ids: [...current.rejected_event_ids, event.event_id] } } };
}

function canOrganize(current, author) {
  return current?.organizers?.includes(author);
}

function applyEvent(state, event) {
  const current = state.events[event.object_id];
  if (event.event_type === 'event.created') {
    if (current) return state;
    return { ...state, events: { ...state.events, [event.object_id]: {
      ...event.payload, id: event.object_id, author: event.author, created_at: event.created_at,
      event_id: event.event_id, tombstoned: false, organizers: [event.author], rsvps: {}, rejected_event_ids: [],
    } } };
  }
  if (!current) return state;
  if (event.event_type === 'event.rsvp.updated' || event.event_type === 'rsvp.updated') {
    const attendee = event.payload.attendee_id || event.author;
    if (attendee !== event.author || !['going', 'maybe', 'not going'].includes(event.payload.status)) return rejected(state, event);
    return { ...state, events: { ...state.events, [event.object_id]: { ...current, rsvps: { ...current.rsvps, [attendee]: { status: event.payload.status, author: event.author, event_id: event.event_id, updated_at: event.created_at } } } } };
  }
  if (!canOrganize(current, event.author) || !event.parents?.includes(current.event_id)) return rejected(state, event);
  if (event.event_type === 'event.updated') {
    return { ...state, events: { ...state.events, [event.object_id]: { ...current, ...event.payload.changes, event_id: event.event_id, updated_at: event.created_at } } };
  }
  if (event.event_type === 'event.tombstoned') {
    return { ...state, events: { ...state.events, [event.object_id]: { ...current, tombstoned: true, tombstone_event_id: event.event_id, updated_at: event.created_at } } };
  }
  if (event.event_type === 'event.organizer.granted') {
    const attendee = event.payload.attendee_id;
    if (!attendee || !current.rsvps[attendee] || current.rsvps[attendee].status === 'not going') return rejected(state, event);
    return { ...state, events: { ...state.events, [event.object_id]: { ...current, event_id: event.event_id, organizers: [...new Set([...current.organizers, attendee])] } } };
  }
  if (event.event_type === 'event.organizer.revoked') {
    const attendee = event.payload.attendee_id;
    if (!attendee || attendee === current.author) return rejected(state, event);
    return { ...state, events: { ...state.events, [event.object_id]: { ...current, event_id: event.event_id, organizers: current.organizers.filter(id => id !== attendee) } } };
  }
  return state;
}

export function projectEvent(state, event) {
  const current = state.events[event.object_id];
  const next = applyEvent(state, event);
  if (next === state || !next.events[event.object_id]) return next;
  const projected = next.events[event.object_id];
  if (current && projected.rejected_event_ids === current.rejected_event_ids) return next;
  return next;
}