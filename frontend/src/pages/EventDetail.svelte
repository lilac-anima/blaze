<script>
  /**
   * EventDetail — /events/:id
   * Full event detail with RSVP, attendee list, and creator controls.
   * Props: params (from svelte-spa-router, { id: event_id })
   */
  import { push } from 'svelte-spa-router';
  import { getEvent, listAttendees, deleteEvent, createEventPost, listEventPosts, likePost, unlikePost, deletePost } from '../lib/api/social.js';
  import { getTokenPayload } from '../lib/auth/token.js';
  import RSVPButton from '../lib/components/RSVPButton.svelte';
  import UserAvatar from '../lib/components/UserAvatar.svelte';

  let { params } = $props();

  let event = $state(null);
  let attendees = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let deleting = $state(false);

  let currentUser = $state(null);
  let eventPosts = $state([]);
  let postContent = $state('');
  let postSubmitting = $state(false);
  let postLoading = $state(true);

  // Current user info from JWT
  $effect(() => {
    currentUser = getTokenPayload();
  });

  // Load event and attendees
  $effect(() => {
    if (!params?.id) return;
    loadData(params.id);
  });

  async function loadData(eventId) {
    loading = true;
    error = null;
    try {
      const [eventData, attendeesData, postsData] = await Promise.all([
        getEvent(eventId),
        listAttendees(eventId),
        listEventPosts(eventId),
      ]);
      event = eventData;
      attendees = attendeesData;
      eventPosts = postsData;
    } catch (e) {
      console.error('Failed to load event:', e);
      error = 'Could not load event details. It may have been removed or you may not have access.';
    } finally {
      loading = false;
      postLoading = false;
    }
  }

  // Derived — current user is the event creator
  let isCreator = $derived(
    currentUser?.sub && event?.created_by && String(currentUser.sub) === String(event.created_by)
  );

  // Group attendees by RSVP status
  let groupedAttendees = $derived(() => {
    const groups = {
      going: [],
      maybe: [],
      'not going': [],
    };
    for (const a of attendees) {
      const key = a.rsvp_status || 'not going';
      if (groups[key]) {
        groups[key].push(a);
      } else {
        groups['not going'].push(a);
      }
    }
    return groups;
  });

  // Counts
  let attendeeCount = $derived(event?.attendee_count ?? groupedAttendees().going.length);
  let maxAttendees = $derived(event?.max_attendees ?? null);

  // Current user's RSVP status among attendees
  let myStatus = $derived(() => {
    if (!currentUser?.sub) return null;
    const match = attendees.find(
      (a) => String(a.user_id) === String(currentUser.sub)
    );
    return match?.rsvp_status || null;
  });

  // ── Event Post Actions ──────────────────────────────────────────

  async function handleCreatePost() {
    if (!postContent.trim() || postSubmitting) return;
    postSubmitting = true;
    try {
      const newPost = await createEventPost(event.event_id, postContent.trim());
      eventPosts = [newPost, ...eventPosts];
      postContent = '';
    } catch (e) {
      console.error('Failed to create post:', e);
    } finally {
      postSubmitting = false;
    }
  }

  async function handleLikePost(post) {
    try {
      await likePost(post.post_id);
      post.is_liked_by_me = true;
      post.like_count = (post.like_count || 0) + 1;
      eventPosts = eventPosts;
    } catch (e) {
      console.error('Like failed:', e);
    }
  }

  async function handleUnlikePost(post) {
    try {
      await unlikePost(post.post_id);
      post.is_liked_by_me = false;
      post.like_count = Math.max(0, (post.like_count || 0) - 1);
      eventPosts = eventPosts;
    } catch (e) {
      console.error('Unlike failed:', e);
    }
  }

  async function handleDeletePost(post) {
    if (!window.confirm('Delete this post?')) return;
    try {
      await deletePost(post.post_id);
      eventPosts = eventPosts.filter((p) => p.post_id !== post.post_id);
    } catch (e) {
      console.error('Delete failed:', e);
    }
  }

  async function handleDelete() {
    if (!window.confirm('🔥 Are you sure you want to delete this event?')) return;
    deleting = true;
    try {
      await deleteEvent(event.event_id);
      push('/events');
    } catch (e) {
      console.error('Failed to delete event:', e);
      error = 'Failed to delete event. Please try again.';
      deleting = false;
    }
  }

  function handleRSVPChange() {
    loadData(params.id);
  }

  function handleEdit() {
    push(`/events/${event.event_id}/edit`);
  }

  function formatDate(dateStr) {
    if (!dateStr) return null;
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  }

  function timeAgo(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const secs = Math.floor((now - d) / 1000);
    if (secs < 60) return 'just now';
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString();
  }
