/**
 * Social API — client for all social feature endpoints.
 * Reads current user_id from JWT payload for endpoints that need it.
 */
import { api } from './client.js';
import { getTokenPayload } from '../auth/token.js';

function getUserId() {
  const p = getTokenPayload();
  return p?.sub || null;
}

// ── Feed ──────────────────────────────────────────────────────────

export async function fetchFeed(cursor = null, limit = 20) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const params = new URLSearchParams({ limit });
  if (cursor) params.set('cursor', cursor);
  const res = await api.get(`/feed/${uid}?${params}`);
  if (!res.ok) throw new Error('Failed to fetch feed');
  return res.json();
}

// ── Posts ─────────────────────────────────────────────────────────

export async function createPost(content, imageUrl = null) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post('/posts', { author_id: uid, content, image_url: imageUrl });
  if (!res.ok) throw new Error('Failed to create post');
  return res.json();
}

export async function getPost(postId) {
  const uid = getUserId();
  const params = uid ? `?current_user_id=${uid}` : '';
  const res = await api.get(`/posts/${postId}${params}`);
  if (!res.ok) throw new Error('Failed to fetch post');
  return res.json();
}

export async function deletePost(postId) {
  const res = await api.del(`/posts/${postId}`);
  if (!res.ok) throw new Error('Failed to delete post');
  return res.json();
}

export async function listUserPosts(userId, limit = 50) {
  const uid = getUserId();
  const params = new URLSearchParams({ limit });
  if (uid) params.set('current_user_id', uid);
  const res = await api.get(`/posts/user/${userId}?${params}`);
  if (!res.ok) throw new Error('Failed to fetch user posts');
  return res.json();
}

export async function likePost(postId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/posts/${postId}/like?user_id=${uid}`);
  if (!res.ok) throw new Error('Failed to like post');
  return res.json();
}

export async function unlikePost(postId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.del(`/posts/${postId}/like?user_id=${uid}`);
  if (!res.ok) throw new Error('Failed to unlike post');
  return res.json();
}

export async function getPostLikes(postId) {
  const res = await api.get(`/posts/${postId}/likes`);
  if (!res.ok) throw new Error('Failed to fetch likes');
  return res.json();
}

export async function addComment(postId, content) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/posts/${postId}/comments`, { user_id: uid, content });
  if (!res.ok) throw new Error('Failed to add comment');
  return res.json();
}

export async function listComments(postId) {
  const res = await api.get(`/posts/${postId}/comments`);
  if (!res.ok) throw new Error('Failed to fetch comments');
  return res.json();
}

// ── Friends ───────────────────────────────────────────────────────

export async function listFriends(userId) {
  const uid = userId || getUserId();
  const res = await api.get(`/friends/${uid}`);
  if (!res.ok) throw new Error('Failed to fetch friends');
  return res.json();
}

export async function sendFriendRequest(toUserId, message = null) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post('/friends/request', { from_user_id: uid, to_user_id: toUserId, message });
  if (!res.ok) throw new Error('Failed to send friend request');
  return res.json();
}

export async function acceptFriendRequest(requestId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/friends/request/${requestId}/accept`, { user_id: uid, request_id: requestId });
  if (!res.ok) throw new Error('Failed to accept friend request');
  return res.json();
}

export async function rejectFriendRequest(requestId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/friends/request/${requestId}/reject`, { user_id: uid, request_id: requestId });
  if (!res.ok) throw new Error('Failed to reject friend request');
  return res.json();
}

export async function listPendingRequests(direction = 'incoming') {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.get(`/friends/${uid}/pending?direction=${direction}`);
  if (!res.ok) throw new Error('Failed to fetch pending requests');
  return res.json();
}

export async function unfriend(friendId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.del(`/friends/${uid}/unfriend/${friendId}`);
  if (!res.ok) throw new Error('Failed to unfriend');
  return res.json();
}

// ── Events ────────────────────────────────────────────────────────

