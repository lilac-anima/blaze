<script>
  /**
   * SearchableDropdown — async search-as-you-type dropdown.
   *
   * Props:
   *   searchFn       (async (query: string) => any[]) — required, e.g. searchEvents
   *   labelKey       (string | (item) => string)       — property or fn to get display text
   *   valueKey       (string)                          — property to use as item key (default 'id')
   *   placeholder    (string)                          — input placeholder
   *   onselect       (item) => void                    — called when user picks an item
   *   onclear        () => void                        — called when user clears the selection
   *   initialQuery   (string)                          — pre-fill the search field
   *   minQueryLength (number)                          — min chars before searching (default 2)
   *   debounceMs     (number)                          — debounce delay in ms (default 300)
   *   disabled       (boolean)                         — disable the input
   *   value          (any)                             — optional controlled selected value
   *
   * Usage:
   *   <SearchableDropdown
   *     searchFn={searchEvents}
   *     labelKey="name"
   *     valueKey="event_id"
   *     placeholder="Search events…"
   *     onselect={(e) => selectedEvent = e}
   *   />
   */
  import { tick } from 'svelte';

  let {
    searchFn,
    labelKey = 'name',
    valueKey = 'id',
    placeholder = 'Search…',
    onselect = () => {},
    onclear = () => {},
    oninput = () => {},
    initialQuery = '',
    minQueryLength = 2,
    debounceMs = 300,
    disabled = false,
    value = undefined,
  } = $props();

  // svelte-ignore state_referenced_locally — intentional: only want the initial value
  let query = $state(initialQuery);
  let items = $state([]);
  let loading = $state(false);
  let error = $state('');
  let open = $state(false);
  let highlightedIndex = $state(-1);
  let lastSelectedLabel = $state('');

  let inputEl = $state(null);
  let listEl = $state(null);
  let debounceTimer = $state(0);
  /** @type {ReturnType<setTimeout>|null} */

  /** Resolve display text from an item. */
  function getLabel(item) {
    if (typeof labelKey === 'function') return labelKey(item);
    return item?.[labelKey] ?? '';
  }

  /** Resolve value from an item. */
  function getValue(item) {
    return item?.[valueKey];
  }

  /** Perform the actual search. */
  async function doSearch(q) {
    if (!q || q.length < minQueryLength) {
      items = [];
      open = false;
      return;
    }
    loading = true;
    error = '';
    try {
      const data = await searchFn(q);
      // searchEvents and searchCamps return the array directly from listEvents/listCamps
      items = Array.isArray(data) ? data : (data?.events ?? data?.camps ?? data?.results ?? []);
      open = items.length > 0;
      highlightedIndex = -1;
    } catch (e) {
      error = e.message || 'Search failed';
      items = [];
    } finally {
      loading = false;
    }
  }

  /** Debounced search handler. */
  function handleInput(e) {
    query = e.target.value;
    oninput(query);
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => doSearch(query), debounceMs);
  }

  /** Select an item. */
  function selectItem(item) {
    lastSelectedLabel = getLabel(item);
    query = lastSelectedLabel;
    items = [];
    open = false;
    highlightedIndex = -1;
    onselect(item);
  }

  /** Clear the current selection. */
  function handleClear() {
    query = '';
    items = [];
    open = false;
    highlightedIndex = -1;
    lastSelectedLabel = '';
    onclear();
  }

  /** Keyboard navigation. */
  function handleKeydown(e) {
    if (!open || items.length === 0) {
      if (e.key === 'Escape') {
        inputEl?.blur();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        highlightedIndex = Math.min(highlightedIndex + 1, items.length - 1);
        scrollHighlightedIntoView();
        break;
      case 'ArrowUp':
        e.preventDefault();
        highlightedIndex = Math.max(highlightedIndex - 1, -1);
        scrollHighlightedIntoView();
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && highlightedIndex < items.length) {
          selectItem(items[highlightedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        open = false;
        highlightedIndex = -1;
        break;
    }
  }

  function scrollHighlightedIntoView() {
    if (!listEl) return;
    const item = listEl.children[highlightedIndex];
    if (item) item.scrollIntoView({ block: 'nearest' });
  }

  /** Close dropdown on outside click. */
  function handleWindowClick(e) {
    if (open && inputEl && !inputEl.parentElement?.contains(e.target)) {
      open = false;
    }
  }

  /** Reset to initial state (e.g. when searchFn changes). */
  $effect(() => {
    if (initialQuery && !lastSelectedLabel) {
      query = initialQuery;
      doSearch(initialQuery);
    }
  });

  $effect(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('click', handleWindowClick);
      return () => window.removeEventListener('click', handleWindowClick);
    }
  });

  /** Expose a programmatic reset. */
  $effect(() => {
    // If value changes externally back to undefined, clear
    if (value === undefined || value === null) {
      // Only clear if we have a stale displayed label
      if (lastSelectedLabel) {
        query = '';
        lastSelectedLabel = '';
        items = [];
        open = false;
      }
    }
  });
</script>

<div class="searchable-dropdown">
  <div class="input-wrapper">
    <input
      bind:this={inputEl}
      type="text"
      class="dropdown-input"
      class:has-value={query.length > 0}
      {placeholder}
      value={query}
      oninput={handleInput}
      onkeydown={handleKeydown}
      onfocus={() => { if (query.length >= minQueryLength && items.length > 0) open = true; }}
      {disabled}
      role="combobox"
      aria-expanded={open}
      aria-haspopup="listbox"
      aria-autocomplete="list"
      aria-controls="search-results-listbox"
    />

    {#if loading}
      <span class="dropdown-indicator dropdown-spinner" aria-label="Loading…"></span>
    {:else if query.length >= minQueryLength && !open}
      <span class="dropdown-indicator dropdown-search-icon" aria-hidden="true">&#128269;</span>
    {/if}

    {#if lastSelectedLabel}
      <button
        class="dropdown-clear"
        onclick={handleClear}
        aria-label="Clear selection"
        tabindex="-1"
      >&times;</button>
    {/if}
  </div>

  {#if open && items.length > 0}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <ul
      bind:this={listEl}
      id="search-results-listbox"
      class="dropdown-list card"
      role="listbox"
      onkeydown={handleKeydown}
    >
      {#each items as item, i (getValue(item))}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <li
          class="dropdown-item"
          class:highlighted={i === highlightedIndex}
          role="option"
          aria-selected={i === highlightedIndex}
          onclick={() => selectItem(item)}
          onmouseenter={() => (highlightedIndex = i)}
        >
          {getLabel(item)}
        </li>
      {/each}
    </ul>
  {:else if open && !loading && query.length >= minQueryLength}
    <div class="dropdown-empty card" role="status">
      No results found
    </div>
  {/if}

  {#if error}
    <div class="dropdown-error" role="alert">{error}</div>
  {/if}
</div>

<style>
  .searchable-dropdown {
    position: relative;
    width: 100%;
  }

  .input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .dropdown-input {
    width: 100%;
    padding: 10px 36px 10px 12px;
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    background: var(--bg-input);
    color: var(--text-primary);
    font-size: 0.9rem;
    transition: border-color var(--transition-fast);
    box-sizing: border-box;
  }
  .dropdown-input:focus {
    outline: none;
    border-color: var(--accent-sand);
    box-shadow: 0 0 0 2px rgba(212, 167, 106, 0.15);
  }
  .dropdown-input::placeholder {
    color: var(--text-muted);
  }
  .dropdown-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .dropdown-input.has-value {
    padding-right: 56px; /* room for clear button */
  }

  .dropdown-indicator {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .dropdown-search-icon {
    font-size: 0.85rem;
    opacity: 0.5;
  }

  .dropdown-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--border-subtle);
    border-top-color: var(--accent-sand);
    border-radius: 50%;
    animation: spin 600ms linear infinite;
  }

  @keyframes spin {
    to { transform: translateY(-50%) rotate(360deg); }
  }

  .dropdown-clear {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: 50%;
    color: var(--text-secondary);
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
    padding: 0;
    transition: all var(--transition-fast);
  }
  .dropdown-clear:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-color: var(--accent-sand);
  }

  .dropdown-list {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    max-height: 240px;
    overflow-y: auto;
    z-index: 100;
    list-style: none;
    padding: 4px;
    margin: 0;
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    background: var(--bg-card);
    box-shadow: var(--shadow-md);
    animation: fadeIn 120ms ease;
  }

  .dropdown-item {
    padding: 8px 12px;
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    font-size: 0.9rem;
    cursor: pointer;
    transition: background var(--transition-fast);
  }
  .dropdown-item:hover,
  .dropdown-item.highlighted {
    background: var(--bg-hover);
  }
  .dropdown-item[aria-selected="true"] {
    background: var(--bg-hover);
    color: var(--accent-warm);
  }

  .dropdown-empty {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    padding: 12px 16px;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    background: var(--bg-card);
    box-shadow: var(--shadow-sm);
    z-index: 100;
  }

  .dropdown-error {
    margin-top: 4px;
    padding: 6px 10px;
    border-radius: var(--radius-sm);
    background: rgba(212, 83, 74, 0.12);
    color: var(--error);
    font-size: 0.8rem;
    border: 1px solid rgba(212, 83, 74, 0.25);
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
  }
</style>
