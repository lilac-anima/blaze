<script>
  /**
   * RSVPButton — RSVP state for events.
   * Props: eventId, myStatus ('going'|'maybe'|'not going'|null), onchange(status)
   */
  import { rsvpEvent } from '../api/social.js';

  let { eventId, myStatus = null, onchange = () => {} } = $props();
  let loading = $state(false);

  const options = [
    { value: 'going', label: '🔥 Going', icon: '🔥' },
    { value: 'maybe', label: '🤔 Maybe', icon: '🤔' },
    { value: 'not going', label: '🚫 Nope', icon: '🚫' },
  ];

  async function handleRSVP(status) {
    loading = true;
    try {
      await rsvpEvent(eventId, status);
      onchange(status);
    } catch (e) {
      console.error('RSVP failed:', e);
    } finally {
      loading = false;
    }
  }

  function handleClear() {
    handleRSVP('not going');
  }
</script>

<div class="rsvp-group">
  {#each options as opt}
    <button
      class="rsvp-btn"
      class:active={myStatus === opt.value}
      disabled={loading}
      onclick={() => handleRSVP(opt.value)}
    >
      {opt.label}
    </button>
  {/each}
</div>

<style>
  .rsvp-group {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .rsvp-btn {
    padding: 8px 16px;
    border-radius: var(--radius-xl);
    font-size: 0.85rem;
    font-weight: 600;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .rsvp-btn:hover:not(:disabled) {
    border-color: var(--accent-sand);
    color: var(--text-primary);
  }
  .rsvp-btn.active {
    background: rgba(212, 167, 106, 0.15);
    border-color: var(--accent-sand);
    color: var(--accent-sand);
  }
  .rsvp-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
