import { boundedLimit, eventParents } from './schema.js';

/** Backend-neutral local replica contract. Reads are bounded to at most 500 records. */
export function createMemoryReplicaStore() {
  const events = new Map();
  const quarantine = new Map();
  const cursors = new Map();
  const projections = new Map();
  return {
    async appendEvent(event) { if (events.has(event.event_id)) return false; events.set(event.event_id, structuredClone(event)); return true; },
    async hasEvent(eventId) { return events.has(eventId); },
    async getEventsAfter(cursor = null, scope = {}) {
      const limit = boundedLimit(scope.limit); const values = [...events.values()];
      const start = cursor ? Math.max(0, values.findIndex(e => e.event_id === cursor) + 1) : 0;
      return values.slice(start, start + limit).filter(e => !scope.eventType || e.event_type === scope.eventType).map(value => structuredClone(value));
    },
    async getMissingParents(eventIds) {
      const missing = new Set(); for (const id of eventIds || []) for (const parent of eventParents(events.get(id))) if (!events.has(parent)) missing.add(parent); return [...missing];
    },
    async getProjection(name, query = {}) { const value = projections.get(name); if (query.id && value?.id !== query.id) return null; return value ? structuredClone(value) : null; },
    async setPeerCursor(peerId, cursor) { cursors.set(peerId, cursor); },
    async getPeerCursor(peerId) { return cursors.get(peerId) ?? null; },
    async quarantineEvent(event, reason) { quarantine.set(event.event_id || crypto.randomUUID(), { event: structuredClone(event), reason, quarantined_at: new Date().toISOString() }); },
    async getQuarantinedEvents() { return [...quarantine.values()].map(value => structuredClone(value)); },
    async putProjection(name, value) { projections.set(name, structuredClone(value)); }
  };
}

export const replicaStoreOperations = Object.freeze([
  'appendEvent', 'hasEvent', 'getEventsAfter', 'getMissingParents',
  'getProjection', 'putProjection', 'setPeerCursor', 'getPeerCursor',
  'quarantineEvent', 'getQuarantinedEvents'
]);
