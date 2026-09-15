<script>
  /**
   * AppLayout — global layout with sidebar, topbar, and main content area.
   * Wraps the router content.
   */
  import Sidebar from './Sidebar.svelte';
  import TopBar from './TopBar.svelte';
  import { getTokenPayload } from '../auth/token.js';
  import PeerSyncPanel from './PeerSyncPanel.svelte';

  let { children } = $props();
  let sidebarCollapsed = $state(false);
  let user = $state(null);

  // Load user info from JWT payload
  $effect(() => {
    const payload = getTokenPayload();
    if (payload) {
      user = {
        username: payload.sub || payload.username || 'Burner',
      };
    }
  });

  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }
</script>

<div class="app-layout" class:sidebar-closed={sidebarCollapsed}>
  <Sidebar collapsed={sidebarCollapsed} />
  <TopBar {user} onToggleSidebar={toggleSidebar} />

  <main class="main-content">
    <PeerSyncPanel />
    {@render children?.()}
  </main>
</div>

<style>
  .app-layout {
    min-height: 100vh;
  }

  .main-content {
    margin-left: var(--sidebar-width);
    margin-top: var(--topbar-height);
    padding: 28px 32px;
    min-height: calc(100vh - var(--topbar-height));
    transition: margin-left var(--transition-normal);
  }

  .sidebar-closed .main-content {
    margin-left: 64px;
  }

  @media (max-width: 768px) {
    .main-content {
      margin-left: 0;
      padding: 20px 16px;
    }
    .sidebar-closed .main-content {
      margin-left: 0;
    }
  }
</style>
