<script>
  /**
   * UserProfile — Public profile page at /profile/:username.
   * Shows avatar, display name, burner info, and tabbed posts/friends.
   */
  import { push } from 'svelte-spa-router';
  import { getTokenPayload } from '../lib/auth/token.js';
  import { isLocalFirst, featureMode } from '../lib/config/features.js';
  import { identityStore, store } from '../lib/local/localRuntime.js';
  import {
    searchUsers,
    getUser,
    getMyProfile,
    listUserPosts,
    listFriends,
    listPendingRequests,
    sendFriendRequest,
    acceptFriendRequest,
    rejectFriendRequest,
    unfriend,
  } from '../lib/api/social.js';
  import UserAvatar from '../lib/components/UserAvatar.svelte';
  import FeedCard from '../lib/components/FeedCard.svelte';
  import FriendButton from '../lib/components/FriendButton.svelte';

  let { params } = $props();

  // ── Core profile state ──
  let profileUser = $state(null);       // { user_id, username, display_name, created_at }
  let burnerInfo = $state(null);        // { playa_name, home_camp, years_attended, vibe, bio }
  let loading = $state(true);
  let error = $state('');

  // ── Friend state (for other users) ──
  let friendStatus = $state({ userId: null, isFriend: false, requestStatus: 'none' });
  let friendLoading = $state(false);

  // ── Tab state ──
  let activeTab = $state('posts');
  let posts = $state([]);
  let friendsList = $state([]);
  let postsLoading = $state(true);
  let friendsLoading = $state(false);

  // ── Derived ──
  const currentUser = $derived(getTokenPayload());
  const isOwnProfile = $derived(currentUser?.username === params?.username);
  const profileUserId = $derived(profileUser?.user_id);

  // ── Load profile on mount / route change ──
  $effect(() => {
    const username = params?.username;
    if (!username) return;
    loadProfile(username);
  });

  async function loadProfile(username) {
    loading = true;
    error = '';
    activeTab = 'posts';
    if (isLocalFirst(featureMode)) {
      const identity = await identityStore.initialize();
      const projection = await store.getProjection('root') || { profiles: {}, posts: {} };
      const local = projection.profiles[identity.id] || { id: identity.id, user_id: identity.id, username: identity.id, display_name: identity.id };
      profileUser = local;
      burnerInfo = local;
      posts = Object.values(projection.posts || {}).filter(post => post.author === identity.publicKey);
      postsLoading = false;
      loading = false;
      return;
    }
    posts = [];
    friendsList = [];
    profileUser = null;
    burnerInfo = null;

    try {
      // 1. Search by username to find the user record
      const results = await searchUsers(username);
      const match = Array.isArray(results)
        ? results.find(u => u.username === username)
        : null;

      if (!match) {
        error = 'User not found';
        loading = false;
        return;
      }

      // 2. Get full user details
      const userData = await getUser(match.user_id);
      profileUser = userData;

      // 3. Burner info & friend check
      if (currentUser?.username === username) {
        // Own profile — load full burner info
        try {
          const myProfile = await getMyProfile();
          burnerInfo = myProfile.burner || null;
        } catch (e) {
          console.error('Failed to load burner info:', e);
        }
      } else {
        // Other user — check friend relationship
        friendStatus = {
          userId: match.user_id,
          isFriend: match.is_friend || false,
          requestStatus: match.is_friend ? 'friends' : 'none',
        };
        // Check pending requests for accurate status
        if (!match.is_friend) {
          await refreshFriendStatus(match.user_id);
        }
      }

      // 4. Load posts (default tab)
      await loadUserPosts(match.user_id);
    } catch (e) {
      error = e.message || 'Failed to load profile';
      console.error('Profile load error:', e);
    } finally {
      loading = false;
    }
  }

  // ── Friend status helpers ──

  async function refreshFriendStatus(userId) {
    try {
      // Check outgoing requests first (we sent to them)
      const outgoing = await listPendingRequests('outgoing');
      const sentToUser = Array.isArray(outgoing)
        ? outgoing.some(r => r.to_user_id === userId)
        : false;
      if (sentToUser) {
        friendStatus = { userId, isFriend: false, requestStatus: 'pending_sent' };
        return;
      }

      // Check incoming requests (they sent to us)
      const incoming = await listPendingRequests('incoming');
      const receivedFromUser = Array.isArray(incoming)
        ? incoming.find(r => r.from_user_id === userId)
        : null;
      if (receivedFromUser) {
        friendStatus = {
          userId,
          isFriend: false,
          requestStatus: 'pending_received',
          requestId: receivedFromUser.request_id,
        };
        return;
      }

      friendStatus = { userId, isFriend: false, requestStatus: 'none' };
    } catch (e) {
      console.error('Failed to check friend status:', e);
    }
  }

  async function handleFriendAdd() {
    if (!friendStatus.userId) return;
    friendLoading = true;
    try {
      await sendFriendRequest(friendStatus.userId);
      friendStatus = { ...friendStatus, requestStatus: 'pending_sent' };
    } catch (e) {
      console.error('Friend request failed:', e);
    } finally {
      friendLoading = false;
    }
  }

  async function handleFriendAccept() {
    const requestId = friendStatus.requestId;
    if (!requestId) return;
    friendLoading = true;
    try {
      await acceptFriendRequest(requestId);
      friendStatus = { userId: friendStatus.userId, isFriend: true, requestStatus: 'friends' };
    } catch (e) {
      console.error('Accept friend failed:', e);
    } finally {
      friendLoading = false;
    }
  }

  async function handleFriendReject() {
    const requestId = friendStatus.requestId;
    if (!requestId) return;
    friendLoading = true;
    try {
      await rejectFriendRequest(requestId);
      friendStatus = { userId: friendStatus.userId, isFriend: false, requestStatus: 'none' };
    } catch (e) {
      console.error('Reject friend failed:', e);
    } finally {
      friendLoading = false;
    }
  }

  async function handleFriendRemove() {
    if (!friendStatus.userId) return;
    friendLoading = true;
    try {
      await unfriend(friendStatus.userId);
      friendStatus = { userId: friendStatus.userId, isFriend: false, requestStatus: 'none' };
    } catch (e) {
      console.error('Unfriend failed:', e);
    } finally {
      friendLoading = false;
    }
  }

  // ── Tab content loaders ──

  async function loadUserPosts(userId) {
    postsLoading = true;
    try {
      const data = await listUserPosts(userId);
      posts = Array.isArray(data) ? data : data?.posts || [];
    } catch (e) {
      console.error('Failed to load posts:', e);
      posts = [];
    } finally {
      postsLoading = false;
    }
  }

  async function loadUserFriends(userId) {
    friendsLoading = true;
    try {
      const data = await listFriends(userId);
      friendsList = Array.isArray(data) ? data : data?.friends || [];
    } catch (e) {
      console.error('Failed to load friends:', e);
      friendsList = [];
    } finally {
      friendsLoading = false;
    }
  }

  function switchTab(tab) {
    activeTab = tab;
    if (tab === 'friends' && friendsList.length === 0 && profileUserId) {
      loadUserFriends(profileUserId);
    }
    if (tab === 'posts' && posts.length === 0 && profileUserId) {
      loadUserPosts(profileUserId);
    }
  }

  function handlePostDeleted(postId) {
    posts = posts.filter(p => p.post_id !== postId);
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  }
</script>

