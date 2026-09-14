export function materializeFeed(state, { limit = 50 } = {}) {
  return Object.values(state.posts || {}).sort((a,b) => b.created_at.localeCompare(a.created_at) || b.event_id.localeCompare(a.event_id)).slice(0, Math.max(0, Math.min(500, limit)));
}
