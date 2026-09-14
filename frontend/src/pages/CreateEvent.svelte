<script>
  /**
   * CreateEvent — create event page at /events/new.
   */
  import { push } from 'svelte-spa-router';
  import { createEvent, searchCamps } from '../lib/api/social.js';
  import SearchableDropdown from '../lib/components/SearchableDropdown.svelte';

  let name = $state('');
  let date = $state('');
  let description = $state('');
  let locationOnPlaya = $state('');
  let camp = $state('');
  let maxAttendees = $state('');
  let saving = $state(false);
  let error = $state('');
  let fieldErrors = $state({});

  function validate() {
    const errs = {};
    if (!name.trim() || name.trim().length < 2) errs.name = 'Event name is required';
    if (!date.trim()) errs.date = 'Date is required';
    if (maxAttendees && (isNaN(maxAttendees) || parseInt(maxAttendees) < 1)) errs.maxAttendees = 'Must be a positive number';
    fieldErrors = errs;
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validate()) return;

    saving = true;
    error = '';
    try {
      await createEvent({
        name: name.trim(),
        date: date.trim(),
        description: description.trim() || undefined,
        location_on_playa: locationOnPlaya.trim() || undefined,
        camp: camp.trim() || undefined,
        max_attendees: maxAttendees ? parseInt(maxAttendees) : undefined,
      });
      push('/events');
    } catch (e) {
      error = e.message || 'Failed to create event';
    } finally {
      saving = false;
    }
  }
</script>

<div class="create-page">
  <button class="back-btn" onclick={() => push('/events')}>← Back to Events</button>

  <div class="form-card card">
    <h1>Create Event</h1>

    {#if error}
      <div class="form-error">{error}</div>
    {/if}

    <form onsubmit={handleSubmit}>
      <div class="form-group">
        <label for="ev-name" class="form-label">Event Name *</label>
        <input id="ev-name" type="text" class="form-input" class:input-error={fieldErrors.name}
          placeholder="e.g. Burning Man 2025" bind:value={name} disabled={saving} />
        {#if fieldErrors.name}<p class="field-error">{fieldErrors.name}</p>{/if}
      </div>

      <div class="form-group">
        <label for="ev-date" class="form-label">Date *</label>
        <input id="ev-date" type="date" class="form-input" class:input-error={fieldErrors.date}
          bind:value={date} disabled={saving} />
        {#if fieldErrors.date}<p class="field-error">{fieldErrors.date}</p>{/if}
      </div>

      <div class="form-group">
        <label for="ev-desc" class="form-label">Description</label>
        <textarea id="ev-desc" class="form-input form-textarea" placeholder="What's the event about?"
          bind:value={description} disabled={saving} rows="4"></textarea>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="ev-loc" class="form-label">Location on Playa</label>
          <input id="ev-loc" type="text" class="form-input" placeholder="e.g. 7:15 &amp; Esplanade"
            bind:value={locationOnPlaya} disabled={saving} />
        </div>
        <div class="form-group">
          <label for="ev-camp" class="form-label">Host Camp</label>
          <SearchableDropdown
            searchFn={searchCamps}
            labelKey="name"
            valueKey="camp_id"
            placeholder="Search camps…"
            onselect={(item) => camp = item.name}
            oninput={(val) => camp = val}
            disabled={saving}
          />
        </div>
      </div>

      <div class="form-group">
        <label for="ev-max" class="form-label">Max Attendees <span class="label-hint">(optional)</span></label>
        <input id="ev-max" type="number" min="1" class="form-input form-input-short" class:input-error={fieldErrors.maxAttendees}
          placeholder="Leave blank for unlimited" bind:value={maxAttendees} disabled={saving} />
        {#if fieldErrors.maxAttendees}<p class="field-error">{fieldErrors.maxAttendees}</p>{/if}
      </div>

      <div class="form-actions">
        <button type="button" class="btn btn-secondary" onclick={() => push('/events')} disabled={saving}>Cancel</button>
        <button type="submit" class="btn btn-primary" disabled={saving}>
          {saving ? 'Creating…' : 'Create Event'}
        </button>
      </div>
    </form>
  </div>
</div>

<style>
  .create-page { max-width: 600px; margin: 0 auto; padding: 24px 24px 60px; }
  .back-btn { background: none; border: none; color: var(--accent-sand); font-size: 0.9rem; cursor: pointer; padding: 0 0 16px; display: inline-block; }
  .back-btn:hover { color: var(--accent-amber); }
  .form-card { padding: 28px; }
  .form-card h1 { font-size: 1.4rem; color: var(--accent-warm); margin: 0 0 24px; }
  .form-error {
    padding: 8px 12px; border-radius: var(--radius-sm);
    background: rgba(212,83,74,0.15); color: var(--error);
    border: 1px solid rgba(212,83,74,0.3); font-size: 0.85rem; margin-bottom: 16px;
  }
  form { display: flex; flex-direction: column; gap: 18px; }
  .form-group { display: flex; flex-direction: column; gap: 6px; flex: 1; }
  .form-row { display: flex; gap: 16px; }
  .form-label { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); }
  .label-hint { font-weight: 400; color: var(--text-muted); font-size: 0.8rem; }
  .form-input {
    padding: 10px 12px; border: 1px solid var(--border-primary); border-radius: var(--radius-md);
    background: var(--bg-input); color: var(--text-primary); font-size: 0.9rem;
    transition: border-color var(--transition-fast); width: 100%; box-sizing: border-box;
  }
  .form-input:focus { outline: none; border-color: var(--accent-sand); }
  .form-input.input-error { border-color: var(--error); }
  .form-input-short { max-width: 200px; }
  .form-textarea { resize: vertical; min-height: 80px; font-family: inherit; }
  .field-error { color: var(--error); font-size: 0.8rem; margin: 0; }
  .form-actions { display: flex; justify-content: flex-end; gap: 10px; padding-top: 8px; }
  .btn {
    padding: 10px 20px; border: none; border-radius: var(--radius-md);
    font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: all var(--transition-fast);
  }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-primary { background: var(--accent-terracotta); color: white; }
  .btn-primary:hover:not(:disabled) { background: #b04e12; }
  .btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); border: 1px solid var(--border-primary); }
  .btn-secondary:hover:not(:disabled) { background: var(--bg-hover); }
  @media (max-width: 768px) {
    .form-row { flex-direction: column; gap: 18px; }
    .create-page { padding: 16px 16px 40px; }
    .form-card { padding: 20px; }
  }
</style>