<div class="profile-page">
  {#if loading}
    <div class="profile-loading">
      <div class="spinner"></div>
      <p>Loading profile...</p>
    </div>
  {:else if error}
    <div class="profile-error card">
      <div class="error-icon">🏜️</div>
      <h2>{error}</h2>
      <p class="error-sub">This burner may have dusted out or the path was wrong.</p>
      <button class="btn btn-secondary" onclick={() => push('/')}>Return Home</button>
    </div>
  {:else if profileUser}
    <div class="profile-header card">
      <div class="profile-avatar-section">
        <UserAvatar
          username={profileUser.username}
          displayName={profileUser.display_name}
          vibe={burnerInfo?.vibe || null}
          size="lg"
        />
        <div class="profile-meta">
          <h1 class="profile-display-name">
            {profileUser.display_name || profileUser.username}
          </h1>
          <span class="profile-username">@{profileUser.username}</span>
          {#if burnerInfo?.vibe}
            <span class="profile-vibe-badge">
              <span class="vibe-emoji">{burnerInfo.vibe}</span>
              <span>Feeling {burnerInfo.vibe}</span>
            </span>
          {/if}
        </div>
      </div>

      <div class="profile-actions">
        {#if isOwnProfile}
          <a href="#/profile/edit" class="btn btn-secondary">
            ✏️ Edit Profile
          </a>
        {:else}
          <FriendButton
            userId={friendStatus.userId}
            isFriend={friendStatus.isFriend}
            requestStatus={friendStatus.requestStatus}
            onadd={handleFriendAdd}
            onaccept={handleFriendAccept}
            onreject={handleFriendReject}
            onremove={handleFriendRemove}
          />
        {/if}
      </div>
    </div>

    {#if burnerInfo}
      <div class="burner-card card">
        <h2 class="section-title">🔥 Burner Profile</h2>
        <div class="burner-grid">
          {#if burnerInfo.playa_name}
            <div class="burner-field">
              <span class="field-label">Playa Name</span>
              <span class="field-value">{burnerInfo.playa_name}</span>
            </div>
          {/if}
          {#if burnerInfo.home_camp}
            <div class="burner-field">
              <span class="field-label">Home Camp</span>
              <span class="field-value">{burnerInfo.home_camp}</span>
            </div>
          {/if}
          {#if burnerInfo.years_attended}
            <div class="burner-field">
              <span class="field-label">Years on Playa</span>
              <span class="field-value">{burnerInfo.years_attended}</span>
            </div>
          {/if}
          {#if burnerInfo.bio}
            <div class="burner-field burner-bio">
              <span class="field-label">Bio</span>
              <p class="field-value bio-text">{burnerInfo.bio}</p>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <div class="profile-tabs card">
      <div class="tab-bar">
        <button
          class="tab-btn"
          class:active={activeTab === 'posts'}
          onclick={() => switchTab('posts')}
        >
          📝 Posts
        </button>
        <button
          class="tab-btn"
          class:active={activeTab === 'friends'}
          onclick={() => switchTab('friends')}
        >
          👥 Friends
        </button>
      </div>

      <div class="tab-content">
        {#if activeTab === 'posts'}
          {#if postsLoading}
            <div class="tab-placeholder">
              <div class="spinner"></div>
              <p>Loading posts...</p>
            </div>
          {:else if posts.length === 0}
            <div class="tab-empty">
              <span class="empty-icon">📭</span>
              <p>No posts yet</p>
              {#if isOwnProfile}
                <p class="empty-hint">Share your first burn story with the community.</p>
              {/if}
            </div>
          {:else}
            <div class="posts-list">
              {#each posts as post (post.post_id)}
                <FeedCard {post} ondelete={handlePostDeleted} />
              {/each}
            </div>
          {/if}
        {:else if activeTab === 'friends'}
          {#if friendsLoading}
            <div class="tab-placeholder">
              <div class="spinner"></div>
              <p>Loading friends...</p>
            </div>
          {:else if friendsList.length === 0}
            <div class="tab-empty">
              <span class="empty-icon">👥</span>
              <p>No friends yet</p>
              {#if isOwnProfile}
                <p class="empty-hint">Connect with other burners to build your tribe.</p>
              {/if}
            </div>
          {:else}
            <div class="friends-grid">
              {#each friendsList as friend (friend.user_id || friend.friend_id)}
                <a
                  href="#/profile/{friend.username}"
                  class="friend-card"
                >
                  <UserAvatar
                    username={friend.username}
                    displayName={friend.display_name}
                    size="md"
                  />
                  <div class="friend-info">
                    <span class="friend-name">
                      {friend.display_name || friend.username}
                    </span>
                    <span class="friend-username">@{friend.username}</span>
                  </div>
                </a>
              {/each}
            </div>
          {/if}
        {/if}
      </div>
    </div>

    <div class="profile-footer">
      <span class="member-since">
        🔥 Member since {formatDate(profileUser.created_at)}
      </span>
    </div>
  {/if}
</div>

<style>
  /* ── Layout ── */
  .profile-page {
    max-width: 720px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  /* ── Loading ── */
  .profile-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 24px;
    gap: 16px;
    color: var(--text-muted);
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border-subtle);
    border-top-color: var(--accent-sand);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ── Error state ── */
  .profile-error {
    text-align: center;
    padding: 60px 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .error-icon {
    font-size: 3rem;
  }

  .profile-error h2 {
    color: var(--accent-warm);
    font-size: 1.3rem;
  }

  .error-sub {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin-bottom: 8px;
  }

  /* ── Profile header ── */
  .profile-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 20px;
    flex-wrap: wrap;
  }

  .profile-avatar-section {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-shrink: 0;
  }

  .profile-meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .profile-display-name {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent-warm);
    line-height: 1.2;
  }

  .profile-username {
    font-size: 0.95rem;
    color: var(--text-muted);
  }

  .profile-vibe-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    padding: 4px 12px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    font-size: 0.85rem;
    color: var(--accent-sand);
  }

  .vibe-emoji {
    font-size: 1.1rem;
  }

  .profile-actions {
    flex-shrink: 0;
  }

  /* ── Burner info card ── */
  .burner-card {
    padding: 24px;
  }

  .section-title {
    font-size: 1.1rem;
    color: var(--accent-amber);
    margin-bottom: 18px;
  }

  .burner-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .burner-field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .burner-bio {
    grid-column: 1 / -1;
  }

  .field-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .field-value {
    font-size: 0.95rem;
    color: var(--text-primary);
  }

  .bio-text {
    line-height: 1.6;
    white-space: pre-wrap;
  }

  /* ── Tabs ── */
  .profile-tabs {
    padding: 0;
    overflow: hidden;
  }

  .tab-bar {
    display: flex;
    border-bottom: 1px solid var(--border-subtle);
    background: var(--bg-card);
  }

  .tab-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 14px 20px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-secondary);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .tab-btn:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  .tab-btn.active {
    color: var(--accent-sand);
    border-bottom-color: var(--accent-sand);
  }

  .tab-content {
    padding: 20px;
    min-height: 200px;
  }

  .tab-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px 24px;
    gap: 12px;
    color: var(--text-muted);
  }

  .tab-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 48px 24px;
    gap: 8px;
  }

  .empty-icon {
    font-size: 2.5rem;
    margin-bottom: 4px;
  }

  .tab-empty p {
    color: var(--text-secondary);
    font-size: 0.95rem;
  }

  .empty-hint {
    color: var(--text-muted);
    font-size: 0.85rem;
    max-width: 280px;
  }

  /* ── Posts list ── */
  .posts-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* ── Friends grid ── */
  .friends-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }

  .friend-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    transition: all var(--transition-fast);
    color: var(--text-primary);
    text-decoration: none;
  }

  .friend-card:hover {
    background: var(--bg-hover);
    border-color: var(--accent-sand);
    transform: translateY(-1px);
  }

  .friend-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .friend-name {
    font-weight: 600;
    font-size: 0.9rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .friend-username {
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  /* ── Footer ── */
  .profile-footer {
    text-align: center;
    padding: 8px 0 24px;
  }

  .member-since {
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  /* ── Responsive ── */
  @media (max-width: 600px) {
    .profile-header {
      flex-direction: column;
      align-items: stretch;
    }

    .profile-avatar-section {
      flex-direction: column;
      text-align: center;
    }

    .profile-meta {
      align-items: center;
    }

    .profile-actions {
      display: flex;
      justify-content: center;
    }

    .burner-grid {
      grid-template-columns: 1fr;
    }

    .friends-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