/**
 * Search events with server-side text matching (uses ?q= param on /events).
 * Thin wrapper around listEvents with a search-friendly limit.
 */
export async function searchEvents(q, limit = 20) {
  return listEvents(limit, q);
}

export async function listEvents(limit = 50, q = null) {
  const params = new URLSearchParams({ limit });
  if (q) params.set('q', q);
  const res = await api.get(`/events?${params}`);
  if (!res.ok) throw new Error('Failed to fetch events');
  return res.json();
}

export async function getEvent(eventId) {
  const res = await api.get(`/events/${eventId}`);
  if (!res.ok) throw new Error('Failed to fetch event');
  return res.json();
}

export async function createEvent(eventData) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const params = new URLSearchParams({ created_by: uid });
  const res = await api.post(`/events?${params}`, eventData);
  if (!res.ok) throw new Error('Failed to create event');
  return res.json();
}

export async function updateEvent(eventId, eventData) {
  const res = await api.patch(`/events/${eventId}`, eventData);
  if (!res.ok) throw new Error('Failed to update event');
  return res.json();
}

export async function deleteEvent(eventId) {
  const res = await api.del(`/events/${eventId}`);
  if (!res.ok) throw new Error('Failed to delete event');
  return res.json();
}

export async function rsvpEvent(eventId, status) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/events/${eventId}/rsvp`, { user_id: uid, status });
  if (!res.ok) throw new Error('Failed to RSVP');
  return res.json();
}

export async function listAttendees(eventId) {
  const res = await api.get(`/events/${eventId}/attendees`);
  if (!res.ok) throw new Error('Failed to fetch attendees');
  return res.json();
}

/**
 * Create a post scoped to an event.
 * Reuse existing likePost / unlikePost / deletePost for post-level actions.
 */
export async function createEventPost(eventId, content, imageUrl = null) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/events/${eventId}/posts`, {
    author_id: uid,
    content,
    image_url: imageUrl,
  });
  if (!res.ok) throw new Error('Failed to create event post');
  return res.json();
}

/**
 * List posts for an event, newest first.
 * Passes current_user_id so each post's is_liked_by_me is evaluated server-side.
 */
export async function listEventPosts(eventId) {
  const uid = getUserId();
  const params = uid ? `?current_user_id=${uid}` : '';
  const res = await api.get(`/events/${eventId}/posts${params}`);
  if (!res.ok) throw new Error('Failed to fetch event posts');
  return res.json();
}

/**
 * Promote an attendee to organizer. Only existing organizers can promote.
 */
export async function promoteToOrganizer(eventId, userId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/events/${eventId}/promote`, {
    user_id: userId,
    promoted_by: uid,
  });
  if (!res.ok) throw new Error('Failed to promote attendee');
  return res.json();
}

/**
 * Demote an organizer to regular attendee. Only organizers can demote.
 */
export async function demoteFromOrganizer(eventId, userId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/events/${eventId}/demote`, {
    user_id: userId,
    promoted_by: uid,
  });
  if (!res.ok) throw new Error('Failed to demote attendee');
  return res.json();
}

// ── Camps ─────────────────────────────────────────────────────────

/**
 * Search camps with server-side text matching (uses ?q= param on /camps).
 * Thin wrapper around listCamps with a search-friendly limit.
 */
export async function searchCamps(q, limit = 20) {
  return listCamps(limit, q);
}

export async function listCamps(limit = 50, q = null) {
  const params = new URLSearchParams({ limit });
  if (q) params.set('q', q);
  const res = await api.get(`/camps?${params}`);
  if (!res.ok) throw new Error('Failed to fetch camps');
  return res.json();
}

export async function getCamp(campId) {
  const res = await api.get(`/camps/${campId}`);
  if (!res.ok) throw new Error('Failed to fetch camp');
  return res.json();
}

export async function createCamp(campData) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const params = new URLSearchParams({ created_by: uid });
  const res = await api.post(`/camps?${params}`, campData);
  if (!res.ok) throw new Error('Failed to create camp');
  return res.json();
}

