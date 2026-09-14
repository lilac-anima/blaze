<script>
  /**
   * Modal — reusable modal overlay.
   * Props:
   *   open        (boolean)   — show/hide
   *   title       (string)    — modal heading
   *   onclose     (function)  — called when user tries to close
   * Usage:
   *   <Modal open={show} title="Create Camp" onclose={() => (show = false)}>
   *     <p>content</p>
   *   </Modal>
   */
  let { open = false, title = '', onclose = () => {}, children } = $props();

  function handleKeydown(e) {
    if (e.key === 'Escape') onclose();
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) onclose();
  }

  // focus trap — auto-focus close button on open
  $effect(() => {
    if (open) {
      const btn = document.querySelector('.modal-close');
      btn?.focus();
    }
  });
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="modal-backdrop"
    role="dialog"
    aria-modal="true"
    aria-label={title || 'Modal'}
    tabindex="-1"
    onclick={handleBackdropClick}
    onkeydown={handleKeydown}
  >
    <div class="modal-panel card">
      <div class="modal-header">
        <h2 class="modal-title">{title}</h2>
        <button class="modal-close" onclick={onclose} aria-label="Close modal">&times;</button>
      </div>
      <div class="modal-body">
        {@render children?.()}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(3px);
    animation: fadeIn 150ms ease;
  }

  .modal-panel {
    width: 100%;
    max-width: 480px;
    max-height: 90vh;
    overflow-y: auto;
    padding: 0;
    animation: slideUp 200ms ease;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px 0;
  }

  .modal-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--accent-warm);
  }

  .modal-close {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: 50%;
    color: var(--text-secondary);
    font-size: 1.3rem;
    line-height: 1;
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .modal-close:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-color: var(--accent-sand);
  }
  .modal-close:focus-visible {
    outline: 2px solid var(--accent-sand);
    outline-offset: 2px;
  }

  .modal-body {
    padding: 16px 24px 24px;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
  }
</style>
