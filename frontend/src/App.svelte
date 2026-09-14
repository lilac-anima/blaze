<script>
  /**
   * App.svelte — Root component with svelte-spa-router.
   * Auth pages render without sidebar layout; protected pages get AppLayout.
   */
  import Router, { push, router } from 'svelte-spa-router';
  import { wrap } from 'svelte-spa-router/wrap';

  import { authCondition } from './lib/auth/authGuard.js';
  import { isAuthenticated } from './lib/auth/token.js';

  import AppLayout from './lib/components/AppLayout.svelte';
  import Home from './pages/Home.svelte';
  import Login from './pages/Login.svelte';
  import Register from './pages/Register.svelte';
  import ForgotPassword from './pages/ForgotPassword.svelte';
  import Friends from './pages/Friends.svelte';
  import Groups from './pages/Groups.svelte';
  import EventDetail from './pages/EventDetail.svelte';
  import NewsFeed from './pages/NewsFeed.svelte';
  import UserProfile from './pages/UserProfile.svelte';
  import EditProfile from './pages/EditProfile.svelte';
  import Events from './pages/Events.svelte';
  import CreateEvent from './pages/CreateEvent.svelte';
  import Camps from './pages/Camps.svelte';
  import CampDetail from './pages/CampDetail.svelte';

  // Auth route paths (render without layout)
  const authRoutes = ['/login', '/register', '/forgot-password'];

  /**
   * Route definitions.
   */
  const routes = {
    '/login': wrap({
      component: Login,
      conditions: [
        () => {
          if (isAuthenticated()) {
            push('/');
            return false;
          }
          return true;
        },
      ],
    }),
    '/register': wrap({
      component: Register,
      conditions: [
        () => {
          if (isAuthenticated()) {
            push('/');
            return false;
          }
          return true;
        },
      ],
    }),
    '/forgot-password': wrap({
      component: ForgotPassword,
      conditions: [
        () => {
          if (isAuthenticated()) {
            push('/');
            return false;
          }
          return true;
        },
      ],
    }),

    // Protected routes
    '/': wrap({
      component: Home,
      conditions: [authCondition],
    }),
    '/feed': wrap({
      component: NewsFeed,
      conditions: [authCondition],
    }),
    '/profile/edit': wrap({
      component: EditProfile,
      conditions: [authCondition],
    }),
    '/profile/:username': wrap({
      component: UserProfile,
      conditions: [authCondition],
    }),
    '/friends': wrap({
      component: Friends,
      conditions: [authCondition],
    }),
    '/events': wrap({
      component: Events,
      conditions: [authCondition],
    }),
    '/events/new': wrap({
      component: CreateEvent,
      conditions: [authCondition],
    }),
    '/events/:id': wrap({
      component: EventDetail,
      conditions: [authCondition],
    }),
    '/camps': wrap({
      component: Camps,
      conditions: [authCondition],
    }),
    '/camps/:id': wrap({
      component: CampDetail,
      conditions: [authCondition],
    }),
    '/groups': wrap({
      component: Groups,
      conditions: [authCondition],
    }),

    // Catch-all — redirect to login
    '*': wrap({
      component: Home,
      conditions: [authCondition],
    }),
  };

  function onConditionsFailed(detail) {
    push('/login');
  }

  // Determine if current route needs the app layout (reactive via router.location)
  let isAuthRoute = $derived(authRoutes.includes(router.location));
</script>

{#if isAuthRoute}
  <Router {routes} {onConditionsFailed} />
{:else}
  <AppLayout>
    <Router {routes} {onConditionsFailed} />
  </AppLayout>
{/if}
