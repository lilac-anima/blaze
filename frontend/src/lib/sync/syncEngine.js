import { boundedLimit } from '../local/schema.js';
import { validateAndStore } from '../protocol/validateEvent.js';
import { rebuildStore } from '../projections/projector.js';

export function createSyncEngine({ store, session, peerId, batchSize = 100, onStatus = () => {} }) {
  const limit = boundedLimit(batchSize);
  let unsubscribe;

  async function localEvents() {
    return store.getEventsAfter(null, { limit });
  }

  async function sendHello() {
    const events = await localEvents();
    session.send({
      type: 'hello',
      protocol_version: 1,
      peer_id: peerId,
      known_event_ids: events.map(event => event.event_id),
      cursor: await store.getPeerCursor(peerId),
    });
  }

  async function handle(message) {
    if (!message || typeof message !== 'object') return;
    if (message.type === 'hello') {
      if (message.protocol_version !== 1) return onStatus('unsupported-protocol');
      const known = new Set(message.known_event_ids || []);
      const events = (await localEvents()).filter(event => !known.has(event.event_id));
      session.send({ type: 'event_batch', cursor: events.at(-1)?.event_id || null, events });
    } else if (message.type === 'event_batch') {
      let accepted = 0;
      let rejected = 0;
      for (const event of message.events || []) {
        const result = await validateAndStore(event, store);
        if (result.valid) accepted += 1;
        else rejected += 1;
      }
      if (accepted) await rebuildStore(store);
      if (message.cursor) await store.setPeerCursor(peerId, message.cursor);
      session.send({ type: 'ack', cursor: message.cursor || null, accepted, rejected });
      onStatus(rejected ? 'quarantined' : 'synchronized');
    } else if (message.type === 'ack' && message.cursor) {
      await store.setPeerCursor(peerId, message.cursor);
      onStatus('synchronized');
    }
  }

  return {
    async start() {
      unsubscribe = session.onDataMessage(handle);
      await sendHello();
    },
    async resync() { await sendHello(); },
    close() { unsubscribe?.(); },
  };
}
