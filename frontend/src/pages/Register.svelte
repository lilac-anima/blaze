<script>
  /**
   * Register Page — username, burner-name, password form.
   */
  import { push } from 'svelte-spa-router';
  import { register } from '../lib/auth/authService.js';
  import { isAuthenticated } from '../lib/auth/token.js';

  let username = $state('');
  let burnerName = $state('');
  let password = $state('');
  let confirmPassword = $state('');
  let error = $state('');
  let success = $state(false);
  let loading = $state(false);

  $effect(() => {
    if (isAuthenticated()) {
      push('/');
    }
  });

  async function handleSubmit(e) {
    e.preventDefault();
    error = '';

    if (password !== confirmPassword) {
      error = 'Passwords do not match.';
      return;
    }
    if (password.length < 8) {
      error = 'Password must be at least 8 characters.';
      return;
    }

    loading = true;

    try {
      await register(username, burnerName, password);
      success = true;
      // Auto-redirect to login after 2 seconds
      setTimeout(() => push('/login'), 2000);
    } catch (err) {
      error = err.message || 'Registration failed. Please try again.';
    } finally {
      loading = false;
    }
  }
</script>

<div class="auth-page">
  <div class="auth-card">
    <div class="auth-header">
      <div class="auth-icon">🏕️</div>
      <h1>Join the Burn</h1>
      <p class="subtitle">Create your burner identity</p>
    </div>

    {#if success}
      <div class="alert alert-success">
        <span>✅</span> Account created! Redirecting to login...
      </div>
    {:else}
      <form class="auth-form" onsubmit={handleSubmit}>
        {#if error}
          <div class="alert alert-error">
            <span>⚠️</span> {error}
          </div>
        {/if}

        <div class="form-group">
          <label class="form-label" for="username">Username</label>
          <input
            id="username"
            type="text"
            placeholder="sparklepony"
            bind:value={username}
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="burner-name">Burner Name</label>
          <input
            id="burner-name"
            type="text"
            placeholder="Captain Sparkles"
            bind:value={burnerName}
            required
          />
          <span class="form-hint">Your playa name — make it legendary</span>
        </div>

        <div class="form-group">
          <label class="form-label" for="password">Password</label>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            bind:value={password}
            required
            minlength="8"
            autocomplete="new-password"
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="confirm-password">Confirm Password</label>
          <input
            id="confirm-password"
            type="password"
            placeholder="••••••••"
            bind:value={confirmPassword}
            required
            autocomplete="new-password"
          />
        </div>

        <button type="submit" class="btn btn-primary btn-full" disabled={loading}>
          {loading ? '🏕️ Setting up camp...' : '🏕️ Create Account'}
        </button>
      </form>

      <div class="auth-footer">
        Already have a burner name? <a href="#/login">Sign in</a>
      </div>
    {/if}
  </div>
</div>

<style>
  .auth-header {
    text-align: center;
    margin-bottom: 8px;
  }

  .auth-icon {
    font-size: 2.5rem;
    margin-bottom: 8px;
  }

  .form-hint {
    font-size: 0.8rem;
    color: var(--text-muted);
    font-style: italic;
  }

  .btn-full {
    width: 100%;
    padding: 12px 24px;
    font-size: 1rem;
  }

  .alert {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
  }

  .alert-error {
    background: rgba(212, 83, 74, 0.12);
    border: 1px solid rgba(212, 83, 74, 0.3);
    color: #f08a82;
  }

  .alert-success {
    background: rgba(76, 175, 125, 0.12);
    border: 1px solid rgba(76, 175, 125, 0.3);
    color: #7ddaae;
  }
</style>
