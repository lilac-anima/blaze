<script>
  /**
   * UserAvatar — avatar circle with vibe indicator dot.
   * Props: username, displayName, vibe (emoji string), size ('sm'|'md'|'lg')
   */
  let { username = '?', displayName = null, vibe = null, size = 'md' } = $props();

  const initials = $derived(
    (displayName || username || '?').slice(0, 2).toUpperCase()
  );

  const colors = [
    '#d4a76a', '#c85a17', '#e8b86d', '#f4a840',
    '#d4874a', '#f0c28a', '#5b8dd4', '#4caf7d',
  ];
  const colorIndex = $derived(
    Math.abs((username || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % colors.length
  );
</script>

<div class="user-avatar avatar-{size}" style="background: {colors[colorIndex]}">
  <span class="initials">{initials}</span>
  {#if vibe}
    <span class="vibe-dot" title="Feeling: {vibe}">{vibe}</span>
  {/if}
</div>

<style>
  .user-avatar {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    flex-shrink: 0;
    font-weight: 700;
    color: var(--text-on-accent);
  }

  .initials {
    user-select: none;
  }

  .vibe-dot {
    position: absolute;
    bottom: -2px;
    right: -2px;
    font-size: 0.7rem;
    line-height: 1;
    border: 2px solid var(--bg-primary);
    border-radius: 50%;
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-card);
  }

  .avatar-sm { width: 32px; height: 32px; font-size: 0.75rem; }
  .avatar-md { width: 44px; height: 44px; font-size: 0.9rem; }
  .avatar-lg { width: 64px; height: 64px; font-size: 1.2rem; }
  .avatar-lg .vibe-dot { width: 22px; height: 22px; font-size: 0.8rem; }
</style>
