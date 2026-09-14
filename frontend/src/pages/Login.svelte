<script>
  /**
   * Login Page — username + password form.
   */
  import { push } from 'svelte-spa-router';
  import { login } from '../lib/auth/authService.js';
  import { isAuthenticated } from '../lib/auth/token.js';

  let username = $state('');
  let password = $state('');
  let error = $state('');
  let loading = $state(false);

  // Redirect if already logged in
  $effect(() => {
    if (isAuthenticated()) {
      push('/');
    }
  });

  async function handleSubmit(e) {
    e.preventDefault();
    error = '';
    loading = true;

    try {
      await login(username, password);
      push('/');
    } catch (err) {
      error = err.message || 'Login failed. Please try again.';
    } finally {
      loading = false;
    }
  }
</script>

<div class="auth-page">
  <div class="auth-card">
    <div class="auth-header">
      <div class="auth-icon">🔥</div>
      <h1>Welcome Back</h1>
      <p class="subtitle">Find your tribe on the playa</p>
    </div>

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
        <label class="form-label" for="password">Password</label>
        <input
          id="password"
          type="password"
          placeholder="••••••••"
          bind:value={password}
          required
          autocomplete="current-password"
        />
      </div>

      <div class="form-actions">
        <a href="#/forgot-password" class="forgot-link">Forgot password?</a>
      </div>

      <button type="submit" class="btn btn-primary btn-full" disabled={loading}>
        {loading ? '🔥 Igniting...' : '🔥 Sign In'}
      </button>
    </form>

    <div class="auth-footer">
      New to the playa? <a href="#/register">Create an account</a>
    </div>
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

  .form-actions {
    display: flex;
    justify-content: flex-end;
  }

  .forgot-link {
    font-size: 0.85rem;
    color: var(--text-muted);
    transition: color var(--transition-fast);
  }
  .forgot-link:hover {
    color: var(--accent-sand);
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
</style>
