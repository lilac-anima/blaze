export const FEATURE_MODES = Object.freeze({
  CENTRALIZED: 'centralized',
  LOCAL_FIRST: 'local-first',
  P2P_PREVIEW: 'p2p-preview',
});

export function getFeatureMode(env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {}) {
  const value = env.VITE_FEATURE_MODE || env.PUBLIC_FEATURE_MODE || FEATURE_MODES.CENTRALIZED;
  return Object.values(FEATURE_MODES).includes(value) ? value : FEATURE_MODES.CENTRALIZED;
}

export function isLocalFirst(mode = getFeatureMode()) {
  return mode === FEATURE_MODES.LOCAL_FIRST || mode === FEATURE_MODES.P2P_PREVIEW;
}

export const featureMode = getFeatureMode();
