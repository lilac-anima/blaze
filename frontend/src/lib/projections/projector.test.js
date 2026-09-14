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
