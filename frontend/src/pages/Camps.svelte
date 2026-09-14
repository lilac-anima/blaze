<script>
  /**
   * Camps — browse camps and create new ones.
   * Lists camps from the API, shows a create-camp button that opens
   * the CreateCampModal dialog.
   */
  import { push } from 'svelte-spa-router';
  import { listCamps } from '../lib/api/social.js';
  import CampCard from '../lib/components/CampCard.svelte';
  import CreateCampModal from '../lib/components/CreateCampModal.svelte';

  let camps = $state([]);
  let loading = $state(false);
  let error = $state('');
  let showCreateModal = $state(false);

  async function loadCamps() {
    loading = true;
    error = '';
    try {
      camps = await listCamps(50);
    } catch (e) {
      error = e.message || 'Failed to load camps';
      camps = [];
    } finally {
      loading = false;
    }
  }

  function handleCampCreated(camp) {
    camps = [camp, ...camps];
    showCreateModal = false;
  }

  $effect(() => {
    loadCamps();
  });
</script>

<div class="camps-page">
  <!-- Page Header -->
  <div class="camps-header">
    <div class="camps-header-text">
      <h1>⛺ Camps</h1>
      <p class="camps-subtitle">Discover camps on the playa or start your own</p>
    </div>
    <button class="btn btn-primary" onclick={() => (showCreateModal = true)}>
      ✨ New Camp
    </button>
  </div>

  <!-- Loading State -->
  {#if loading}
    <div class="camps-status">
      <div class="spinner"></div>
      <span>Scouting camps...</span>
    </div>
  {:else if error}
    <!-- Error State -->
    <div class="camps-status camps-error">
      <span class="status-icon">⚠️</span>
      <p>{error}</p>
      <button class="btn btn-secondary" onclick={loadCamps}>Try Again</button>
    </div>
  {:else if camps.length === 0}
    <!-- Empty State -->
    <div class="camps-empty card">
      <div class="camps-empty-inner">
        <span class="empty-icon">🏕️</span>
        <h3>No camps yet</h3>
        <p>The playa is wide open. Be the first to plant your flag!</p>
        <button class="btn btn-primary" onclick={() => (showCreateModal = true)}>
          🏕️ Create a Camp
        </button>
      </div>
    </div>
  {:else}
    <!-- Camp List -->
    <div class="camps-list">
      {#each camps as camp (camp.camp_id)}
        <CampCard {camp} />
      {/each}
    </div>
  {/if}
</div>

<!-- Create Camp Modal -->
<CreateCampModal
  open={showCreateModal}
  onclose={() => (showCreateModal = false)}
  oncampcreated={handleCampCreated}
/>

<style>
  .camps-page {
    max-width: 680px;
    margin: 0 auto;
    padding: 0 0 40px;
  }

  /* ── Header ── */

  .camps-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }

  .camps-header-text h1 {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent-warm);
  }

  .camps-subtitle {
    font-size: 0.9rem;
    color: var(--text-muted);
    margin-top: 4px;
  }

  /* ── Status & States ── */

  .camps-status {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 60px 24px;
    color: var(--text-secondary);
    font-size: 0.95rem;
  }

  .camps-error {
    color: var(--error);
  }

  .status-icon {
    font-size: 2rem;
  }

  /* ── Empty State ── */

  .camps-empty {
    text-align: center;
    padding: 60px 24px;
  }

  .camps-empty-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .empty-icon {
    font-size: 3rem;
  }

  .camps-empty-inner h3 {
    font-size: 1.2rem;
    color: var(--text-primary);
  }

  .camps-empty-inner p {
    color: var(--text-muted);
    font-size: 0.9rem;
    max-width: 360px;
    line-height: 1.5;
  }

  /* ── Camp List ── */

  .camps-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* ── Spinner ── */

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border-subtle);
    border-top-color: var(--accent-sand);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* ── Mobile Responsive ── */

  @media (max-width: 768px) {
    .camps-page {
      padding: 0 0 24px;
    }

    .camps-header {
      flex-direction: column;
      align-items: stretch;
      margin-bottom: 18px;
    }

    .camps-header .btn {
      width: 100%;
    }

    .camps-header-text h1 {
      font-size: 1.25rem;
    }

    .camps-status {
      padding: 40px 16px;
    }

    .camps-empty {
      padding: 40px 16px;
    }

    .camps-list {
      gap: 8px;
    }
  }
</style>
