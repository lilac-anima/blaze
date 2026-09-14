<script>
  /**
   * CommentThread — display and add comments on a post.
   * Props: post, bind:commentCount
   */
  import { addComment, listComments } from '../api/social.js';
  import { getTokenPayload } from '../auth/token.js';
  import UserAvatar from './UserAvatar.svelte';

  let { post, commentCount = $bindable() } = $props();

  let comments = $state([]);
  let loading = $state(false);
  let newComment = $state('');
  let submitting = $state(false);

  const currentUser = $derived(getTokenPayload());

  $effect(() => {
    loadComments();
  });

  async function loadComments() {
    loading = true;
    try {
      comments = await listComments(post.post_id);
    } catch (e) {
      console.error('Failed to load comments:', e);
    } finally {
      loading = false;
    }
  }

  async function handleSubmit() {
    if (!newComment.trim() || submitting) return;
    submitting = true;
    try {
      await addComment(post.post_id, newComment.trim());
      newComment = '';
      commentCount += 1;
      await loadComments();
    } catch (e) {
      console.error('Failed to add comment:', e);
    } finally {
      submitting = false;
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
    return d.toLocaleDateString();
  }
</script>

<div class="comment-section">
  {#if loading}
    <div class="comment-loading">Loading comments...</div>
  {:else if comments.length === 0}
    <div class="comment-empty">No comments yet. Be the first to spark a conversation!</div>
  {:else}
    <div class="comment-list">
      {#each comments as comment}
        <div class="comment-item">
          <UserAvatar username={comment.username} displayName={comment.display_name} size="sm" />
          <div class="comment-body">
            <div class="comment-header">
              <span class="comment-author">{comment.display_name || comment.username}</span>
              <span class="comment-time">{timeAgo(comment.created_at)}</span>
            </div>
            <p class="comment-text">{comment.content}</p>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <div class="comment-input-wrap">
    <input
      type="text"
      class="comment-input"
      placeholder="Write a comment..."
      bind:value={newComment}
      onkeydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
      disabled={submitting}
    />
    <button
      class="comment-submit"
      onclick={handleSubmit}
      disabled={!newComment.trim() || submitting}
    >
      {submitting ? '...' : 'Post'}
    </button>
  </div>
</div>

<style>
  .comment-section {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--border-subtle);
  }

  .comment-loading, .comment-empty {
    text-align: center;
    padding: 16px;
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  .comment-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 12px;
    max-height: 300px;
    overflow-y: auto;
  }

  .comment-item {
    display: flex;
    gap: 8px;
    align-items: flex-start;
  }

  .comment-body {
    flex: 1;
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
    padding: 8px 12px;
  }

  .comment-header {
    display: flex;
    gap: 8px;
    align-items: baseline;
    margin-bottom: 2px;
  }

  .comment-author {
    font-size: 0.85rem;
    font-weight: 600;
  }

  .comment-time {
    font-size: 0.72rem;
    color: var(--text-muted);
  }

  .comment-text {
    font-size: 0.88rem;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-word;
  }

  .comment-input-wrap {
    display: flex;
    gap: 8px;
  }

  .comment-input {
    flex: 1;
    padding: 8px 12px;
    font-size: 0.88rem;
    border-radius: var(--radius-xl);
    background: var(--bg-input);
    border: 1px solid var(--border-primary);
    color: var(--text-primary);
  }
  .comment-input:focus {
    border-color: var(--accent-sand);
    box-shadow: 0 0 0 2px rgba(212, 167, 106, 0.15);
    outline: none;
  }

  .comment-submit {
    padding: 8px 16px;
    border-radius: var(--radius-xl);
    background: linear-gradient(135deg, var(--accent-terracotta), var(--accent-orange));
    color: var(--text-on-accent);
    font-weight: 600;
    font-size: 0.85rem;
    border: none;
    cursor: pointer;
    white-space: nowrap;
  }
  .comment-submit:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .comment-submit:hover:not(:disabled) {
    box-shadow: var(--shadow-sm);
  }
</style>
