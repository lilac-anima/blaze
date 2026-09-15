<script>
  import { featureMode, isLocalFirst } from '../config/features.js';
  import { identityStore, store } from '../local/localRuntime.js';
  import { createPeerSession } from '../sync/peerSession.js';
  import { createSignalingTransport } from '../sync/signalingClient.js';
  import { createSyncEngine } from '../sync/syncEngine.js';
  import { createResumeController } from '../sync/resume.js';

  let roomId = $state('blaze-demo');
  let remotePeerId = $state('');
  let localPeerId = $state('');
  let status = $state('offline');
  let error = $state('');
  let session = $state(null);
  let resume = $state(null);

  async function connect() {
    error = '';
    status = 'connecting';
    try {
      const identity = await identityStore.initialize();
      localPeerId = identity.id;
      if (!remotePeerId) throw new Error('Enter the other peer ID first');
      const baseUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`;
      const transport = createSignalingTransport({ url: baseUrl, roomId, peerId: localPeerId });
      const peerSession = createPeerSession({ peerId: localPeerId, remotePeerId, transport });
      const sync = createSyncEngine({ store, session: peerSession, peerId: remotePeerId, onStatus: value => status = value });
      peerSession.onStateChange(value => {
        status = value;
        if (value === 'connected') sync.start();
        if (value === 'disconnected' && resume) resume.resume().catch(cause => { error = cause.message; });
      });
      resume = createResumeController({
        connect: async () => {
          await transport.connect();
          await peerSession.restart({ initiator: true });
        },
        resync: () => sync.resync(),
        onStatus: value => status = value,
      });
      await transport.connect();
      await peerSession.start({ initiator: true });
      session = peerSession;
      status = 'waiting-for-peer';
    } catch (cause) {
      error = cause.message;
      status = 'failed';
    }
  }

  async function retry() {
    if (resume) await resume.resume().catch(cause => { error = cause.message; });
  }

  function disconnect() {
    resume?.stop();
    session?.close();
    session = null;
    status = 'offline';
  }
</script>

{#if isLocalFirst(featureMode)}
  <section class="sync-panel" aria-label="Peer synchronization">
    <div class="sync-heading">
      <div>
        <h2>Peer sync</h2>
        <p>Phase 2 local-first preview</p>
      </div>
      <span class:online={status === 'connected'} class="status">{status}</span>
    </div>
    <label>Room ID <input bind:value={roomId} /></label>
    <label>Remote peer ID <input bind:value={remotePeerId} placeholder="did:key:..." /></label>
    {#if localPeerId}<small>Your peer ID: {localPeerId}</small>{/if}
    {#if error}<p class="error">{error}</p>{/if}
    <div class="actions">
      {#if session}
        <button class="btn btn-secondary" onclick={retry}>Retry sync</button>
        <button class="btn btn-secondary" onclick={disconnect}>Disconnect</button>
      {:else}
        <button class="btn btn-primary" onclick={connect}>Connect peer</button>
      {/if}
    </div>
  </section>
{/if}

<style>
  .sync-panel { max-width: 420px; padding: 16px; margin-bottom: 20px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); }
  .sync-heading { display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px; }
  h2 { font-size: 1rem; color: var(--text-primary); }
  p, small { color: var(--text-secondary); font-size: .8rem; }
  label { display: grid; gap: 4px; margin: 10px 0; color: var(--text-secondary); font-size: .8rem; }
  input { padding: 8px; color: var(--text-primary); background: var(--bg-tertiary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); }
  .status { color: var(--accent-sand); font-size: .8rem; }
  .status.online { color: var(--accent-warm); }
  .error { color: var(--accent-danger); }
  .actions { display: flex; gap: 8px; margin-top: 12px; }
</style>
