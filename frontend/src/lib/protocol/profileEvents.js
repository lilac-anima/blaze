import { signLocalEvent, newObjectId } from './localEvent.js';
export function createProfileEvent(identity, profile, store) {
  return signLocalEvent(identity, profile, 'profile.updated', profile.id || `profile:${identity.id}`, store);
}
