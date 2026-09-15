import test from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { createIdentityStore } from '../identity/identityStore.js';
import { createMemoryReplicaStore } from '../local/replicaStore.js';
import { createCommentEvent, createLikeEvent, createUnlikeEvent } from './socialEvents.js';
import { appendLocalEvent } from '../local/localFirst.js';
import { createPostEvent } from './postEvents.js';
import { validateEvent } from './validateEvent.js';

if (!globalThis.crypto?.subtle) Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

test('comment and reaction events carry signed, object-scoped payloads', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const comment = await createCommentEvent(identity, 'post-1', 'hello');
  const liked = await createLikeEvent(identity, 'post-1');
  const unliked = await createUnlikeEvent(identity, 'post-1');
  assert.equal(comment.event_type, 'comment.created');
  assert.equal(comment.payload.post_id, 'post-1');
  assert.equal(comment.payload.content, 'hello');
  assert.equal(liked.event_type, 'post.liked');
  assert.equal(unliked.event_type, 'post.unliked');
  assert.equal(liked.object_id, 'post-1');
  assert.ok(comment.signature && liked.signature && unliked.signature);
});

test('social event validation rejects a reaction whose payload targets another post', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const event = await createLikeEvent(identity, 'post-1');
  event.payload.post_id = 'post-2';
  assert.equal((await validateEvent(event, { now: Date.parse(event.created_at) })).valid, false);
});

test('local comments and reactions project idempotently and unlike wins by event order', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const store = createMemoryReplicaStore();
  const post = await createPostEvent(identity, { content: 'hello' });
  const comment = await createCommentEvent(identity, post.object_id, 'first');
  const liked = await createLikeEvent(identity, post.object_id);
  const unliked = await createUnlikeEvent(identity, post.object_id);
  for (const event of [post, comment, liked, unliked, comment]) await appendLocalEvent(store, event);
  const projection = await store.getProjection('root');
  assert.equal(projection.comments[comment.object_id].content, 'first');
  assert.equal(projection.posts[post.object_id].comment_count, 1);
  assert.equal(projection.posts[post.object_id].like_count, 0);
  assert.equal(projection.reactions[`${post.object_id}:${identity.publicKey}`].liked, false);
});

test('peer rebuild materializes a comment and reaction regardless of delivery order', async () => {
  const identity = await createIdentityStore({ storage: new Map() }).initialize();
  const source = createMemoryReplicaStore();
  const replica = createMemoryReplicaStore();
  const post = await createPostEvent(identity, { content: 'shared' });
  const comment = await createCommentEvent(identity, post.object_id, 'shared comment');
  const like = await createLikeEvent(identity, post.object_id);
  for (const event of [post, comment, like]) await source.appendEvent(event);
  for (const event of [like, comment, post]) await replica.appendEvent(event);
  const sourceProjection = (await appendLocalEvent(source, await createUnlikeEvent(identity, post.object_id))).projection;
  await appendLocalEvent(replica, await createUnlikeEvent(identity, post.object_id));
  const replicaProjection = await replica.getProjection('root');
  assert.deepEqual(replicaProjection.posts[post.object_id], sourceProjection.posts[post.object_id]);
});
