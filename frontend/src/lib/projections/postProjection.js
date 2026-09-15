function isNewer(previous, event) {
  return !previous || previous.created_at < event.created_at ||
    (previous.created_at === event.created_at && previous.event_id < event.event_id);
}

function materializePost(state, postId) {
  const post = state.posts[postId];
  if (!post) return state;
  const comments = Object.values(state.comments || {})
    .filter(comment => comment.post_id === postId)
    .sort((a, b) => a.created_at.localeCompare(b.created_at) || a.event_id.localeCompare(b.event_id));
  const reactions = Object.values(state.reactions || {})
    .filter(reaction => reaction.post_id === postId && reaction.liked);
  return { ...state, posts: { ...state.posts, [postId]: {
    ...post, comments, comment_count: comments.length,
    liked_by: reactions.map(reaction => reaction.author), like_count: reactions.length,
  } } };
}

export function projectPost(state, event) {
  if (state.posts[event.object_id]) return materializePost(state, event.object_id);
  const post = { ...event.payload, id: event.object_id, author: event.author,
    created_at: event.created_at, event_id: event.event_id, comments: [], comment_count: 0,
    liked_by: [], like_count: 0 };
  return materializePost({ ...state, posts: { ...state.posts, [event.object_id]: post } }, event.object_id);
}

export { isNewer, materializePost };
