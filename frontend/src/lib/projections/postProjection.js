export function projectPost(state, event) {
  if (state.posts[event.object_id]) return state;
  return { ...state, posts: { ...state.posts, [event.object_id]: { ...event.payload, id:event.object_id, author:event.author, created_at:event.created_at, event_id:event.event_id } } };
}
