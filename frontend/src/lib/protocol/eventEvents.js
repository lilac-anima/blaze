import { signLocalEvent, newObjectId } from './localEvent.js';

function lifecycleEvent(identity, payload, type, objectId, store, parents, createdAt) {
  return signLocalEvent(identity, payload, type, objectId, store, parents, { createdAt });
}

export function createEventEvent(identity, event, store, createdAt = new Date().toISOString()) {
  const objectId = event.id || newObjectId('event');
  return lifecycleEvent(identity, {
    name: event.name,
    date: event.date,
    location_on_playa: event.location_on_playa ?? null,
    camp: event.camp ?? null,
    description: event.description ?? null,
    max_attendees: event.max_attendees ?? null,
    organizer_id: identity.publicKey,
  }, 'event.created', objectId, store, [], createdAt);
}

export function updateEventEvent(identity, eventId, changes, store, parents = [], createdAt = new Date().toISOString()) {
  return lifecycleEvent(identity, { changes: { ...changes } }, 'event.updated', eventId, store, parents, createdAt);
}

export function tombstoneEvent(identity, eventId, store, parents = [], createdAt = new Date().toISOString()) {
  return lifecycleEvent(identity, { tombstoned: true }, 'event.tombstoned', eventId, store, parents, createdAt);
}

export function createRsvpEvent(identity, eventId, status, store, parents = [], createdAt = new Date().toISOString()) {
  if (!['going', 'maybe', 'not going'].includes(status)) throw new Error('invalid RSVP status');
  return lifecycleEvent(identity, { attendee_id: identity.publicKey, status }, 'event.rsvp.updated', eventId, store, parents, createdAt);
}

export function grantOrganizerEvent(identity, eventId, attendeeId, store, parents = [], createdAt = new Date().toISOString()) {
  return lifecycleEvent(identity, { attendee_id: attendeeId }, 'event.organizer.granted', eventId, store, parents, createdAt);
}

export function revokeOrganizerEvent(identity, eventId, attendeeId, store, parents = [], createdAt = new Date().toISOString()) {
  return lifecycleEvent(identity, { attendee_id: attendeeId }, 'event.organizer.revoked', eventId, store, parents, createdAt);
}

export const createRSVPEvent = createRsvpEvent;
export const createEventRSVPEvent = createRsvpEvent;
