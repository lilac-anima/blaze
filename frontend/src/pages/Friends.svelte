<script>
  /**
   * Friends Page — friends management with three tabs:
   * 'My Friends', 'Requests' (Incoming/Outgoing), 'Find People'.
   * Route: /friends (protected)
   */
  import {
    listFriends, listPendingRequests, acceptFriendRequest,
    rejectFriendRequest, searchUsers, getUserSuggestions, unfriend
  } from '../lib/api/social.js';
  import { getTokenPayload } from '../lib/auth/token.js';
  import UserAvatar from '../lib/components/UserAvatar.svelte';
  import FriendButton from '../lib/components/FriendButton.svelte';

  // ── Current user ──
  let currentUser = $state(getTokenPayload());
  let userId = $derived(currentUser?.sub);

  // ── Tab state ──
  let activeTab = $state('friends');
  let requestSubTab = $state('incoming'); // 'incoming' | 'outgoing'

  // ── My Friends ──
  let friends = $state([]);
  let friendsLoading = $state(false);
  let friendsError = $state('');

  // ── Requests ──
  let requests = $state([]);
  let requestsLoading = $state(false);
  let requestsError = $state('');

  // ── Find People ──
  let searchQuery = $state('');
  let searchResults = $state([]);
  let searchLoading = $state(false);
  let suggestions = $state([]);
  let suggestionsLoading = $state(false);
  let suggestionsError = $state('');

  // ── Load friends ──
  async function loadFriends() {
    friendsLoading = true;
    friendsError = '';
    try {
      const data = await listFriends(userId);
      friends = Array.isArray(data) ? data : (data.friends || []);
    } catch (e) {
      friendsError = e.message;
      friends = [];
    } finally {
      friendsLoading = false;
    }
  }

  // ── Load requests ──
  async function loadRequests() {
    requestsLoading = true;
    requestsError = '';
    try {
      const data = await listPendingRequests(requestSubTab);
      requests = Array.isArray(data) ? data : (data.requests || []);
    } catch (e) {
      requestsError = e.message;
      requests = [];
    } finally {
      requestsLoading = false;
    }
  }

  // ── Accept / Reject friend request ──
  let processingRequestId = $state(null);

  async function handleAccept(requestId) {
    processingRequestId = requestId;
    requestsError = '';
    try {
      await acceptFriendRequest(requestId);
      await loadRequests();
    } catch (e) {
      requestsError = e.message;
    } finally {
      processingRequestId = null;
    }
  }

  async function handleReject(requestId) {
    processingRequestId = requestId;
    requestsError = '';
    try {
      await rejectFriendRequest(requestId);
      await loadRequests();
    } catch (e) {
      requestsError = e.message;
    } finally {
      processingRequestId = null;
    }
  }

  // ── Unfriend ──
  let unfriendingId = $state(null);

  async function handleUnfriend(friendId) {
    unfriendingId = friendId;
    friendsError = '';
    try {
      await unfriend(friendId);
      await loadFriends();
    } catch (e) {
      friendsError = e.message;
    } finally {
      unfriendingId = null;
    }
  }

  // ── Search users ──
  let searchTimeout;

  async function handleSearch() {
    const q = searchQuery.trim();
    if (!q) {
      searchResults = [];
      return;
    }
    searchLoading = true;
    try {
      const data = await searchUsers(q);
      searchResults = Array.isArray(data) ? data : (data.users || []);
    } catch (e) {
      searchResults = [];
    } finally {
      searchLoading = false;
    }
  }

  function onSearchInput() {
    clearTimeout(searchTimeout);
    if (!searchQuery.trim()) {
      searchResults = [];
      return;
    }
    searchTimeout = setTimeout(handleSearch, 350);
  }

  function clearSearch() {
    searchQuery = '';
    searchResults = [];
  }

  // ── Suggestions ──
  async function loadSuggestions() {
    suggestionsLoading = true;
    suggestionsError = '';
    try {
      const data = await getUserSuggestions(userId, 10);
      suggestions = Array.isArray(data) ? data : (data.suggestions || []);
    } catch (e) {
      suggestionsError = e.message;
      suggestions = [];
    } finally {
      suggestionsLoading = false;
    }
  }

  // ── Tab switching ──
  function switchTab(tab) {
    activeTab = tab;
    if (tab === 'friends') loadFriends();
    else if (tab === 'requests') loadRequests();
    else if (tab === 'find') loadSuggestions();
  }

  function switchRequestSubTab(subtab) {
    requestSubTab = subtab;
    loadRequests();
  }

  // ── Callback after FriendButton actions (search results) ──
  function onFriendActionDone() {
    if (searchQuery.trim()) handleSearch();
  }

  // ── Initial load ──
  $effect(() => {
    if (userId) loadFriends();
  });

  // ── Helpers ──
  function friendDisplayName(f) {
    return f.display_name || f.displayName || f.username || f.name || 'Unknown';
  }

  function friendUsername(f) {
    return f.username || f.name || '';
  }

  function requestDisplayName(r) {
    const user = r.from_user || r.sender || r.user || r;
    return user.display_name || user.displayName || user.username || user.name || 'Unknown';
  }

  function requestUsername(r) {
    const user = r.from_user || r.sender || r.user || r;
    return user.username || user.name || '';
  }

  function friendId(f) {
    return f.id || f.friend_id || f.user_id;
  }

  function searchUserStatus(u) {
    if (u.is_friend) return 'friends';
    if (u.friend_request_status) return u.friend_request_status;
    if (u.request_status) return u.request_status;
    return 'none';
  }
