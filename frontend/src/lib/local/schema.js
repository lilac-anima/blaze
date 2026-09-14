export const DB_VERSION = 1;
export const STORE_NAMES = Object.freeze({
  events: 'events', parents: 'parents', quarantine: 'quarantine', cursors: 'peerCursors',
  projections: 'projections', identities: 'identities', media: 'mediaManifests', sync: 'syncTasks'
});
export const DEFAULT_BATCH_SIZE = 100;
export const MAX_BATCH_SIZE = 500;
export function boundedLimit(limit = DEFAULT_BATCH_SIZE) {
  return Math.max(1, Math.min(MAX_BATCH_SIZE, Number.isFinite(limit) ? Math.floor(limit) : DEFAULT_BATCH_SIZE));
}
export function eventParents(event) { return Array.isArray(event?.parents) ? event.parents : []; }