</script>

<div class="event-detail-page">
  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading event...</p>
    </div>
  {:else if error}
    <div class="error-state card">
      <span class="error-icon">⚠️</span>
      <p>{error}</p>
      <button class="btn btn-secondary" onclick={() => push('/events')}>
        ← Back to Events
      </button>
    </div>
  {:else if event}
    <!-- Event Header -->
    <div class="event-header card">
      <div class="event-header-top">
        <div class="event-title-row">
          <div class="event-icon-large">🎪</div>
          <div>
            <h1 class="event-name">{event.name}</h1>
            {#if event.camp_name || event.camp}
              <p class="event-camp">Part of <strong>{event.camp_name || event.camp}</strong></p>
            {/if}
          </div>
        </div>

        <!-- Creator Actions -->
        {#if isCreator}
          <div class="creator-actions">
            <button class="btn btn-secondary" onclick={handleEdit}>
              ✏️ Edit
            </button>
            <button
              class="btn btn-danger"
              onclick={handleDelete}
              disabled={deleting}
            >
              {deleting ? '🗑️ Deleting...' : '🗑️ Delete'}
            </button>
          </div>
        {/if}
      </div>

      <!-- Event Meta Row -->
      <div class="event-meta-row">
        {#if event.date}
          <div class="meta-item">
            <span class="meta-icon">📅</span>
            <span class="meta-value">{formatDate(event.date)}</span>
          </div>
        {/if}
        {#if event.location_on_playa}
          <div class="meta-item">
            <span class="meta-icon">📍</span>
            <span class="meta-value">{event.location_on_playa}</span>
          </div>
        {/if}
        {#if event.location}
          <div class="meta-item">
            <span class="meta-icon">📍</span>
            <span class="meta-value">{event.location}</span>
          </div>
        {/if}
      </div>

      <!-- Attendee Count vs Max -->
      <div class="attendance-bar">
        <div class="attendance-header">
          <span class="attendance-label">👥 Attendees</span>
          <span class="attendance-numbers">
            {attendeeCount}
            {#if maxAttendees}
              / {maxAttendees}
            {/if}
          </span>
        </div>
        {#if maxAttendees}
          <div class="progress-track">
            <div
              class="progress-fill"
              style="width: {Math.min((attendeeCount / maxAttendees) * 100, 100)}%"
            ></div>
          </div>
        {/if}
      </div>

      <!-- RSVP Section -->
      <div class="rsvp-section">
        <h3 class="section-label">Your RSVP</h3>
        <RSVPButton
          eventId={event.event_id}
          myStatus={myStatus()}
          onchange={handleRSVPChange}
        />
      </div>
    </div>

    <!-- Description -->
    {#if event.description}
      <div class="event-description card">
        <h3 class="section-label">📝 About this event</h3>
        <p class="description-text">{event.description}</p>
      </div>
    {/if}

    <!-- Attendee List -->
    <div class="attendee-section card">
      <h3 class="section-label">🎭 Attendees</h3>

      <!-- Going -->
      {#if groupedAttendees().going.length > 0}
        <div class="rsvp-group-block">
          <h4 class="rsvp-group-label going-label">
            🔥 Going <span class="rsvp-count">{groupedAttendees().going.length}</span>
          </h4>
          <div class="attendee-grid">
            {#each groupedAttendees().going as attendee (attendee.user_id)}
              <button
                class="attendee-chip"
                onclick={() => push(`/profile/${attendee.username}`)}
              >
                <UserAvatar
                  username={attendee.username}
                  displayName={attendee.display_name}
                  size="sm"
                />
                <span class="attendee-name">{attendee.display_name || attendee.username}</span>
              </button>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Maybe -->
      {#if groupedAttendees().maybe.length > 0}
        <div class="rsvp-group-block">
          <h4 class="rsvp-group-label maybe-label">
            🤔 Maybe <span class="rsvp-count">{groupedAttendees().maybe.length}</span>
          </h4>
          <div class="attendee-grid">
            {#each groupedAttendees().maybe as attendee (attendee.user_id)}
              <button
                class="attendee-chip"
                onclick={() => push(`/profile/${attendee.username}`)}
              >
                <UserAvatar
                  username={attendee.username}
                  displayName={attendee.display_name}
                  size="sm"
                />
                <span class="attendee-name">{attendee.display_name || attendee.username}</span>
              </button>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Not Going -->
      {#if groupedAttendees()['not going'].length > 0}
        <div class="rsvp-group-block">
          <h4 class="rsvp-group-label notgoing-label">
            🚫 Not Going <span class="rsvp-count">{groupedAttendees()['not going'].length}</span>
          </h4>
          <div class="attendee-grid">
            {#each groupedAttendees()['not going'] as attendee (attendee.user_id)}
              <button
                class="attendee-chip"
                onclick={() => push(`/profile/${attendee.username}`)}
              >
                <UserAvatar
                  username={attendee.username}
                  displayName={attendee.display_name}
                  size="sm"
                />
                <span class="attendee-name">{attendee.display_name || attendee.username}</span>
              </button>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Empty state -->
      {#if attendees.length === 0}
        <div class="attendee-empty">
          <span class="empty-icon">🏜️</span>
          <p>No RSVPs yet. Be the first!</p>
        </div>
      {/if}
    </div>

    <!-- Event Post Board -->
    <div class="post-board card">
      <h3 class="section-label">💬 Event Chat</h3>

      <!-- Post Composer -->
      <div class="post-composer">
        <textarea
          class="post-input"
          placeholder="Share something about this event..."
          bind:value={postContent}
          disabled={postSubmitting}
          maxlength="5000"
        ></textarea>
        <button
          class="btn btn-primary post-submit"
          onclick={handleCreatePost}
          disabled={!postContent.trim() || postSubmitting}
        >
          {postSubmitting ? '🔥 Posting...' : '🔥 Post'}
        </button>
      </div>

      <!-- Post List -->
      <div class="post-list">
        {#if postLoading}
          <div class="post-loading">
            <div class="spinner"></div>
            <p>Loading posts...</p>
          </div>
        {:else if eventPosts.length === 0}
          <div class="post-empty">
            <span class="empty-icon">💬</span>
            <p>No posts yet. Start the conversation!</p>
          </div>
        {:else}
          {#each eventPosts as post (post.post_id)}
            <div class="event-post-card">
              <div class="post-header">
                <button
                  class="post-author-btn"
                  onclick={() => push(`/profile/${post.author_username}`)}
                >
                  <UserAvatar
                    username={post.author_username}
                    displayName={post.author_display_name}
                    size="sm"
                  />
                  <div class="post-author-info">
                    <span class="post-author-name">{post.author_display_name || post.author_username || 'Unknown'}</span>
                    <span class="post-time">@{post.author_username} · {timeAgo(post.created_at)}</span>
                  </div>
                </button>
                {#if currentUser?.sub === post.author_id}
                  <button
                    class="btn-icon btn-danger-icon"
                    onclick={() => handleDeletePost(post)}
                    title="Delete"
                  >🗑️</button>
                {/if}
              </div>
              <div class="post-body">
                <p class="post-content">{post.content}</p>
              </div>
              <div class="post-actions">
                <button
                  class="action-btn"
                  class:liked={post.is_liked_by_me}
                  onclick={() => post.is_liked_by_me ? handleUnlikePost(post) : handleLikePost(post)}
                >
                  <span>{post.is_liked_by_me ? '❤️' : '🤍'}</span>
                  <span>{post.like_count || 0}</span>
                </button>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .event-detail-page {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  /* ── Loading ── */
  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 24px;
    gap: 16px;
    color: var(--text-muted);
  }

  .spinner {
    width: 36px;
    height: 36px;
    border: 3px solid var(--border-primary);
    border-top-color: var(--accent-sand);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ── Error ── */
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 12px;
    padding: 60px 24px;
  }

  .error-icon {
    font-size: 2.5rem;
  }

  .error-state p {
    color: var(--text-secondary);
    max-width: 400px;
  }

  /* ── Event Header ── */
  .event-header {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .event-header-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    flex-wrap: wrap;
  }

  .event-title-row {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    min-width: 0;
    flex: 1;
  }

  .event-icon-large {
    font-size: 2.5rem;
    flex-shrink: 0;
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
  }

  .event-name {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent-warm);
    word-break: break-word;
  }

  .event-camp {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-top: 4px;
  }

  .event-camp strong {
    color: var(--accent-sand);
  }

  .creator-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }

  .creator-actions .btn {
    font-size: 0.85rem;
    padding: 8px 16px;
  }

  /* ── Event Meta Row ── */
  .event-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-xl);
    font-size: 0.88rem;
  }

  .meta-icon {
    flex-shrink: 0;
  }

  .meta-value {
    color: var(--text-primary);
  }

  /* ── Attendance Bar ── */
  .attendance-bar {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .attendance-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .attendance-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .attendance-numbers {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--accent-sand);
  }

  .progress-track {
    height: 6px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-terracotta), var(--accent-amber));
    border-radius: 3px;
    transition: width 0.4s ease;
  }

  /* ── RSVP Section ── */
  .rsvp-section {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .section-label {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }

  /* ── Description ── */
  .event-description {
    line-height: 1.7;
  }

  .description-text {
    color: var(--text-primary);
    font-size: 0.95rem;
    white-space: pre-wrap;
    word-break: break-word;
  }

  /* ── Attendee Section ── */
  .attendee-section {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .rsvp-group-block {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .rsvp-group-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .rsvp-count {
    font-size: 0.8rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: var(--radius-xl);
    background: var(--bg-tertiary);
    color: var(--text-muted);
  }

  .going-label { color: var(--success); }
  .maybe-label { color: var(--accent-amber); }
  .notgoing-label { color: var(--text-muted); }

  .attendee-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .attendee-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px 6px 6px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    cursor: pointer;
    transition: all var(--transition-fast);
    font-family: inherit;
    font-size: inherit;
    color: var(--text-primary);
  }
  .attendee-chip:hover {
    border-color: var(--accent-sand);
    background: var(--bg-hover);
  }

  .attendee-name {
    font-size: 0.85rem;
    font-weight: 600;
  }

  .attendee-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 40px 24px;
    text-align: center;
  }

  .empty-icon {
    font-size: 2rem;
  }

  .attendee-empty p {
    color: var(--text-muted);
    font-size: 0.9rem;
  }

  /* ── Post Board ── */
  .post-board {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .post-composer {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .post-input {
    width: 100%;
    min-height: 64px;
    padding: 10px 12px;
    border-radius: var(--radius-md);
    background: var(--bg-input);
    border: 1px solid var(--border-primary);
    color: var(--text-primary);
    font-size: 0.9rem;
    resize: vertical;
    line-height: 1.5;
    font-family: inherit;
  }
  .post-input:focus {
    border-color: var(--accent-sand);
    box-shadow: 0 0 0 2px rgba(212, 167, 106, 0.15);
    outline: none;
  }

  .post-submit {
    align-self: flex-end;
    font-size: 0.85rem;
    padding: 8px 20px;
  }

  .post-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .post-loading,
  .post-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 32px 16px;
    text-align: center;
  }

  .post-loading p,
  .post-empty p {
    color: var(--text-muted);
    font-size: 0.88rem;
  }

  .event-post-card {
    padding: 16px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    transition: border-color var(--transition-fast);
  }
  .event-post-card:hover {
    border-color: var(--border-primary);
  }

  .post-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
  }

  .post-author-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    padding: 0;
    text-align: left;
  }
  .post-author-btn:hover .post-author-name {
    color: var(--accent-sand);
  }

  .post-author-info {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .post-author-name {
    font-weight: 600;
    font-size: 0.9rem;
    transition: color var(--transition-fast);
  }

  .post-time {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .btn-icon {
    background: none;
    border: none;
    padding: 4px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.85rem;
    cursor: pointer;
    transition: background var(--transition-fast);
  }
  .btn-icon:hover {
    background: var(--bg-hover);
  }
  .btn-danger-icon:hover {
    background: rgba(212, 83, 74, 0.15);
  }

  .post-body {
    margin-bottom: 8px;
  }

  .post-content {
    font-size: 0.9rem;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--text-primary);
  }

  .post-actions {
    display: flex;
    gap: 6px;
    padding-top: 8px;
    border-top: 1px solid var(--border-subtle);
  }

  .action-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: var(--radius-xl);
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    color: var(--text-secondary);
    font-size: 0.82rem;
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .action-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
  .action-btn.liked {
    color: var(--error);
    border-color: rgba(212, 83, 74, 0.3);
  }

  /* ── Responsive ── */
  @media (max-width: 640px) {
    .event-header-top {
      flex-direction: column;
    }

    .creator-actions {
      width: 100%;
    }

    .creator-actions .btn {
      flex: 1;
    }

    .event-name {
      font-size: 1.25rem;
    }

    .event-meta-row {
      flex-direction: column;
    }

    .meta-item {
      width: 100%;
    }
  }
</style>
