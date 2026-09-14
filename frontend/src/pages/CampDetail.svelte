<script>
  /**
   * CampDetail — camp detail page at /camps/:id.
   * Shows camp info, members list with roles, join/leave, promote/demote.
   */
  import { push } from 'svelte-spa-router';
  import { getCamp, listCampMembers, joinCamp, leaveCamp, promoteToModerator, demoteFromModerator } from '../lib/api/social.js';
  import { getTokenPayload } from '../lib/auth/token.js';

  let { params = {} } = $props();
  let campId = $derived(params.id || '');

  let camp = $state(null);
  let members = $state([]);
  let loading = $state(true);
  let error = $state('');
  let actionMsg = $state('');
  let actionError = $state('');

  let currentUserId = $derived(getTokenPayload()?.sub || '');

  let myMembership = $derived(members.find(m => m.user_id === currentUserId));
  let isMember = $derived(!!myMembership);
  let isLead = $derived(myMembership?.role === 'lead');

  async function loadCamp() {
    if (!campId) return;
    loading = true;
    error = '';
    try {
      const [campData, membersData] = await Promise.all([
        getCamp(campId),
        listCampMembers(campId),
      ]);
      camp = campData;
      members = membersData;
    } catch (e) {
      error = e.message || 'Failed to load camp';
    } finally {
      loading = false;
    }
  }

  async function handleJoin() {
    actionError = '';
    actionMsg = '';
    try {
      await joinCamp(campId);
      actionMsg = 'Joined camp!';
      await loadCamp();
    } catch (e) {
      actionError = e.message || 'Failed to join';
    }
  }

  async function handleLeave() {
    actionError = '';
    actionMsg = '';
    try {
      await leaveCamp(campId);
      actionMsg = 'Left camp';
      await loadCamp();
    } catch (e) {
      actionError = e.message || 'Failed to leave';
    }
  }

  async function handlePromote(userId) {
    actionError = '';
    actionMsg = '';
    try {
      await promoteToModerator(campId, userId);
      actionMsg = 'Promoted to moderator';
      await loadCamp();
    } catch (e) {
      actionError = e.message || 'Failed to promote';
    }
  }

  async function handleDemote(userId) {
    actionError = '';
    actionMsg = '';
    try {
      await demoteFromModerator(campId, userId);
      actionMsg = 'Demoted to member';
      await loadCamp();
    } catch (e) {
      actionError = e.message || 'Failed to demote';
    }
  }

  $effect(() => {
    if (campId) loadCamp();
  });

  function roleBadge(role) {
    if (role === 'lead') return '👑 Lead';
    if (role === 'moderator') return '⭐ Moderator';
    return '👥 Member';
  }

  function roleClass(role) {
    if (role === 'lead') return 'role-lead';
    if (role === 'moderator') return 'role-moderator';
    return 'role-member';
  }
</script>

