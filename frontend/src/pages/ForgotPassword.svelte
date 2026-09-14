<script>
  /**
   * Forgot Password Page — email form to request password reset.
   */
  import { push } from 'svelte-spa-router';
  import { forgotPassword } from '../lib/auth/authService.js';

  let email = $state('');
  let error = $state('');
  let sent = $state(false);
  let loading = $state(false);

  async function handleSubmit(e) {
    e.preventDefault();
    error = '';
    loading = true;

    try {
      await forgotPassword(email);
      sent = true;
    } catch (err) {
      error = err.message || 'Request failed. Please try again.';
    } finally {
      loading = false;
    }
  }
</script>

<div class="auth-page">
  <div class="auth-card">
    <div class="auth-header">
      <div class="auth-icon">🌵</div>
      <h1>Forgot Password</h1>
      <p class="subtitle">Don't worry, we'll get you back on the playa</p>
    </div>

    {#if sent}
      <div class="alert alert-success">
        <span>📬</span>
        <div>
          <strong>Check your inbox!</strong>
          <p class="alert-text">If an account exists for {email}, we've sent reset instructions.</p>
        </div>
      </div>
      <div class="auth-footer" style="margin-top: 20px;">
        Remembered your password? <a href="#/login">Sign in</a>
      </div>
    {:else}
      <form class="auth-form" onsubmit={handleSubmit}>
        {#if error}
          <div class="alert alert-error">
            <span>⚠️</span> {error}
          </div>
        {/if}

        <p class="form-description">
          Enter the email address associated with your account and we'll send you
          a link to reset your password.
        </p>

        <div class="form-group">
          <label class="form-label" for="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="you@burningman.org"
            bind:value={email}
            required
            autocomplete="email"
          />
        </div>

        <button type="submit" class="btn btn-primary btn-full" disabled={loading}>
          {loading ? '🌵 Sending...' : '🌵 Send Reset Link'}
        </button>
      </form>

      <div class="auth-footer">
        Remembered your password? <a href="#/login">Sign in</a>
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

  .form-description {
    font-size: 0.9rem;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .btn-full {
    width: 100%;
    padding: 12px 24px;
    font-size: 1rem;
  }

  .alert {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 14px;
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
  }

  .alert strong {
    display: block;
    margin-bottom: 4px;
  }

  .alert-text {
    font-size: 0.85rem;
    opacity: 0.9;
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
