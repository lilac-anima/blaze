export function projectProfile(state, event) {
  const previous = state.profiles[event.object_id];
  if (previous && (previous.created_at > event.created_at || (previous.created_at === event.created_at && previous.event_id >= event.event_id))) return state;
  return { ...state, profiles: { ...state.profiles, [event.object_id]: { ...event.payload, id:event.object_id, created_at:event.created_at, event_id:event.event_id } } };
}