<div class="detail-page">
  <button class="back-btn" onclick={() => push('/camps')}>← Back to Camps</button>

  {#if loading}
    <div class="loading-state"><p>Loading camp…</p></div>
  {:else if error}
    <div class="error-state">
      <p class="error-text">{error}</p>
      <button class="btn btn-secondary" onclick={loadCamp}>Retry</button>
    </div>
  {:else if camp}
    <div class="camp-header card">
      <div class="camp-icon-large">⛺</div>
      <div class="camp-info">
        <h1>{camp.name}</h1>
        {#if camp.description}
          <p class="camp-description">{camp.description}</p>
        {/if}
        {#if camp.location_on_playa}
          <p class="camp-location">📍 {camp.location_on_playa}</p>
        {/if}
        {#if camp.event_name}
          <p class="camp-event">🏕️ Part of <strong>{camp.event_name}</strong></p>
        {/if}
        <p class="camp-meta">👥 {camp.member_count || members.length} member{(camp.member_count || members.length) !== 1 ? 's' : ''}</p>
      </div>
      <div class="camp-actions">
        {#if isMember}
          <button class="btn btn-outline btn-leave" onclick={handleLeave}>Leave Camp</button>
        {:else}
          <button class="btn btn-primary" onclick={handleJoin}>Join Camp</button>
        {/if}
      </div>
    </div>

    {#if actionMsg}
      <div class="action-msg success-msg">{actionMsg}</div>
    {/if}
    {#if actionError}
      <div class="action-msg error-msg">{actionError}</div>
    {/if}

    <div class="members-section card">
      <h2>Members ({members.length})</h2>
      <div class="members-list">
        {#each members as member (member.user_id)}
          <div class="member-row">
            <div class="member-avatar">{member.display_name?.[0] || member.username[0]}</div>
            <div class="member-info">
              <span class="member-name">{member.display_name || member.username}</span>
              <span class="member-username">@{member.username}</span>
            </div>
            <span class="role-badge {roleClass(member.role)}">{roleBadge(member.role)}</span>
            {#if isLead && member.user_id !== currentUserId}
              <div class="member-actions">
                {#if member.role === 'member'}
                  <button class="btn btn-sm btn-secondary" onclick={() => handlePromote(member.user_id)} title="Promote to moderator">⭐</button>
                {:else if member.role === 'moderator'}
                  <button class="btn btn-sm btn-secondary" onclick={() => handleDemote(member.user_id)} title="Demote to member">👤</button>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .detail-page {
    max-width: 800px;
    margin: 0 auto;
    padding: 24px 24px 60px;
  }

  .back-btn {
    background: none;
    border: none;
    color: var(--accent-sand);
    font-size: 0.9rem;
    cursor: pointer;
    padding: 0 0 16px;
    display: inline-block;
  }
  .back-btn:hover {
    color: var(--accent-amber);
  }

  .camp-header {
    display: flex;
    gap: 20px;
    align-items: flex-start;
    padding: 24px;
    flex-wrap: wrap;
  }

  .camp-icon-large {
    font-size: 3rem;
    width: 72px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: var(--radius-lg);
    flex-shrink: 0;
  }

  .camp-info {
    flex: 1;
    min-width: 200px;
  }

  .camp-info h1 {
    font-size: 1.5rem;
    color: var(--accent-warm);
    margin: 0 0 8px;
  }

  .camp-description {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-bottom: 8px;
    line-height: 1.5;
  }

  .camp-location {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-bottom: 4px;
  }

  .camp-meta {
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  .camp-event {
    color: var(--accent-sand);
    font-size: 0.85rem;
    margin-bottom: 4px;
  }

  .camp-actions {
    flex-shrink: 0;
  }

  .action-msg {
    padding: 10px 16px;
    border-radius: var(--radius-md);
    margin: 12px 0;
    font-size: 0.9rem;
  }
  .success-msg {
    background: rgba(76, 175, 125, 0.15);
    color: var(--success);
    border: 1px solid rgba(76, 175, 125, 0.3);
  }
  .error-msg {
    background: rgba(212, 83, 74, 0.15);
    color: var(--error);
    border: 1px solid rgba(212, 83, 74, 0.3);
  }

  .members-section {
    padding: 24px;
    margin-top: 20px;
  }

  .members-section h2 {
    font-size: 1.1rem;
    color: var(--accent-warm);
    margin: 0 0 16px;
  }

  .members-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .member-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: var(--radius-md);
    transition: background var(--transition-fast);
  }
  .member-row:hover {
    background: var(--bg-tertiary);
  }

  .member-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--accent-terracotta);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
  }

  .member-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .member-name {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .member-username {
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .role-badge {
    font-size: 0.78rem;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
    white-space: nowrap;
  }
  .role-lead {
    background: rgba(212, 167, 106, 0.15);
    color: var(--accent-sand);
    border: 1px solid rgba(212, 167, 106, 0.3);
  }
  .role-moderator {
    background: rgba(93, 141, 212, 0.15);
    color: var(--info);
    border: 1px solid rgba(93, 141, 212, 0.3);
  }
  .role-member {
    background: rgba(176, 172, 158, 0.1);
    color: var(--text-secondary);
    border: 1px solid rgba(176, 172, 158, 0.15);
  }

  .member-actions {
    flex-shrink: 0;
  }

  .btn {
    padding: 10px 20px;
    border: none;
    border-radius: var(--radius-md);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .btn-primary {
    background: var(--accent-terracotta);
    color: white;
  }
  .btn-primary:hover {
    background: #b04e12;
  }
  .btn-secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
  }
  .btn-secondary:hover {
    background: var(--bg-hover);
  }
  .btn-outline {
    background: transparent;
    border: 1px solid var(--border-primary);
    color: var(--text-primary);
  }
  .btn-outline:hover {
    border-color: var(--accent-terracotta);
    color: var(--accent-terracotta);
  }
  .btn-leave:hover {
    border-color: var(--error);
    color: var(--error);
  }
  .btn-sm {
    padding: 4px 8px;
    font-size: 0.85rem;
    min-width: 32px;
  }

  .loading-state,
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 80px 24px;
    gap: 12px;
  }
  .loading-state p { color: var(--text-muted); }
  .error-text { color: var(--error); }

  @media (max-width: 768px) {
    .camp-header {
      flex-direction: column;
      align-items: stretch;
    }
    .camp-actions {
      width: 100%;
    }
    .camp-actions .btn {
      width: 100%;
    }
    .detail-page {
      padding: 16px 16px 40px;
    }
  }
</style>
