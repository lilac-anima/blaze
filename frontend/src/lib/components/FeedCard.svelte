<script>
  /**
   * FeedCard — post display with like/comment actions.
   * Props: post (PostResponse object), onlike, onunlike, oncomment, ondelete
   */
  import { push } from 'svelte-spa-router';
  import UserAvatar from './UserAvatar.svelte';
  import CommentThread from './CommentThread.svelte';
  import { likePost, unlikePost, deletePost } from '../api/social.js';
  import { getTokenPayload } from '../auth/token.js';

  let { post, ondelete = () => {} } = $props();

  let liked = $state(false);
  let likeCount = $state(0);
  let showComments = $state(false);
  let commentCount = $state(0);
  let loading = $state(false);
  let deleting = $state(false);

  // Sync from props on mount and when post reference changes
  $effect(() => {
    liked = post.is_liked_by_me || false;
    likeCount = post.like_count || 0;
    commentCount = post.comment_count || 0;
  });

  const currentUser = $derived(getTokenPayload());
  const isOwner = $derived(currentUser?.sub === post.author_id);

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

  async function toggleLike() {
    if (loading) return;
    loading = true;
    try {
      if (liked) {
        await unlikePost(post.post_id);
        liked = false;
        likeCount = Math.max(0, likeCount - 1);
      } else {
        await likePost(post.post_id);
        liked = true;
        likeCount += 1;
      }
    } catch (e) {
      console.error('Like failed:', e);
    } finally {
      loading = false;
    }
  }

  async function handleDelete() {
    if (!confirm('Delete this post?')) return;
    deleting = true;
    try {
      await deletePost(post.post_id);
      ondelete(post.post_id);
    } catch (e) {
      console.error('Delete failed:', e);
    } finally {
      deleting = false;
    }
  }

  function goToProfile() {
    push(`/profile/${post.author_username || post.author_id}`);
  }
</script>

<div class="feed-card card">
  <div class="card-header">
    <button class="author-btn" onclick={goToProfile}>
      <UserAvatar username={post.author_username} displayName={post.author_display_name} size="md" />
      <div class="author-info">
        <span class="author-name">{post.author_display_name || post.author_username || 'Unknown'}</span>
        <span class="post-time">@{post.author_username} · {timeAgo(post.created_at)}</span>
      </div>
    </button>

    <div class="card-actions-top">
      {#if isOwner}
        <button class="btn-icon btn-danger-icon" onclick={handleDelete} disabled={deleting} title="Delete">
          {deleting ? '...' : '🗑️'}
        </button>
      {/if}
    </div>
  </div>

  <div class="card-body">
    {#if post.sync_status}<span class="sync-status">{post.sync_status === 'pending' ? 'pending sync' : post.sync_status}</span>{/if}
    <p class="post-content">{post.content}</p>
    {#if post.image_url}
      <div class="post-image">
        <img src={post.image_url} alt="" loading="lazy" />
      </div>
    {/if}
  </div>

  <div class="card-actions">
    <button class="action-btn" class:liked onclick={toggleLike} disabled={loading}>
      <span>{liked ? '❤️' : '🤍'}</span>
      <span>{likeCount}</span>
    </button>
    <button class="action-btn" onclick={() => (showComments = !showComments)}>
      <span>💬</span>
      <span>{commentCount}</span>
    </button>
  </div>

  {#if showComments}
    <CommentThread {post} bind:commentCount />
  {/if}
</div>

<style>
  .feed-card {
    padding: 20px;
    transition: border-color var(--transition-fast);
  }
  .feed-card:hover {
    border-color: var(--border-primary);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 14px;
  }

  .author-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    padding: 0;
    text-align: left;
  }
  .author-btn:hover .author-name {
    color: var(--accent-sand);
  }

  .author-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .author-name {
    font-weight: 600;
    font-size: 0.95rem;
    transition: color var(--transition-fast);
  }

  .post-time {
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  .card-actions-top {
    display: flex;
    gap: 4px;
  }

  .btn-icon {
    background: none;
    border: none;
    padding: 4px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
    cursor: pointer;
    transition: background var(--transition-fast);
  }
  .btn-icon:hover {
    background: var(--bg-hover);
  }
  .btn-danger-icon:hover {
    background: rgba(212, 83, 74, 0.15);
  }

  .card-body {
    margin-bottom: 12px;
  }

  .post-content {
    font-size: 0.95rem;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .post-image {
    margin-top: 12px;
    border-radius: var(--radius-md);
    overflow: hidden;
  }
  .post-image img {
    width: 100%;
    max-height: 400px;
    object-fit: cover;
    display: block;
  }

  .card-actions {
    display: flex;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--border-subtle);
  }

  .action-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: var(--radius-xl);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    color: var(--text-secondary);
    font-size: 0.85rem;
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
  .action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
