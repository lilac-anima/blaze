import { validateAndStore } from '../protocol/validateEvent.js';
import { rebuildStore } from '../projections/projector.js';

export async function appendLocalEvent(store, event) {
  const result = await validateAndStore(event, store, { now: Date.parse(event.created_at) });
  if (!result.valid) return { status: 'rejected', reason: result.reason, event };
  const projection = await rebuildStore(store);
  return { status: 'local', syncStatus: 'pending', event, projection };
}

export async function readLocalFeed(store) {
  const projection = await store.getProjection('root') || await rebuildStore(store);
  return Object.values(projection.posts || {}).sort((a, b) => b.created_at.localeCompare(a.created_at));
}
