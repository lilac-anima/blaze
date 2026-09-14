<script>
  /**
   * Auth Guard — exports a reusable route pre-condition function and
   * the onConditionsFailed handler for svelte-spa-router's wrap().
   *
   * Usage in App.svelte:
   *   import { authCondition } from '$lib/auth/AuthGuard.svelte'
   *   import { push } from 'svelte-spa-router'
   *
   *   const routes = {
   *     '/': wrap({ component: Home, conditions: [authCondition] }),
   *     '/login': Login,
   *   }
   *
   *   function onConditionsFailed(detail) { push('/login') }
   *
   *   <Router {routes} {onConditionsFailed} />
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
</script>
