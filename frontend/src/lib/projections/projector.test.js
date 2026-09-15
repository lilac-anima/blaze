import test from 'node:test';
import assert from 'node:assert/strict';
import { rebuild } from './projector.js';
import { materializeFeed } from './feedProjection.js';

const post = (id, at) => ({ event_id:id, event_type:'post.created', object_id:id, author:'author', created_at:at, payload:{body:id}, parents:[] });

test('projection rebuild is deterministic for out-of-order duplicate delivery', () => {
  const events = [post('b','2026-01-02T00:00:00Z'), post('a','2026-01-01T00:00:00Z'), post('b','2026-01-02T00:00:00Z')];
  const first = rebuild(events);
  const second = rebuild([...events].reverse());
  assert.deepEqual(first, second);
  assert.deepEqual(materializeFeed(first).map(x => x.id), ['b','a']);
});

test('profile projection uses deterministic last-write ordering', () => {
  const newer = { event_id:'new', event_type:'profile.updated', object_id:'p', created_at:'2026-01-02T00:00:00Z', payload:{display_name:'new'}, parents:[] };
  const older = { ...newer, event_id:'old', created_at:'2026-01-01T00:00:00Z', payload:{display_name:'old'} };
  assert.equal(rebuild([newer, older]).profiles.p.display_name, 'new');
});

test('feed projection filters private audiences while keeping public compatibility reads', () => {
  const events = [
    post('public', '2026-01-03T00:00:00Z'),
    { ...post('friends', '2026-01-02T00:00:00Z'), payload: { body: 'friends', visibility: 'friends' }, author: 'bob' },
    { ...post('private', '2026-01-01T00:00:00Z'), payload: { body: 'private', visibility: 'private' }, author: 'bob' },
    { event_id: 'friendship', event_type: 'friend.accepted', object_id: 'friendship', author: 'alice', created_at: '2026-01-01T00:00:00Z', payload: { requester: 'alice', recipient: 'bob' }, parents: [] },
  ];
  const state = rebuild(events);
  assert.deepEqual(materializeFeed(state).map(item => item.id), ['public']);
  assert.deepEqual(materializeFeed(state, { viewerId: 'alice' }).map(item => item.id), ['public', 'friends']);
  assert.deepEqual(materializeFeed(state, { viewerId: 'bob' }).map(item => item.id), ['public', 'friends', 'private']);
});

test('feed projection applies group membership and deterministic tie ordering', () => {
  const state = rebuild([
    { ...post('z', '2026-01-02T00:00:00Z'), payload: { visibility: 'group', group_id: 'g' }, author: 'bob' },
    { ...post('a', '2026-01-02T00:00:00Z'), payload: { visibility: 'public' }, author: 'bob' },
    { event_id: 'membership', event_type: 'group.member.added', object_id: 'membership', author: 'admin', created_at: '2026-01-01T00:00:00Z', payload: { member_id: 'alice', group_id: 'g' }, parents: [] },
  ]);
  assert.deepEqual(materializeFeed(state, { viewerId: 'alice' }).map(item => item.id), ['z', 'a']);
  assert.deepEqual(materializeFeed(state, { viewerId: 'nobody' }).map(item => item.id), ['a']);
});