export async function updateCamp(campId, campData) {
  const res = await api.patch(`/camps/${campId}`, campData);
  if (!res.ok) throw new Error('Failed to update camp');
  return res.json();
}

export async function deleteCamp(campId) {
  const res = await api.del(`/camps/${campId}`);
  if (!res.ok) throw new Error('Failed to delete camp');
  return res.json();
}

export async function joinCamp(campId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/camps/${campId}/join?user_id=${uid}`);
  if (!res.ok) throw new Error('Failed to join camp');
  return res.json();
}

export async function leaveCamp(campId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/camps/${campId}/leave?user_id=${uid}`);
  if (!res.ok) throw new Error('Failed to leave camp');
  return res.json();
}

export async function listCampMembers(campId) {
  const res = await api.get(`/camps/${campId}/members`);
  if (!res.ok) throw new Error('Failed to fetch camp members');
  return res.json();
}

export async function promoteToModerator(campId, userId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/camps/${campId}/promote?user_id=${userId}&promoted_by=${uid}`);
  if (!res.ok) throw new Error('Failed to promote member');
  return res.json();
}

export async function demoteFromModerator(campId, userId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/camps/${campId}/demote?user_id=${userId}&demoted_by=${uid}`);
  if (!res.ok) throw new Error('Failed to demote member');
  return res.json();
}

// ── Groups ────────────────────────────────────────────────────────

export async function listGroups(limit = 50) {
  const res = await api.get(`/groups?limit=${limit}&public_only=true`);
  if (!res.ok) throw new Error('Failed to fetch groups');
  return res.json();
}

export async function getGroup(groupId) {
  const res = await api.get(`/groups/${groupId}`);
  if (!res.ok) throw new Error('Failed to fetch group');
  return res.json();
}

export async function createGroup(groupData) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const params = new URLSearchParams({ created_by: uid });
  const res = await api.post(`/groups?${params}`, groupData);
  if (!res.ok) throw new Error('Failed to create group');
  return res.json();
}

export async function updateGroup(groupId, groupData) {
  const res = await api.patch(`/groups/${groupId}`, groupData);
  if (!res.ok) throw new Error('Failed to update group');
  return res.json();
}

export async function joinGroup(groupId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/groups/${groupId}/join?user_id=${uid}`);
  if (!res.ok) throw new Error('Failed to join group');
  return res.json();
}

export async function leaveGroup(groupId) {
  const uid = getUserId();
  if (!uid) throw new Error('Not authenticated');
  const res = await api.post(`/groups/${groupId}/leave?user_id=${uid}`);
  if (!res.ok) throw new Error('Failed to leave group');
  return res.json();
}

export async function listGroupMembers(groupId) {
  const res = await api.get(`/groups/${groupId}/members`);
  if (!res.ok) throw new Error('Failed to fetch group members');
  return res.json();
}

// ── Users / Search ────────────────────────────────────────────────

export async function searchUsers(query) {
  const uid = getUserId();
  const params = new URLSearchParams({ q: query });
  if (uid) params.set('current_user_id', uid);
  const res = await api.get(`/users?${params}`);
  if (!res.ok) throw new Error('Failed to search users');
  return res.json();
}

export async function getUser(userId) {
  const res = await api.get(`/users/${userId}`);
  if (!res.ok) throw new Error('Failed to fetch user');
  return res.json();
}

export async function getUserSuggestions(userId, limit = 10) {
  const uid = userId || getUserId();
  const res = await api.get(`/users/${uid}/suggestions?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch suggestions');
  return res.json();
}

// ── Profile (uses JWT auth) ───────────────────────────────────────

export async function getMyProfile() {
  const res = await api.get('/api/users/me');
  if (!res.ok) throw new Error('Failed to fetch profile');
  return res.json();
}

export async function updateMyProfile(userData, profileData) {
  const body = {};
  if (userData) body.user = userData;
  if (profileData) body.burner = profileData;
  const res = await api.patch('/api/users/me', body);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update profile');
  }
  return res.json();
}
