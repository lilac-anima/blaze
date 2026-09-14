<script>
  /**
   * GroupCard — group card for lists.
   * Props: group (GroupResponse object)
   */
  import { push } from 'svelte-spa-router';

  let { group } = $props();

  function goToDetail() {
    push(`/groups/${group.group_id}`);
  }
</script>

<div class="group-card card" onclick={goToDetail} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && goToDetail()}>
  <div class="group-icon">🔗</div>
  <div class="group-info">
    <h3 class="group-name">{group.name}</h3>
    {#if group.description}
      <p class="group-desc">{group.description}</p>
    {/if}
  </div>
  <div class="group-meta">
    <span class="group-visibility" title={group.is_public ? 'Public group' : 'Invite-only'}>
      {group.is_public ? '🌍' : '🔒'}
    </span>
    <span class="member-count">👥 {group.member_count || 0}</span>
  </div>
</div>

<style>
  .group-card {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    padding: 18px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .group-card:hover {
    border-color: var(--accent-sand);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
  }
  .group-card:focus-visible {
    outline: 2px solid var(--accent-sand);
    outline-offset: 2px;
  }

  .group-icon {
    font-size: 2rem;
    flex-shrink: 0;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
  }

  .group-info {
    flex: 1;
    min-width: 0;
  }

  .group-name {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--accent-warm);
  }

  .group-desc {
    font-size: 0.85rem;
    color: var(--text-secondary);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .group-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    flex-shrink: 0;
  }

  .group-visibility {
    font-size: 1.1rem;
  }

  .member-count {
    font-size: 0.85rem;
    color: var(--text-secondary);
  }
</style>
