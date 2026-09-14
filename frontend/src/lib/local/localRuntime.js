import { createIdentityStore } from '../identity/identityStore.js';
import { createMemoryReplicaStore } from './replicaStore.js';
import { appendLocalEvent, readLocalFeed } from './localFirst.js';
import { createPostEvent } from '../protocol/postEvents.js';
import { createProfileEvent } from '../protocol/profileEvents.js';

const store = createMemoryReplicaStore();
const identityStore = createIdentityStore();
export async function createLocalPost(content, imageUrl, visibility = 'public') {
  const identity = await identityStore.initialize();
  const event = await createPostEvent(identity, { content, image_url: imageUrl, visibility }, identityStore);
  const result = await appendLocalEvent(store, event);
  const post = result.projection.posts[event.object_id];
  return { ...post, post_id: event.object_id, author_id: identity.id, author_username: identity.id, sync_status: result.syncStatus };
}
export async function updateLocalProfile(profile) {
  const identity = await identityStore.initialize();
  const event = await createProfileEvent(identity, profile, identityStore);
  return appendLocalEvent(store, event);
}
export { store, identityStore, readLocalFeed };
