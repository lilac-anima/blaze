import { createIdentityStore } from '../identity/identityStore.js';
import { createMemoryReplicaStore } from './replicaStore.js';
import { appendLocalEvent, readLocalFeed } from './localFirst.js';
import { createPostEvent } from '../protocol/postEvents.js';
import { createProfileEvent } from '../protocol/profileEvents.js';
import { createCommentEvent, createLikeEvent, createUnlikeEvent } from '../protocol/socialEvents.js';
import { createCampEvent, updateCampEvent, deleteCampEvent, joinCampEvent, leaveCampEvent, grantCampRoleEvent, revokeCampRoleEvent } from '../protocol/campEvents.js';

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
export async function createLocalComment(postId, content) {
  const identity = await identityStore.initialize();
  return appendLocalEvent(store, await createCommentEvent(identity, postId, content, identityStore));
}
export async function likeLocalPost(postId) {
  const identity = await identityStore.initialize();
  return appendLocalEvent(store, await createLikeEvent(identity, postId, identityStore));
}
export async function unlikeLocalPost(postId) {
  const identity = await identityStore.initialize();
  return appendLocalEvent(store, await createUnlikeEvent(identity, postId, identityStore));
}
async function appendCampEvent(makeEvent) {
  const identity = await identityStore.initialize();
  return appendLocalEvent(store, await makeEvent(identity, identityStore));
}
export async function createLocalCamp(camp) { return appendCampEvent((identity, keys) => createCampEvent(identity, camp, keys)); }
export async function updateLocalCamp(campId, changes) { return appendCampEvent((identity, keys) => updateCampEvent(identity, campId, changes, keys)); }
export async function tombstoneLocalCamp(campId, reason) { return appendCampEvent((identity, keys) => deleteCampEvent(identity, campId, reason, keys)); }
export async function joinLocalCamp(campId) { return appendCampEvent((identity, keys) => joinCampEvent(identity, campId, keys)); }
export async function leaveLocalCamp(campId) { return appendCampEvent((identity, keys) => leaveCampEvent(identity, campId, keys)); }
export async function grantLocalCampRole(campId, memberId, role = 'moderator') { return appendCampEvent((identity, keys) => grantCampRoleEvent(identity, campId, memberId, role, keys)); }
export async function revokeLocalCampRole(campId, memberId, role = 'moderator') { return appendCampEvent((identity, keys) => revokeCampRoleEvent(identity, campId, memberId, role, keys)); }
export { store, identityStore, readLocalFeed };
