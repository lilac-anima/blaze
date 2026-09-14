import { signLocalEvent, newObjectId } from './localEvent.js';
export function createPostEvent(identity, post, store) {
  return signLocalEvent(identity, post, 'post.created', post.id || newObjectId('post'), store);
}
