import { DB_VERSION, STORE_NAMES, boundedLimit, eventParents } from './schema.js';

function request(req) { return new Promise((resolve, reject) => { req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error); }); }
export function openReplicaDatabase(name = 'blaze-replica') {
  return new Promise((resolve, reject) => { const req = indexedDB.open(name, DB_VERSION); req.onupgradeneeded = () => { const db = req.result;
    for (const store of Object.values(STORE_NAMES)) if (!db.objectStoreNames.contains(store)) db.createObjectStore(store, { keyPath: store === STORE_NAMES.events ? 'event_id' : 'id', autoIncrement: store === STORE_NAMES.quarantine });
    const events = req.transaction.objectStore(STORE_NAMES.events); if (!events.indexNames.contains('created_at')) events.createIndex('created_at', 'created_at');
    if (!events.indexNames.contains('event_type')) events.createIndex('event_type', 'event_type');
    const parents = req.transaction.objectStore(STORE_NAMES.parents); if (!parents.indexNames.contains('parent')) parents.createIndex('parent', 'parent');
  }; req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error); });
}
export function createIndexedDbReplicaStore(name) {
  let dbPromise = openReplicaDatabase(name);
  const tx = async (stores, mode, fn) => fn((await dbPromise).transaction(stores, mode));
  return {
    async appendEvent(event) { return tx([STORE_NAMES.events, STORE_NAMES.parents], 'readwrite', async t => { const events=t.objectStore(STORE_NAMES.events); if (await request(events.get(event.event_id))) return false; await request(events.add(structuredClone(event))); for (const parent of eventParents(event)) await request(t.objectStore(STORE_NAMES.parents).put({ id: `${parent}:${event.event_id}`, parent, event_id: event.event_id })); return true; }); },
    async hasEvent(id) { return tx([STORE_NAMES.events], 'readonly', t => request(t.objectStore(STORE_NAMES.events).getKey(id)).then(Boolean)); },
    async getEventsAfter(cursor = null, scope = {}) { return tx([STORE_NAMES.events], 'readonly', async t => { const all=await request(t.objectStore(STORE_NAMES.events).getAll()); const start=cursor ? all.findIndex(e=>e.event_id===cursor)+1 : 0; return all.slice(Math.max(0,start)).filter(e=>!scope.eventType||e.event_type===scope.eventType).slice(0, boundedLimit(scope.limit)); }); },
    async getMissingParents(ids) { return tx([STORE_NAMES.events], 'readonly', async t => { const all=await request(t.objectStore(STORE_NAMES.events).getAll()); const known=new Set(all.map(e=>e.event_id)); return [...new Set(all.filter(e=>ids?.includes(e.event_id)).flatMap(eventParents).filter(p=>!known.has(p)))]; }); },
    async getProjection(name) { return tx([STORE_NAMES.projections], 'readonly', t => request(t.objectStore(STORE_NAMES.projections).get(name)).then(x=>x?.value ?? null)); },
    async putProjection(name,value) { return tx([STORE_NAMES.projections], 'readwrite', t => request(t.objectStore(STORE_NAMES.projections).put({id:name,value}))); },
    async setPeerCursor(peerId,cursor) { return tx([STORE_NAMES.cursors], 'readwrite', t => request(t.objectStore(STORE_NAMES.cursors).put({id:peerId,cursor}))); },
    async getPeerCursor(peerId) { return tx([STORE_NAMES.cursors], 'readonly', t => request(t.objectStore(STORE_NAMES.cursors).get(peerId)).then(x=>x?.cursor ?? null)); },
    async quarantineEvent(event,reason) { return tx([STORE_NAMES.quarantine], 'readwrite', t => request(t.objectStore(STORE_NAMES.quarantine).add({event,reason,quarantined_at:new Date().toISOString()}))); },
    async getQuarantinedEvents() { return tx([STORE_NAMES.quarantine], 'readonly', t => request(t.objectStore(STORE_NAMES.quarantine).getAll())); }
  };
}
