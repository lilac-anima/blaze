import { signLocalEvent, newObjectId } from './localEvent.js';

function requirePostId(postId) {
  if (typeof postId !== 'string' || !postId.trim()) throw new TypeError('post_id is required');
  return postId;
}

export function createCommentEvent(identity, postId, content, store) {
  const target = requirePostId(postId);
  if (typeof content !== 'string' || !content.trim()) throw new TypeError('comment content is required');
  return signLocalEvent(identity, { post_id: target, content: content.trim() }, 'comment.created', newObjectId('comment'), store, [target]);
}

export function createLikeEvent(identity, postId, store) {
  const target = requirePostId(postId);
  return signLocalEvent(identity, { post_id: target }, 'post.liked', target, store, [target]);
}

export function createUnlikeEvent(identity, postId, store) {
  const target = requirePostId(postId);
  return signLocalEvent(identity, { post_id: target }, 'post.unliked', target, store, [target]);
}
