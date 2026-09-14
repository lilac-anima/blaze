import test from 'node:test';
import assert from 'node:assert/strict';
import { FEATURE_MODES, getFeatureMode, isLocalFirst } from './features.js';

test('centralized is the default and explicit modes are accepted', () => {
  assert.equal(getFeatureMode({}), FEATURE_MODES.CENTRALIZED);
  assert.equal(getFeatureMode({ VITE_FEATURE_MODE: 'local-first' }), FEATURE_MODES.LOCAL_FIRST);
  assert.equal(getFeatureMode({ VITE_FEATURE_MODE: 'p2p-preview' }), FEATURE_MODES.P2P_PREVIEW);
  assert.equal(getFeatureMode({ VITE_FEATURE_MODE: 'unknown' }), FEATURE_MODES.CENTRALIZED);
  assert.equal(isLocalFirst(FEATURE_MODES.LOCAL_FIRST), true);
});
