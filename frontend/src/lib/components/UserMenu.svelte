<script>
  /**
   * UserMenu — dropdown menu in the top bar.
   */
  import { push } from 'svelte-spa-router';
  import { logout } from '../auth/authService.js';

  let { user = null } = $props();
  let open = $state(false);

  function toggle() {
    open = !open;
  }

  function close() {
    open = false;
  }

  function handleLogout() {
    logout();
    close();
    push('/login');
  }

  function handleClickOutside(e) {
    if (!e.target.closest('.user-menu')) {
      open = false;
    }
  }

  // We use onMount for the click outside listener but need cleanup
  import { onMount } from 'svelte';

  onMount(() => {
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  });
</script>

<div class="user-menu">
  <button class="user-trigger" onclick={toggle} class:open>
    <span class="user-avatar">{user?.avatar || '🔥'}</span>
    <span class="user-name">{user?.username || 'Burner'}</span>
    <span class="dropdown-arrow">{open ? '▲' : '▼'}</span>
  </button>

  {#if open}
    <div class="dropdown-menu" role="menu">
      <a href="#/profile" class="dropdown-item" role="menuitem" onclick={close}>
        <span>👤</span> My Profile
      </a>
      <a href="#/settings" class="dropdown-item" role="menuitem" onclick={close}>
        <span>⚙️</span> Settings
      </a>
      <div class="dropdown-divider"></div>
      <button class="dropdown-item dropdown-logout" role="menuitem" onclick={handleLogout}>
        <span>🚪</span> Sign Out
      </button>
    </div>
  {/if}
</div>

<style>
  .user-menu {
    position: relative;
  }

  .user-trigger {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px 6px 6px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    color: var(--text-primary);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .user-trigger:hover {
    background: var(--bg-hover);
    border-color: var(--border-primary);
  }
  .user-trigger.open {
    border-color: var(--accent-sand);
  }

  .user-avatar {
    font-size: 1.3rem;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-card);
    border-radius: 50%;
  }

  .user-name {
    font-size: 0.9rem;
    font-weight: 500;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dropdown-arrow {
    font-size: 0.6rem;
    color: var(--text-muted);
    transition: transform var(--transition-fast);
  }

  .dropdown-menu {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    min-width: 200px;
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-lg);
    padding: 6px;
    z-index: 200;
    animation: slideDown 150ms ease;
  }

  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.9rem;
    text-decoration: none;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
    transition: background var(--transition-fast);
  }
  .dropdown-item:hover {
    background: var(--bg-hover);
  }

  .dropdown-divider {
    height: 1px;
    background: var(--border-subtle);
    margin: 4px 8px;
  }

  .dropdown-logout {
    color: var(--error);
  }
  .dropdown-logout:hover {
    background: rgba(212, 83, 74, 0.1);
  }
</style>
