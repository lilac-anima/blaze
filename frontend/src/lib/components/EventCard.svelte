<script>
  /**
   * EventCard — event card for lists.
   * Props: event (EventResponse object)
   */
  import { push } from 'svelte-spa-router';

  let { event } = $props();

  function goToDetail() {
    push(`/events/${event.event_id}`);
  }
</script>

<div class="event-card card" onclick={goToDetail} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && goToDetail()}>
  <div class="event-icon">🎪</div>
  <div class="event-info">
    <h3 class="event-name">{event.name}</h3>
    {#if event.date}
      <p class="event-date">📅 {event.date}</p>
    {/if}
    {#if event.camp}
      <p class="event-camp">⛺ {event.camp}</p>
    {/if}
    {#if event.location_on_playa}
      <p class="event-location">📍 {event.location_on_playa}</p>
    {/if}
  </div>
  <div class="event-meta">
    <span class="attendee-count" title="Attendees">
      👥 {event.attendee_count || 0}
    </span>
    {#if event.max_attendees}
      <span class="max-badge">
        {event.attendee_count || 0}/{event.max_attendees}
      </span>
    {/if}
  </div>
</div>

<style>
  .event-card {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    padding: 18px;
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  .event-card:hover {
    border-color: var(--accent-sand);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
  }
  .event-card:focus-visible {
    outline: 2px solid var(--accent-sand);
    outline-offset: 2px;
  }

  .event-icon {
    font-size: 2rem;
    flex-shrink: 0;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
  }

  .event-info {
    flex: 1;
    min-width: 0;
  }

  .event-name {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--accent-warm);
  }

  .event-date, .event-camp, .event-location {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-top: 2px;
  }

  .event-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    flex-shrink: 0;
  }

  .attendee-count {
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  .max-badge {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: var(--radius-xl);
    background: var(--bg-tertiary);
    color: var(--text-muted);
  }
</style>
