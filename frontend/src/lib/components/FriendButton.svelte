<script>
  /**
   * FriendButton — add/remove/pending friend states.
   * Props: userId, isFriend, requestStatus ('none'|'pending_sent'|'pending_received'|'friends')
   * Events: onadd, onaccept, onreject, onremove
   */
  import { sendFriendRequest, acceptFriendRequest, rejectFriendRequest, unfriend } from '../api/social.js';

  let { userId, isFriend = false, requestStatus = 'none', onadd = () => {}, onaccept = () => {}, onreject = () => {}, onremove = () => {} } = $props();

  let loading = $state(false);
  let error = $state('');

  let status = $derived(
    isFriend ? 'friends' : requestStatus
  );

  async function handleAction(action) {
    loading = true;
    error = '';
    try {
      if (action === 'add') {
        await sendFriendRequest(userId);
        onadd();
      } else if (action === 'accept') {
        // Need request_id — the caller must pass this via a callback or we look it up
        // For now we rely on the parent to handle the full accept flow
        onaccept();
      } else if (action === 'reject') {
        onreject();
      } else if (action === 'remove') {
        await unfriend(userId);
        onremove();
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }
</script>

{#if status === 'friends'}
  <button class="btn-friend friend-remove" disabled={loading} onclick={() => handleAction('remove')}>
    {loading ? '...' : '✓ Friends'}
  </button>
{:else if status === 'pending_sent'}
  <button class="btn-friend friend-pending" disabled>
    ⏳ Request Sent
  </button>
{:else if status === 'pending_received'}
  <div class="friend-actions">
    <button class="btn-friend friend-accept" disabled={loading} onclick={() => handleAction('accept')}>
      {loading ? '...' : '✓ Accept'}
    </button>
    <button class="btn-friend friend-reject" disabled={loading} onclick={() => handleAction('reject')}>
      ✕ Decline
    </button>
  </div>
{:else}
  <button class="btn-friend friend-add" disabled={loading} onclick={() => handleAction('add')}>
    {loading ? '...' : '+ Add Friend'}
  </button>
{/if}

{#if error}
  <p class="friend-error">{error}</p>
{/if}

<style>
  .btn-friend {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    border-radius: var(--radius-xl);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }
  .btn-friend:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .friend-add {
    background: linear-gradient(135deg, var(--accent-terracotta), var(--accent-orange));
    color: var(--text-on-accent);
  }
  .friend-add:hover:not(:disabled) {
    box-shadow: var(--shadow-sm);
    transform: translateY(-1px);
  }

  .friend-remove {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border-color: var(--border-subtle);
  }
  .friend-remove:hover:not(:disabled) {
    border-color: var(--error);
    color: var(--error);
  }

  .friend-pending {
    background: var(--bg-tertiary);
    color: var(--text-muted);
    cursor: default;
  }

  .friend-actions {
    display: flex;
    gap: 6px;
  }

  .friend-accept {
    background: var(--success);
    color: white;
  }
  .friend-accept:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  .friend-reject {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border-color: var(--border-subtle);
  }
  .friend-reject:hover:not(:disabled) {
    border-color: var(--error);
    color: var(--error);
  }

  .friend-error {
    font-size: 0.75rem;
    color: var(--error);
    margin-top: 4px;
  }
</style>
