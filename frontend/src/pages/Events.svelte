<script>
  /**
   * Events — list/search events page at /events.
   */
  import { push } from 'svelte-spa-router';
  import { listEvents } from '../lib/api/social.js';
  import EventCard from '../lib/components/EventCard.svelte';

  let events = $state([]);
  let loading = $state(true);
  let error = $state('');
  let searchQuery = $state('');

  let debounceTimer;

  async function loadEvents(q) {
    loading = true;
    error = '';
    try {
      const data = await listEvents(100, q || undefined);
      events = data || [];
    } catch (e) {
      error = e.message || 'Failed to load events';
      events = [];
    } finally {
      loading = false;
    }
  }

  function handleSearchInput(e) {
    searchQuery = e.target.value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => loadEvents(searchQuery), 300);
  }

  $effect(() => {
    loadEvents();
  });
</script>

<div class="events-page">
  <div class="page-header">
    <div class="header-top">
      <h1>Events</h1>
      <button class="btn btn-primary" onclick={() => push('/events/new')}>
        + Create Event
      </button>
    </div>
    <div class="search-bar">
      <span class="search-icon">🔍</span>
      <input
        type="text"
        class="search-input"
        placeholder="Search events by name..."
        value={searchQuery}
        oninput={handleSearchInput}
      />
    </div>
  </div>

  {#if loading && events.length === 0}
    <div class="loading-state"><p>Loading events…</p></div>
  {:else if error}
    <div class="error-state">
      <p class="error-text">{error}</p>
      <button class="btn btn-secondary" onclick={() => loadEvents()}>Retry</button>
    </div>
  {:else if events.length === 0}
    <div class="empty-state">
      <span class="empty-icon">🎪</span>
      <h2>No events found</h2>
      {#if searchQuery}
        <p>No events match "{searchQuery}"</p>
      {:else}
        <p>No events on the playa yet. Create one!</p>
      {/if}
      <button class="btn btn-primary" onclick={() => push('/events/new')}>Create an Event</button>
    </div>
  {:else}
    <div class="events-grid">
      {#each events as event (event.event_id)}
        <EventCard {event} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .events-page {
    max-width: 1000px;
    margin: 0 auto;
    padding: 32px 24px 60px;
  }
  .page-header { margin-bottom: 28px; }
  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .page-header h1 { font-size: 1.6rem; color: var(--accent-warm); margin: 0; }
  .search-bar { position: relative; display: flex; align-items: center; }
  .search-icon { position: absolute; left: 14px; font-size: 0.9rem; pointer-events: none; }
  .search-input {
    width: 100%; padding: 10px 14px 10px 40px;
    border: 1px solid var(--border-primary); border-radius: var(--radius-md);
    background: var(--bg-input); color: var(--text-primary); font-size: 0.9rem;
    transition: border-color var(--transition-fast); box-sizing: border-box;
  }
  .search-input:focus { outline: none; border-color: var(--accent-sand); }
  .search-input::placeholder { color: var(--text-muted); }
  .events-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
  .loading-state, .error-state, .empty-state {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 80px 24px; text-align: center; gap: 12px;
  }
  .empty-icon { font-size: 3rem; }
  .empty-state h2 { font-size: 1.3rem; color: var(--accent-warm); }
  .empty-state p, .loading-state p { color: var(--text-muted); font-size: 0.9rem; }
  .error-text { color: var(--error); }
  .btn {
    padding: 10px 20px; border: none; border-radius: var(--radius-md);
    font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: all var(--transition-fast);
  }
  .btn-primary { background: var(--accent-terracotta); color: white; }
  .btn-primary:hover { background: #b04e12; }
  .btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); border: 1px solid var(--border-primary); }
  .btn-secondary:hover { background: var(--bg-hover); }
  @media (max-width: 768px) {
    .events-grid { grid-template-columns: 1fr; }
    .header-top { flex-direction: column; align-items: stretch; }
    .events-page { padding: 20px 16px 40px; }
  }
</style>
