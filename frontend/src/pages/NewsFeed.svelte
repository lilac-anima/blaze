<script>
  /**
   * NewsFeed — infinite-scrolling feed page at /feed.
   * Shows PostComposer at top, loads feed via fetchFeed(),
   * renders FeedCard for each post, loads more on scroll to bottom.
   * Cursor-based pagination via fetchFeed(cursor).
   */
  import { push } from 'svelte-spa-router';
  import { fetchFeed } from '../lib/api/social.js';
  import { isLocalFirst, featureMode } from '../lib/config/features.js';
  import { readLocalFeed } from '../lib/local/localRuntime.js';
  import PostComposer from '../lib/components/PostComposer.svelte';
  import FeedCard from '../lib/components/FeedCard.svelte';

  let posts = $state([]);
  let cursor = $state(null);
  let loading = $state(false);
  let loadingMore = $state(false);
  let hasMore = $state(true);
  let error = $state('');
  let sentinel = $state(null);

  // ── Load initial feed ──────────────────────────────────────────

  async function loadFeed() {
    loading = true;
    error = '';
    try {
      if (isLocalFirst(featureMode)) {
        posts = await readLocalFeed();
        cursor = null;
        hasMore = false;
      } else {
        const data = await fetchFeed();
        posts = data.posts || [];
        cursor = data.next_cursor || null;
        hasMore = !!data.next_cursor;
      }
    } catch (e) {
      error = e.message || 'Failed to load feed';
      posts = [];
    } finally {
      loading = false;
    }
  }

  // ── Load more (cursor-based pagination) ────────────────────────

  async function loadMore() {
    if (loadingMore || !hasMore) return;
    loadingMore = true;
    try {
      const data = await fetchFeed(cursor);
      const newPosts = data.posts || [];
      posts = [...posts, ...newPosts];
      cursor = data.next_cursor || null;
      hasMore = !!data.next_cursor;
    } catch (e) {
      console.error('Load more failed:', e);
    } finally {
      loadingMore = false;
    }
  }

  // ── PostComposer callback: prepend new post ────────────────────

  function handleNewPost(post) {
    posts = [post, ...posts];
  }

  // ── FeedCard delete callback: remove from list ─────────────────

  function handleDelete(postId) {
    posts = posts.filter((p) => p.post_id !== postId);
  }

  // ── IntersectionObserver for infinite scroll ───────────────────

  $effect(() => {
    if (!sentinel || !hasMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMore();
        }
      },
      { rootMargin: '200px' }
    );

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
    };
  });

  // ── Load on mount ──────────────────────────────────────────────

  $effect(() => {
    loadFeed();
  });
</script>

<div class="news-feed-page">
  <!-- Page Header -->
  <div class="feed-header">
    <h1>🔥 Your Feed</h1>
    <p class="feed-subtitle">Stay connected with the burn community</p>
  </div>

  <!-- Post Composer -->
  <div class="feed-composer">
    <PostComposer onpost={handleNewPost} />
  </div>

  <!-- Loading State -->
  {#if loading}
    <div class="feed-status">
      <div class="spinner"></div>
      <span>Loading the playa dust...</span>
    </div>
  {:else if error}
    <!-- Error State -->
    <div class="feed-status feed-error">
      <span class="status-icon">⚠️</span>
      <p>{error}</p>
      <button class="btn btn-secondary" onclick={loadFeed}>Try Again</button>
    </div>
  {:else if posts.length === 0}
    <!-- Empty State -->
    <div class="feed-empty card">
      <div class="feed-empty-inner">
        <span class="empty-icon">🏜️</span>
        <h3>The playa is quiet today</h3>
        <p>No posts yet. Be the first to share something with the burn community!</p>
        <button class="btn btn-primary" onclick={() => push('/explore')}>
          Explore the Playa
        </button>
      </div>
    </div>
  {:else}
    <!-- Feed Posts -->
    <div class="feed-list">
      {#each posts as post (post.post_id)}
        <FeedCard {post} ondelete={handleDelete} />
      {/each}
    </div>

    <!-- Sentinel for infinite scroll -->
    <div
      bind:this={sentinel}
      class="feed-sentinel"
      class:loading={loadingMore}
    >
      {#if loadingMore}
        <div class="load-more-indicator">
          <div class="spinner spinner-sm"></div>
          <span>Loading more...</span>
        </div>
      {:else if !hasMore}
        <div class="feed-end">
          <span>🌅 You've caught up with the playa</span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .news-feed-page {
    max-width: 680px;
    margin: 0 auto;
    padding: 0 0 40px;
  }

  /* ── Header ── */

  .feed-header {
    margin-bottom: 20px;
  }

  .feed-header h1 {
    font-size: 1.5rem;
    color: var(--accent-warm);
    font-weight: 700;
  }

  .feed-subtitle {
    font-size: 0.9rem;
    color: var(--text-muted);
    margin-top: 4px;
  }

  /* ── Composer ── */

  .feed-composer {
    margin-bottom: 20px;
  }

  /* ── Feed List ── */

  .feed-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  /* ── Status & States ── */

  .feed-status {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 60px 24px;
    color: var(--text-secondary);
    font-size: 0.95rem;
  }

  .feed-error {
    color: var(--error);
  }

  .status-icon {
    font-size: 2rem;
  }

  /* ── Empty State ── */

  .feed-empty {
    text-align: center;
    padding: 60px 24px;
  }

  .feed-empty-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .empty-icon {
    font-size: 3rem;
  }

  .feed-empty-inner h3 {
    font-size: 1.2rem;
    color: var(--text-primary);
  }

  .feed-empty-inner p {
    color: var(--text-muted);
    font-size: 0.9rem;
    max-width: 360px;
    line-height: 1.5;
  }

  /* ── Sentinel / Infinite Scroll ── */

  .feed-sentinel {
    min-height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 12px;
  }

  .load-more-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--text-muted);
    font-size: 0.85rem;
    padding: 16px;
  }

  .feed-end {
    padding: 24px 16px;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
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

  .spinner-sm {
    width: 20px;
    height: 20px;
    border-width: 2px;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* ── Mobile Responsive ── */

  @media (max-width: 768px) {
    .news-feed-page {
      padding: 0 0 24px;
    }

    .feed-header {
      margin-bottom: 16px;
    }

    .feed-header h1 {
      font-size: 1.25rem;
    }

    .feed-composer {
      margin-bottom: 16px;
    }

    .feed-list {
      gap: 10px;
    }

    .feed-status {
      padding: 40px 16px;
    }

    .feed-empty {
      padding: 40px 16px;
    }
  }
</style>
