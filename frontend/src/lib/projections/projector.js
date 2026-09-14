import { projectProfile } from './profileProjection.js';
import { projectPost } from './postProjection.js';
export function applyEvent(state, event) {
  if (event.event_type === 'profile.updated' || event.event_type === 'profile.created') return projectProfile(state, event);
  if (event.event_type === 'post.created') return projectPost(state, event);
  return state;
}
export function rebuild(events) { return [...events].sort((a,b) => a.created_at.localeCompare(b.created_at) || a.event_id.localeCompare(b.event_id)).reduce(applyEvent, { profiles: {}, posts: {} }); }
export async function rebuildStore(store) { const events=[]; let cursor=null; for (;;) { const batch=await store.getEventsAfter(cursor,{limit:500}); if (!batch.length) break; events.push(...batch); cursor=batch.at(-1).event_id; if(batch.length<500) break; } const result=rebuild(events); await store.putProjection?.('root',result); return result; }
