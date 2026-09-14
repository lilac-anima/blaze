<script>
  /**
   * Home Page — placeholder for the authenticated user's feed/dashboard.
   * This will be fleshed out when social features are built.
   */
  import { isAuthenticated } from '../lib/auth/token.js';
  import { getTokenPayload } from '../lib/auth/token.js';
  import PostComposer from '../lib/components/PostComposer.svelte';
  import FeedCard from '../lib/components/FeedCard.svelte';
  import { fetchFeed } from '../lib/api/social.js';

  let payload = $state(null);
  let greeting = $state('');

  let feedPosts = $state([]);
  let feedLoading = $state(true);
  let feedCursor = $state(null);
  let feedHasMore = $state(true);
  let feedError = $state('');

  $effect(() => {
    payload = getTokenPayload();
    const hours = new Date().getHours();
    if (hours < 12) greeting = 'Good morning';
    else if (hours < 18) greeting = 'Good afternoon';
    else greeting = 'Good evening';

    loadFeed();
  });

  async function loadFeed() {
    if (!feedHasMore || feedLoading) return;
    feedLoading = true;
    feedError = '';
    try {
      const data = await fetchFeed(feedCursor);
      if (data.items && data.items.length > 0) {
        feedPosts = [...feedPosts, ...data.items];
        feedCursor = data.next_cursor || null;
        feedHasMore = !!data.next_cursor;
      } else {
        feedHasMore = false;
      }
    } catch (e) {
      feedError = 'Could not load feed';
      console.error('Feed error:', e);
    } finally {
      feedLoading = false;
    }
  }

  function handleNewPost(post) {
    feedPosts = [{ post, author: null }, ...feedPosts];
  }

  function handleDeletePost(postId) {
    feedPosts = feedPosts.filter(f => f.post.post_id !== postId);
  }

  function handleScroll(e) {
    const el = e.target;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 300) {
      loadFeed();
    }
  }
</script>

{#if isAuthenticated()}
  <div class="home-page">
    <div class="home-header">
      <div>
        <h1>{greeting}, {payload?.username || 'Burner'} 🔥</h1>
        <p class="home-subtitle">Welcome to the playa — what's your adventure today?</p>
      </div>
      <div class="vibe-indicator">
        <span>✨ Feeling: </span>
        <span class="vibe-badge">Radiant</span>
      </div>
    </div>

    <div class="quick-actions">
      <a href="#/events" class="action-card">
        <span class="action-icon">🎪</span>
        <span class="action-label">Find Events</span>
      </a>
      <a href="#/camps" class="action-card">
        <span class="action-icon">⛺</span>
        <span class="action-label">Explore Camps</span>
      </a>
      <a href="#/groups" class="action-card">
        <span class="action-icon">🔗</span>
        <span class="action-label">Join Groups</span>
      </a>
      <a href="#/profile" class="action-card">
        <span class="action-icon">👤</span>
        <span class="action-label">My Profile</span>
      </a>
    </div>

    <PostComposer onpost={handleNewPost} />

    <div class="feed-content" onscroll={handleScroll}>
      {#if feedError}
        <div class="feed-error">
          <p>😵 {feedError}</p>
          <button class="btn btn-secondary" onclick={loadFeed}>Retry</button>
        </div>
      {:else if feedPosts.length === 0 && !feedLoading}
        <div class="feed-empty">
          <span class="feed-empty-icon">🏜️</span>
          <h3>Your feed is quiet</h3>
          <p>Connect with other burners and the dust will settle here.</p>
          <a href="#/friends" class="btn btn-secondary">Find Friends</a>
        </div>
      {:else}
        <div class="feed-stream">
          {#each feedPosts as item}
            <FeedCard post={item.post} ondelete={handleDeletePost} />
          {/each}
        </div>
        {#if feedLoading}
          <div class="feed-loading-more">
            <span>🔥 Loading more...</span>
          </div>
        {/if}
        {#if !feedHasMore && feedPosts.length > 0}
          <div class="feed-end">
            <span>✦ You've reached the edge of the playa ✦</span>
          </div>
        {/if}
      {/if}
    </div>
  </div>
{:else}
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-icon">🔥</div>
        <h1>Blaze</h1>
        <p class="subtitle">Connect with your tribe on and off the playa</p>
      </div>
      <div style="text-align: center;">
        <a href="#/login" class="btn btn-primary" style="margin-right: 10px;">Sign In</a>
        <a href="#/register" class="btn btn-secondary">Join the Burn</a>
      </div>
    </div>
  </div>
{/if}

<style>
  .home-page {
    max-width: 900px;
    margin: 0 auto;
  }

  .home-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 28px;
    flex-wrap: wrap;
    gap: 16px;
  }

  .home-header h1 {
    font-size: 1.6rem;
    color: var(--accent-warm);
  }

  .home-subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-top: 4px;
  }

  .vibe-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  .vibe-badge {
    font-weight: 600;
    color: var(--accent-sand);
  }

  .quick-actions {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 28px;
  }

  .action-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 18px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    transition: all var(--transition-fast);
    color: var(--text-primary);
    text-decoration: none;
  }
  .action-card:hover {
    background: var(--bg-hover);
    border-color: var(--accent-sand);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
  }

  .action-icon {
    font-size: 1.6rem;
  }

  .action-label {
    font-weight: 600;
    font-size: 0.95rem;
  }

  .feed-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-bottom: 28px;
  }

  .feed-error {
    text-align: center;
    padding: 40px 24px;
  }
  .feed-error p {
    color: var(--error);
    margin-bottom: 12px;
  }

  .feed-empty {
    text-align: center;
    padding: 60px 24px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .feed-empty-icon {
    font-size: 3rem;
  }

  .feed-empty h3 {
    font-size: 1.2rem;
    color: var(--text-primary);
  }

  .feed-empty p {
    color: var(--text-muted);
    font-size: 0.9rem;
    max-width: 350px;
  }

  .feed-stream {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .feed-loading-more {
    text-align: center;
    padding: 20px;
    color: var(--text-muted);
    font-size: 0.9rem;
  }

  .feed-end {
    text-align: center;
    padding: 24px;
    color: var(--text-muted);
    font-size: 0.85rem;
    font-style: italic;
  }

  .auth-icon {
    font-size: 3rem;
    margin-bottom: 12px;
  }
</style>