</script>

<div class="friends-page">
  <header class="friends-header">
    <h1>Friends</h1>
    <p class="friends-subtitle">Connect with burners on the playa</p>
  </header>

  <!-- ── Tab bar ── -->
  <nav class="tab-bar">
    <button
      class="tab-btn"
      class:tab-active={activeTab === 'friends'}
      onclick={() => switchTab('friends')}
    >
      <span class="tab-icon">👥</span>
      <span>My Friends</span>
    </button>
    <button
      class="tab-btn"
      class:tab-active={activeTab === 'requests'}
      onclick={() => switchTab('requests')}
    >
      <span class="tab-icon">📩</span>
      <span>Requests</span>
    </button>
    <button
      class="tab-btn"
      class:tab-active={activeTab === 'find'}
      onclick={() => switchTab('find')}
    >
      <span class="tab-icon">🔍</span>
      <span>Find People</span>
    </button>
  </nav>

  <!-- ════════════════════════════════════════════ -->
  <!-- TAB: MY FRIENDS                             -->
  <!-- ════════════════════════════════════════════ -->
  {#if activeTab === 'friends'}
    <div class="tab-content">
      {#if friendsLoading}
        <div class="state-message">
          <span class="spinner"></span>
          <p>Loading friends...</p>
        </div>
      {:else if friendsError}
        <div class="state-message error">
          <p>⚠️ {friendsError}</p>
          <button class="btn btn-secondary" onclick={loadFriends}>Retry</button>
        </div>
      {:else if friends.length === 0}
        <div class="state-message empty">
          <span class="empty-icon">🏜️</span>
          <h3>No friends yet</h3>
          <p>Head over to <button class="link-btn" onclick={() => switchTab('find')}>Find People</button> to connect with other burners.</p>
        </div>
      {:else}
        <div class="friends-list">
          {#each friends as f (friendId(f))}
            <div class="friend-card">
              <div class="friend-info">
                <UserAvatar username={friendUsername(f)} displayName={friendDisplayName(f)} size="md" />
                <div class="friend-details">
                  <span class="friend-name">{friendDisplayName(f)}</span>
                  {#if friendUsername(f)}
                    <span class="friend-username">@{friendUsername(f)}</span>
                  {/if}
                </div>
              </div>
              <button
                class="btn-unfriend"
                disabled={unfriendingId === friendId(f)}
                onclick={() => handleUnfriend(friendId(f))}
              >
                {unfriendingId === friendId(f) ? '...' : 'Unfriend'}
              </button>
            </div>
          {/each}
        </div>
      {/if}
    </div>

  <!-- ════════════════════════════════════════════ -->
  <!-- TAB: REQUESTS                               -->
  <!-- ════════════════════════════════════════════ -->
  {:else if activeTab === 'requests'}
    <div class="tab-content">
      <!-- Sub-tab pills -->
      <div class="subtab-pills">
        <button
          class="pill-btn"
          class:pill-active={requestSubTab === 'incoming'}
          onclick={() => switchRequestSubTab('incoming')}
        >
          Incoming
        </button>
        <button
          class="pill-btn"
          class:pill-active={requestSubTab === 'outgoing'}
          onclick={() => switchRequestSubTab('outgoing')}
        >
          Outgoing
        </button>
      </div>

      {#if requestsLoading}
        <div class="state-message">
          <span class="spinner"></span>
          <p>Loading requests...</p>
        </div>
      {:else if requestsError}
        <div class="state-message error">
          <p>⚠️ {requestsError}</p>
          <button class="btn btn-secondary" onclick={loadRequests}>Retry</button>
        </div>
      {:else if requests.length === 0}
        <div class="state-message empty">
          <span class="empty-icon">📭</span>
          <h3>{requestSubTab === 'incoming' ? 'No incoming requests' : 'No outgoing requests'}</h3>
          <p>
            {#if requestSubTab === 'incoming'}
              When someone sends you a friend request, it'll appear here.
            {:else}
              Friend requests you've sent will show up here.
            {/if}
          </p>
        </div>
      {:else}
        <div class="requests-list">
          {#each requests as r (r.id || r.request_id)}
            <div class="request-card">
              <div class="request-info">
                <UserAvatar username={requestUsername(r)} displayName={requestDisplayName(r)} size="md" />
                <div class="request-details">
                  <span class="request-name">{requestDisplayName(r)}</span>
                  {#if requestUsername(r)}
                    <span class="request-username">@{requestUsername(r)}</span>
                  {/if}
                  {#if r.created_at}
                    <span class="request-date">{new Date(r.created_at).toLocaleDateString()}</span>
                  {/if}
                </div>
              </div>

              {#if requestSubTab === 'incoming'}
                <div class="request-actions">
                  <button
                    class="btn-accept"
                    disabled={processingRequestId === (r.id || r.request_id)}
                    onclick={() => handleAccept(r.id || r.request_id)}
                  >
                    {processingRequestId === (r.id || r.request_id) ? '...' : '✓ Accept'}
                  </button>
                  <button
                    class="btn-decline"
                    disabled={processingRequestId === (r.id || r.request_id)}
                    onclick={() => handleReject(r.id || r.request_id)}
                  >
                    ✕ Decline
                  </button>
                </div>
              {:else}
                <span class="outgoing-badge">⏳ Pending</span>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

  <!-- ════════════════════════════════════════════ -->
  <!-- TAB: FIND PEOPLE                            -->
  <!-- ════════════════════════════════════════════ -->
  {:else if activeTab === 'find'}
    <div class="tab-content">
      <!-- Search -->
      <div class="search-section">
        <div class="search-bar">
          <span class="search-icon">🔍</span>
          <input
            type="text"
            class="search-input"
            placeholder="Search by name or username..."
            bind:value={searchQuery}
            oninput={onSearchInput}
          />
          {#if searchQuery}
            <button class="search-clear" onclick={clearSearch} aria-label="Clear search">✕</button>
          {/if}
        </div>

        {#if searchLoading}
          <div class="state-message compact">
            <span class="spinner"></span>
            <p>Searching...</p>
          </div>
        {:else if searchQuery.trim() && searchResults.length > 0}
          <div class="search-results">
            <h3 class="section-title">Results</h3>
            <div class="results-list">
              {#each searchResults as u (u.id || u.user_id)}
                <div class="result-card">
                  <div class="result-info">
                    <UserAvatar
                      username={u.username || u.name}
                      displayName={u.display_name || u.displayName}
                      size="md"
                    />
                    <div class="result-details">
                      <span class="result-name">{u.display_name || u.displayName || u.username || u.name || 'Unknown'}</span>
                      {#if u.username || u.name}
                        <span class="result-username">@{u.username || u.name}</span>
                      {/if}
                    </div>
                  </div>
                  <FriendButton
                    userId={u.id || u.user_id}
                    isFriend={!!u.is_friend}
                    requestStatus={searchUserStatus(u)}
                    onadd={onFriendActionDone}
                    onaccept={onFriendActionDone}
                    onreject={onFriendActionDone}
                    onremove={onFriendActionDone}
                  />
                </div>
              {/each}
            </div>
          </div>
        {:else if searchQuery.trim() && !searchLoading}
          <div class="state-message compact">
            <p class="no-results">No users found matching "{searchQuery.trim()}"</p>
          </div>
        {/if}
      </div>

      <!-- Suggestions -->
      <div class="suggestions-section">
        <h3 class="section-title">Suggestions</h3>
        {#if suggestionsLoading}
          <div class="state-message compact">
            <span class="spinner"></span>
            <p>Loading suggestions...</p>
          </div>
        {:else if suggestionsError}
          <div class="state-message error compact">
            <p>⚠️ {suggestionsError}</p>
          </div>
        {:else if suggestions.length === 0}
          <div class="state-message empty compact">
            <p>No suggestions right now. Try searching for someone!</p>
          </div>
        {:else}
          <div class="suggestions-grid">
            {#each suggestions as s (s.id || s.user_id)}
              <div class="suggestion-card">
                <div class="suggestion-header">
                  <UserAvatar
                    username={s.username || s.name}
                    displayName={s.display_name || s.displayName}
                    size="md"
                  />
                  <div class="suggestion-details">
                    <span class="suggestion-name">{s.display_name || s.displayName || s.username || s.name || 'Unknown'}</span>
                    <span class="suggestion-username">@{s.username || s.name}</span>
                  </div>
                </div>
                <div class="suggestion-action">
                  <FriendButton
                    userId={s.id || s.user_id}
                    isFriend={!!s.is_friend}
                    requestStatus={searchUserStatus(s)}
                    onadd={onFriendActionDone}
                    onaccept={onFriendActionDone}
                    onreject={onFriendActionDone}
                    onremove={onFriendActionDone}
                  />
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  /* ── Page layout ── */
  .friends-page {
    max-width: 780px;
    margin: 0 auto;
  }

  .friends-header {
    margin-bottom: 24px;
  }

  .friends-header h1 {
    font-size: 1.5rem;
    color: var(--accent-warm);
  }

  .friends-subtitle {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-top: 4px;
  }

  /* ── Tab bar ── */
  .tab-bar {
    display: flex;
    gap: 4px;
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    padding: 4px;
    margin-bottom: 24px;
    border: 1px solid var(--border-subtle);
  }

  .tab-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px 16px;
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 0.9rem;
    border: none;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .tab-btn:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  .tab-active {
    background: var(--bg-card);
    color: var(--accent-amber);
    box-shadow: var(--shadow-sm);
  }

  .tab-icon {
    font-size: 1rem;
  }

  /* ── Tab content ── */
  .tab-content {
    animation: fadeIn 200ms ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* ── State messages ── */
  .state-message {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 48px 24px;
    text-align: center;
    color: var(--text-secondary);
  }

  .state-message.compact {
    padding: 24px;
  }

  .state-message h3 {
    font-size: 1.1rem;
    color: var(--text-primary);
  }

  .state-message p {
    font-size: 0.9rem;
    color: var(--text-muted);
    max-width: 360px;
  }

  .state-message.error p {
    color: var(--error);
  }

  .empty-icon {
    font-size: 2.5rem;
  }

  .no-results {
    color: var(--text-muted);
  }

  /* ── Spinner ── */
  .spinner {
    width: 24px;
    height: 24px;
    border: 3px solid var(--border-subtle);
    border-top-color: var(--accent-sand);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ── Link button ── */
  .link-btn {
    background: none;
    border: none;
    color: var(--text-link);
    font-weight: 600;
    cursor: pointer;
    padding: 0;
    font-size: inherit;
    display: inline;
  }
  .link-btn:hover {
    color: var(--accent-warm);
    text-decoration: underline;
  }

  /* ── Friends list ── */
  .friends-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .friend-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    transition: all var(--transition-fast);
    gap: 12px;
  }

  .friend-card:hover {
    background: var(--bg-hover);
    border-color: var(--border-primary);
  }

  .friend-info {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
  }

  .friend-details {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .friend-name {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .friend-username {
    font-size: 0.8rem;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .btn-unfriend {
    flex-shrink: 0;
    padding: 6px 14px;
    border-radius: var(--radius-xl);
    font-size: 0.8rem;
    font-weight: 600;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }

  .btn-unfriend:hover:not(:disabled) {
    border-color: var(--error);
    color: var(--error);
    background: rgba(212, 83, 74, 0.1);
  }

  .btn-unfriend:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* ── Sub-tab pills ── */
  .subtab-pills {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
  }

  .pill-btn {
    padding: 7px 20px;
    border-radius: var(--radius-xl);
    font-size: 0.85rem;
    font-weight: 600;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .pill-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  .pill-active {
    background: var(--bg-card);
    color: var(--accent-amber);
    border-color: var(--accent-sand);
    box-shadow: var(--shadow-sm);
  }

  /* ── Requests list ── */
  .requests-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .request-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    transition: all var(--transition-fast);
    gap: 12px;
    flex-wrap: wrap;
  }

  .request-card:hover {
    background: var(--bg-hover);
    border-color: var(--border-primary);
  }

  .request-info {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
    flex: 1;
  }

  .request-details {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .request-name {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .request-username {
    font-size: 0.8rem;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .request-date {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 2px;
  }

  .request-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }

  .btn-accept {
    padding: 6px 16px;
    border-radius: var(--radius-xl);
    font-size: 0.8rem;
    font-weight: 600;
    background: var(--success);
    color: white;
    border: none;
    cursor: pointer;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }

  .btn-accept:hover:not(:disabled) {
    filter: brightness(1.1);
    box-shadow: var(--shadow-sm);
  }

  .btn-accept:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-decline {
    padding: 6px 16px;
    border-radius: var(--radius-xl);
    font-size: 0.8rem;
    font-weight: 600;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }

  .btn-decline:hover:not(:disabled) {
    border-color: var(--error);
    color: var(--error);
    background: rgba(212, 83, 74, 0.1);
  }

  .btn-decline:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .outgoing-badge {
    font-size: 0.8rem;
    color: var(--text-muted);
    background: var(--bg-tertiary);
    padding: 6px 14px;
    border-radius: var(--radius-xl);
    border: 1px solid var(--border-subtle);
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* ── Search section ── */
  .search-section {
    margin-bottom: 32px;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--bg-input);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-lg);
    padding: 0 16px;
    transition: border-color var(--transition-fast);
  }

  .search-bar:focus-within {
    border-color: var(--accent-sand);
    box-shadow: 0 0 0 2px rgba(212, 167, 106, 0.15);
  }

  .search-icon {
    font-size: 1rem;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    color: var(--text-primary);
    padding: 12px 0;
    font-size: 0.95rem;
    min-width: 0;
  }

  .search-input::placeholder {
    color: var(--text-muted);
  }

  .search-clear {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 0.9rem;
    cursor: pointer;
    padding: 4px;
    border-radius: 50%;
    transition: all var(--transition-fast);
    flex-shrink: 0;
  }

  .search-clear:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }

  /* ── Search results ── */
  .section-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
    margin-top: 0;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .result-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    transition: all var(--transition-fast);
    gap: 12px;
  }

  .result-card:hover {
    background: var(--bg-hover);
    border-color: var(--border-primary);
  }

  .result-info {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
    flex: 1;
  }

  .result-details {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .result-name {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-username {
    font-size: 0.78rem;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* ── Suggestions grid ── */
  .suggestions-section {
    padding-top: 8px;
  }

  .suggestions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 10px;
  }

  .suggestion-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    transition: all var(--transition-fast);
  }

  .suggestion-card:hover {
    background: var(--bg-hover);
    border-color: var(--border-primary);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
  }

  .suggestion-header {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .suggestion-details {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .suggestion-name {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .suggestion-username {
    font-size: 0.78rem;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .suggestion-action {
    align-self: flex-end;
  }

  /* ── Responsive ── */
  @media (max-width: 640px) {
    .tab-bar {
      flex-direction: column;
      gap: 2px;
    }

    .request-card {
      flex-direction: column;
      align-items: stretch;
    }

    .request-actions {
      width: 100%;
      justify-content: flex-end;
    }

    .suggestions-grid {
      grid-template-columns: 1fr;
    }

    .friend-card {
      flex-wrap: wrap;
    }
  }
</style>
