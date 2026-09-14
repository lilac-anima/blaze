<script>
  /**
   * TopBar — top navigation bar with search and user menu.
   */
  import UserMenu from './UserMenu.svelte';

  let { onToggleSidebar = () => {}, user = null } = $props();
  let searchQuery = $state('');
</script>

<header class="topbar">
  <div class="topbar-left">
    <button class="menu-toggle btn-ghost" onclick={onToggleSidebar}>
      <span class="hamburger">☰</span>
    </button>

    <div class="search-container">
      <span class="search-icon">🔍</span>
      <input
        type="text"
        class="search-input"
        placeholder="Search camps, events, burners..."
        bind:value={searchQuery}
        onkeydown={(e) => {
          if (e.key === 'Enter' && searchQuery.trim()) {
            console.log('Search:', searchQuery.trim());
          }
        }}
      />
    </div>
  </div>

  <div class="topbar-right">
    <UserMenu {user} />
  </div>
</header>

<style>
  .topbar {
    position: fixed;
    top: 0;
    left: var(--sidebar-width);
    right: 0;
    height: var(--topbar-height);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    z-index: 90;
    transition: left var(--transition-normal);
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 16px;
    flex: 1;
  }

  .menu-toggle {
    display: none;
    width: 36px;
    height: 36px;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    font-size: 1.2rem;
  }
  .menu-toggle:hover {
    background: var(--bg-tertiary);
  }

  .hamburger {
    line-height: 1;
  }

  .search-container {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-input);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-xl);
    padding: 0 14px;
    max-width: 400px;
    width: 100%;
    transition: all var(--transition-fast);
  }
  .search-container:focus-within {
    border-color: var(--accent-sand);
    box-shadow: 0 0 0 2px rgba(212, 167, 106, 0.15);
  }

  .search-icon {
    font-size: 0.9rem;
    flex-shrink: 0;
  }

  .search-input {
    background: transparent;
    border: none;
    padding: 8px 0;
    width: 100%;
    font-size: 0.9rem;
    color: var(--text-primary);
  }
  .search-input:focus {
    outline: none;
    box-shadow: none;
  }

  .topbar-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .topbar {
      left: 0;
    }
    .menu-toggle {
      display: flex;
    }
    .search-container {
      max-width: 200px;
    }
  }
</style>
