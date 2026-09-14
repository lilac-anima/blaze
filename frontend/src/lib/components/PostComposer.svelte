<script>
  /**
   * PostComposer — compose a new post with text + optional image.
   * Props: onpost(post) — called when post is created
   */
  import { createPost } from '../api/social.js';
  import { isLocalFirst, featureMode } from '../config/features.js';
  import { createLocalPost } from '../local/localRuntime.js';

  let { onpost = () => {} } = $props();

  let content = $state('');
  let imageUrl = $state('');
  let visibility = $state('public');
  let submitting = $state(false);
  let error = $state('');
  let showComposer = $state(false);

  const maxChars = 5000;

  async function handleSubmit() {
    if (!content.trim() || submitting) return;
    submitting = true;
    error = '';
    try {
      const post = isLocalFirst(featureMode)
        ? await createLocalPost(content.trim(), imageUrl.trim() || null, visibility)
        : await createPost(content.trim(), imageUrl.trim() || null);
      content = '';
      imageUrl = '';
      showComposer = false;
      onpost(post);
    } catch (e) {
      error = e.message;
    } finally {
      submitting = false;
    }
  }

  function cancel() {
    showComposer = false;
    content = '';
    imageUrl = '';
    error = '';
  }
</script>

{#if showComposer}
  <div class="composer-card card">
    <div class="composer-header">
      <h3>✨ New Post</h3>
      <div class="visibility-select">
        <select bind:value={visibility}>
          <option value="public">🌍 Public</option>
          <option value="friends">👥 Friends Only</option>
          <option value="camps">⛺ Camp Mates</option>
        </select>
      </div>
    </div>

    <textarea
      class="composer-textarea"
      placeholder="Share what's on your mind, burner... 🔥"
      bind:value={content}
      maxlength={maxChars}
      disabled={submitting}
    ></textarea>

    <div class="composer-extras">
      <div class="char-count" class:over={content.length > maxChars * 0.9}>
        {content.length}/{maxChars}
      </div>
      <div class="image-url-row">
        <input
          type="text"
          class="image-input"
          placeholder="Image URL (optional)"
          bind:value={imageUrl}
          disabled={submitting}
        />
      </div>
    </div>

    {#if error}
      <p class="composer-error">{error}</p>
    {/if}

    <div class="composer-actions">
      <button class="btn btn-secondary" onclick={cancel} disabled={submitting}>Cancel</button>
      <button
        class="btn btn-primary"
        onclick={handleSubmit}
        disabled={!content.trim() || submitting}
      >
        {submitting ? '🔥 Posting...' : '🔥 Share'}
      </button>
    </div>
  </div>
{:else}
  <button class="composer-trigger" onclick={() => (showComposer = true)}>
    <span class="trigger-icon">✍️</span>
    <span class="trigger-text">Share what's happening on the playa...</span>
  </button>
{/if}

<style>
  .composer-trigger {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 14px 18px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    color: var(--text-muted);
    font-size: 0.95rem;
    cursor: pointer;
    transition: all var(--transition-fast);
    text-align: left;
  }
  .composer-trigger:hover {
    border-color: var(--accent-sand);
    background: var(--bg-hover);
    color: var(--text-secondary);
  }

  .trigger-icon {
    font-size: 1.3rem;
  }

  .composer-card {
    padding: 20px;
  }

  .composer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .composer-header h3 {
    font-size: 1rem;
    color: var(--accent-warm);
  }

  .visibility-select select {
    padding: 4px 10px;
    border-radius: var(--radius-xl);
    font-size: 0.8rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    color: var(--text-secondary);
  }

  .composer-textarea {
    width: 100%;
    min-height: 100px;
    padding: 12px;
    border-radius: var(--radius-md);
    background: var(--bg-input);
    border: 1px solid var(--border-primary);
    color: var(--text-primary);
    font-size: 0.95rem;
    resize: vertical;
    line-height: 1.5;
  }
  .composer-textarea:focus {
    border-color: var(--accent-sand);
    box-shadow: 0 0 0 2px rgba(212, 167, 106, 0.15);
    outline: none;
  }

  .composer-extras {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 8px;
    gap: 12px;
    flex-wrap: wrap;
  }

  .char-count {
    font-size: 0.78rem;
    color: var(--text-muted);
  }
  .char-count.over {
    color: var(--warning);
  }

  .image-url-row {
    flex: 1;
    max-width: 350px;
  }

  .image-input {
    width: 100%;
    padding: 6px 10px;
    border-radius: var(--radius-sm);
    font-size: 0.82rem;
    background: var(--bg-input);
    border: 1px solid var(--border-primary);
    color: var(--text-primary);
  }
  .image-input:focus {
    border-color: var(--accent-sand);
    outline: none;
  }

  .composer-error {
    font-size: 0.82rem;
    color: var(--error);
    margin-top: 6px;
  }

  .composer-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 12px;
  }
</style>
