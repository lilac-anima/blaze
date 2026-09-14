<script>
  import { push } from 'svelte-spa-router';
  import { updateMyProfile } from '../lib/api/social.js';
  import { isLocalFirst, featureMode } from '../lib/config/features.js';
  import { updateLocalProfile } from '../lib/local/localRuntime.js';

  let displayName = $state('');
  let bio = $state('');
  let saving = $state(false);
  let status = $state('');
  async function save() {
    saving = true;
    status = '';
    try {
      if (isLocalFirst(featureMode)) {
        const result = await updateLocalProfile({ display_name: displayName.trim(), bio: bio.trim() });
        status = result.status === 'local' ? 'Saved locally · pending sync' : 'Profile rejected';
      } else {
        await updateMyProfile({ display_name: displayName.trim() }, { bio: bio.trim() });
        status = 'Profile saved';
      }
    } catch (error) { status = error.message || 'Unable to save profile'; }
    finally { saving = false; }
  }
</script>

<div class="profile-editor card">
  <h1>Edit Profile</h1>
  <label>Display name<input bind:value={displayName} maxlength="80" /></label>
  <label>Bio<textarea bind:value={bio} maxlength="500"></textarea></label>
  {#if status}<p class="status">{status}</p>{/if}
  <div class="actions"><button class="btn btn-secondary" onclick={() => push('/profile/test')}>Cancel</button><button class="btn btn-primary" onclick={save} disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button></div>
</div>

<style>
  .profile-editor { max-width: 560px; margin: 32px auto; padding: 24px; display: grid; gap: 16px; }
  h1 { color: var(--accent-warm); font-size: 1.5rem; }
  label { display: grid; gap: 6px; color: var(--text-secondary); }
  input, textarea { padding: 10px; background: var(--bg-input); border: 1px solid var(--border-primary); color: var(--text-primary); border-radius: var(--radius-md); }
  textarea { min-height: 120px; resize: vertical; }
  .status { color: var(--text-secondary); }
  .actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
