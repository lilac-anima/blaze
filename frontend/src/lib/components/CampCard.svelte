<script>
  /**
   * CampCard — camp card for lists.
   * Props: camp (CampResponse object)
   */
  import { push } from 'svelte-spa-router';

  let { camp } = $props();

  function goToDetail() {
    push(`/camps/${camp.camp_id}`);
  }
</script>

<div class="camp-card card" onclick={goToDetail} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && goToDetail()}>
  <div class="camp-icon">⛺</div>
  <div class="camp-info">
    <h3 class="camp-name">{camp.name}</h3>
    {#if camp.description}
      <p class="camp-desc">{camp.description}</p>
    {/if}
    {#if camp.location_on_playa}
      <p class="camp-location">📍 {camp.location_on_playa}</p>
    {/if}
  </div>
  <div class="camp-meta">
    {#if camp.event_name}
      <span class="event-badge" title="Event: {camp.event_name}">🏕️</span>
    {/if}
    <span class="member-count" title="Members">👥 {camp.member_count || 0}</span>
  </div>
</div>

<style>
  .camp-card {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    padding: 18px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .camp-card:hover {
    border-color: var(--accent-sand);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
  }
  .camp-card:focus-visible {
    outline: 2px solid var(--accent-sand);
    outline-offset: 2px;
  }

  .camp-icon {
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

  .camp-info {
    flex: 1;
    min-width: 0;
  }

  .camp-name {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--accent-warm);
  }

  .camp-desc {
    font-size: 0.85rem;
    color: var(--text-secondary);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .camp-location {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .camp-meta {
    flex-shrink: 0;
  }

  .member-count {
    font-size: 0.85rem;
    color: var(--text-secondary);
  }
</style>
