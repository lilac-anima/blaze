/**
 * Auth Guard utilities.
 * Provides a reusable route pre-condition for svelte-spa-router's wrap().
 */
import { isAuthenticated } from './token.js';

/**
 * Pre-condition function for svelte-spa-router wrap().
 * Returns true if authenticated, false otherwise.
 * The onConditionsFailed handler in App.svelte handles the redirect.
 */
export function authCondition(detail) {
  return isAuthenticated();
}
