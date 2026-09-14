<script>
  /**
   * Sidebar — left navigation for the app.
   */
  import { link, router } from 'svelte-spa-router';

  let { collapsed = false } = $props();

  const navItems = [
    { href: '/', label: 'Home', icon: '🏕️' },
    { href: '/feed', label: 'Feed', icon: '📰' },
    { href: '/friends', label: 'Friends', icon: '🤝' },
    { href: '/events', label: 'Events', icon: '🎪' },
    { href: '/camps', label: 'Camps', icon: '⛺' },
    { href: '/groups', label: 'Groups', icon: '🔗' },
    { href: '/profile', label: 'Profile', icon: '👤' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ];
</script>

<aside class="sidebar" class:collapsed>
  <div class="sidebar-brand">
    {#if !collapsed}
      <span class="brand-icon">🔥</span>
      <span class="brand-text">Blaze</span>
    {:else}
      <span class="brand-icon">🔥</span>
    {/if}
  </div>

  <nav class="sidebar-nav">
    {#each navItems as item}
      <a
        href={item.href}
        use:link
        class="nav-item"
        class:active={router.location === item.href}
      >
        <span class="nav-icon">{item.icon}</span>
        {#if !collapsed}
          <span class="nav-label">{item.label}</span>
        {/if}
      </a>
    {/each}
  </nav>

  <div class="sidebar-footer">
    <div class="playa-dust">
      {#if !collapsed}
        <span class="dust-text">✦ Playa Dust ✦</span>
      {/if}
    </div>
  </div>
</aside>

<style>
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--sidebar-width);
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    z-index: 100;
    transition: width var(--transition-normal);
    overflow: hidden;
  }

  .sidebar.collapsed {
    width: 64px;
  }

  .sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 18px 16px;
    border-bottom: 1px solid var(--border-subtle);
    min-height: 60px;
  }

  .brand-icon {
    font-size: 1.5rem;
    flex-shrink: 0;
  }

  .brand-text {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--accent-sand);
    white-space: nowrap;
  }

  .sidebar-nav {
    flex: 1;
    padding: 12px 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    overflow-y: auto;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    text-decoration: none;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }

  .nav-item:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  .nav-item.active {
    background: rgba(212, 167, 106, 0.12);
    color: var(--accent-sand);
  }

  .nav-icon {
    font-size: 1.2rem;
    flex-shrink: 0;
    width: 28px;
    text-align: center;
  }

  .nav-label {
    font-size: 0.9rem;
    font-weight: 500;
  }

  .sidebar-footer {
    padding: 12px 16px;
    border-top: 1px solid var(--border-subtle);
  }

  .playa-dust {
    text-align: center;
  }

  .dust-text {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-style: italic;
  }
</style>
