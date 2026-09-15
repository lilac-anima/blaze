import { projectProfile } from './profileProjection.js';
import { isNewer, materializePost, projectPost } from './postProjection.js';
import { projectEvent } from './eventProjection.js';
import { projectFriend } from './friendshipProjection.js';
import { projectCamp } from './campProjection.js';
import { projectFeedGraph } from './feedProjection.js';

function projectComment(state, event) {
  const { post_id: postId, content } = event.payload || {};
  if (!postId || typeof content !== 'string' || !content.trim()) return state;
  const previous = state.comments?.[event.object_id];
  if (previous && !isNewer(previous, event)) return state;
  const comments = { ...(state.comments || {}), [event.object_id]: {
    id: event.object_id, post_id: postId, content, author: event.author,
    created_at: event.created_at, event_id: event.event_id,
  } };
  return materializePost({ ...state, comments }, postId);
}

function projectReaction(state, event) {
  const postId = event.payload?.post_id || event.object_id;
  if (postId !== event.object_id || !postId) return state;
  const key = `${postId}:${event.author}`;
  const previous = state.reactions?.[key];
  if (previous && !isNewer(previous, event)) return state;
  const reactions = { ...(state.reactions || {}), [key]: {
    post_id: postId, author: event.author, liked: event.event_type === 'post.liked',
    created_at: event.created_at, event_id: event.event_id,
  } };
  return materializePost({ ...state, reactions }, postId);
}

export function applyEvent(state, event) {
  let next = projectFeedGraph(state, event);
  if (event.event_type === 'profile.updated' || event.event_type === 'profile.created') return projectProfile(next, event);
  if (event.event_type === 'post.created') return projectPost(next, event);
  if (event.event_type === 'comment.created') return projectComment(next, event);
  if (event.event_type === 'post.liked' || event.event_type === 'post.unliked') return projectReaction(next, event);
  if (event.event_type.startsWith('friend.')) return projectFriend(next, event);
  if (event.event_type.startsWith('camp.')) return projectCamp(next, event);
  if (event.event_type.startsWith('event.') || event.event_type === 'rsvp.updated') return projectEvent(next, event);
  return next;
}

export function rebuild(events) {
  const unique = new Map(events.map(event => [event.event_id, event]));
  const ordered = [];
  const visiting = new Set();
  const visited = new Set();
  const visit = event => {
    if (!event || visited.has(event.event_id)) return;
    if (visiting.has(event.event_id)) return;
    visiting.add(event.event_id);
    for (const parent of [...(event.parents || [])].sort()) visit(unique.get(parent));
    visiting.delete(event.event_id);
    visited.add(event.event_id);
    ordered.push(event);
  };
  const priority = { 'friend.requested': 0, 'friend.accepted': 1, 'friend.rejected': 1, 'friend.removed': 2, 'camp.created': 0 };
  [...unique.values()].sort((a, b) => a.created_at.localeCompare(b.created_at) || (priority[a.event_type] ?? 5) - (priority[b.event_type] ?? 5) || a.event_id.localeCompare(b.event_id)).forEach(visit);
  return ordered.reduce(applyEvent, {
    profiles: {}, posts: {}, comments: {}, reactions: {},
    friendRequests: {}, friendships: {}, camps: {}, events: {},
    relationships: {}, memberships: {},
  });
}

export async function rebuildStore(store) { const events=[]; let cursor=null; for (;;) { const batch=await store.getEventsAfter(cursor,{limit:500}); if (!batch.length) break; events.push(...batch); cursor=batch.at(-1).event_id; if(batch.length<500) break; } const result=rebuild(events); await store.putProjection?.('root',result); return result; }
