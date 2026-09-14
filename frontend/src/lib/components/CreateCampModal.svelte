<script>
  /**
   * CreateCampModal — modal form for creating a new camp.
   * Props:
   *   onsaved   (function)  — called after successful creation
   *   onclose   (function)  — called when user cancels/closes
   */
  import { createCamp, searchEvents } from '../api/social.js';
  import Modal from './Modal.svelte';
  import SearchableDropdown from './SearchableDropdown.svelte';

  let { onsaved = () => {}, onclose = () => {} } = $props();

  let name = $state('');
  let description = $state('');
  let locationOnPlaya = $state('');
  let selectedEventId = $state('');
  let selectedEventName = $state('');
  let saving = $state(false);
  let error = $state('');
  let nameError = $state('');

  function validate() {
    nameError = '';
    error = '';
    if (!name.trim() || name.trim().length < 2) {
      nameError = 'Camp name is required (min 2 characters)';
      return false;
    }
    return true;
  }

  function handleEventSelect(item) {
    selectedEventId = item.event_id;
    selectedEventName = item.name;
  }

  function handleEventClear() {
    selectedEventId = '';
    selectedEventName = '';
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validate()) return;

    saving = true;
    error = '';
    try {
      await createCamp({
        name: name.trim(),
        description: description.trim() || undefined,
        location_on_playa: locationOnPlaya.trim() || undefined,
        event_id: selectedEventId || undefined,
      });
      onsaved();
    } catch (e) {
      error = e.message || 'Failed to create camp';
    } finally {
      saving = false;
    }
  }

  function handleClose() {
    if (!saving) onclose();
  }
</script>

<Modal open={true} title="Create a Camp" {onclose}>
  <form class="create-form" onsubmit={handleSubmit}>
    {#if error}
      <div class="form-error">{error}</div>
    {/if}

    <div class="form-group">
      <label for="camp-name" class="form-label">Camp Name *</label>
      <input
        id="camp-name"
        type="text"
        class="form-input"
        class:input-error={nameError}
        placeholder="e.g. Spanky's Wine Bar"
        bind:value={name}
        disabled={saving}
      />
      {#if nameError}
        <p class="field-error">{nameError}</p>
      {/if}
    </div>

    <div class="form-group">
      <label for="camp-desc" class="form-label">Description</label>
      <textarea
        id="camp-desc"
        class="form-input form-textarea"
        placeholder="What's your camp about?"
        bind:value={description}
        disabled={saving}
        rows="3"
      ></textarea>
    </div>

    <div class="form-group">
      <label for="camp-location" class="form-label">Location on Playa</label>
      <input
        id="camp-location"
        type="text"
        class="form-input"
        placeholder="e.g. 7:15 &amp; Esplanade"
        bind:value={locationOnPlaya}
        disabled={saving}
      />
    </div>

    <div class="form-group">
      <label for="camp-event" class="form-label">Event</label>
      <SearchableDropdown
        searchFn={searchEvents}
        labelKey="name"
        valueKey="event_id"
        placeholder="Search events…"
        onselect={handleEventSelect}
        onclear={handleEventClear}
        disabled={saving}
      />
    </div>

    <div class="form-actions">
      <button type="button" class="btn btn-secondary" onclick={handleClose} disabled={saving}>Cancel</button>
      <button type="submit" class="btn btn-primary" disabled={saving}>
        {saving ? 'Creating…' : 'Create Camp'}
      </button>
    </div>
  </form>
</Modal>

<style>
  .create-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .form-error {
    padding: 8px 12px;
    border-radius: var(--radius-sm);
    background: rgba(212, 83, 74, 0.15);
    color: var(--error);
    border: 1px solid rgba(212, 83, 74, 0.3);
    font-size: 0.85rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .form-input {
    padding: 10px 12px;
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    background: var(--bg-input);
    color: var(--text-primary);
    font-size: 0.9rem;
    transition: border-color var(--transition-fast);
    width: 100%;
    box-sizing: border-box;
  }

  .form-input:focus {
    outline: none;
    border-color: var(--accent-sand);
  }

  .form-input.input-error {
    border-color: var(--error);
  }

  .form-select {
    cursor: pointer;
    appearance: auto;
    padding-right: 8px;
  }

  .form-textarea {
    resize: vertical;
    min-height: 60px;
    font-family: inherit;
  }

  .field-error {
    color: var(--error);
    font-size: 0.8rem;
    margin: 0;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding-top: 8px;
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
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn-primary {
    background: var(--accent-terracotta);
    color: white;
  }
  .btn-primary:hover:not(:disabled) {
    background: #b04e12;
  }
  .btn-secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
  }
  .btn-secondary:hover:not(:disabled) {
    background: var(--bg-hover);
  }
</style>
