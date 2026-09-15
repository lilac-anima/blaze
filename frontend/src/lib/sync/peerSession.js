const MAX_FRAME_BYTES = 128000;

export function createPeerSession({
  peerId,
  remotePeerId,
  transport,
  RTCPeerConnectionImpl = globalThis.RTCPeerConnection,
}) {
  if (!RTCPeerConnectionImpl) throw new Error('WebRTC is unavailable');
  let connection;
  let channel;
  let unsubscribe;
  let dataMessageHandler = () => {};
  let stateHandler = () => {};
  let restarting = false;
  let pendingCandidates = [];

  async function addPendingCandidates() {
    const candidates = pendingCandidates;
    pendingCandidates = [];
    for (const candidate of candidates) await connection.addIceCandidate(candidate);
  }

  function signal(type, payload) {
    transport.send({ type, target_peer_id: remotePeerId, payload });
  }

  async function createOffer() {
    const offer = await connection.createOffer();
    await connection.setLocalDescription(offer);
    signal('offer', offer);
  }

  function attachChannel(nextChannel) {
    channel = nextChannel;
    channel.onopen = () => stateHandler('connected');
    channel.onclose = () => { if (!restarting) stateHandler('disconnected'); };
    channel.onerror = () => stateHandler('failed');
    channel.onmessage = ({ data }) => {
      try {
        const value = typeof data === 'string' ? data : new TextDecoder().decode(data);
        if (new TextEncoder().encode(value).byteLength > MAX_FRAME_BYTES) return;
        dataMessageHandler(JSON.parse(value));
      } catch {
        stateHandler('invalid-message');
      }
    };
  }

  async function handleSignal(message) {
    if (message.peer_id !== remotePeerId) return;
    if (message.type === 'peer_joined') {
      if (peerId < remotePeerId) await createOffer();
    } else if (message.type === 'offer') {
      await connection.setRemoteDescription(message.payload);
      await addPendingCandidates();
      const answer = await connection.createAnswer();
      await connection.setLocalDescription(answer);
      signal('answer', answer);
    } else if (message.type === 'answer') {
      await connection.setRemoteDescription(message.payload);
      await addPendingCandidates();
    } else if (message.type === 'ice' && message.payload) {
      if (connection.remoteDescription) await connection.addIceCandidate(message.payload);
      else pendingCandidates.push(message.payload);
    }
  }

  return {
    async start({ initiator = false } = {}) {
      restarting = true;
      unsubscribe?.();
      channel?.close();
      connection?.close();
      pendingCandidates = [];
      connection = new RTCPeerConnectionImpl();
      connection.onicecandidate = ({ candidate }) => {
        if (candidate) signal('ice', candidate);
      };
      // The data channel is the synchronization boundary. Chromium can report
      // the RTCPeerConnection as connected before that channel is open; if we
      // publish "connected" here, the panel starts sync too early and
      // session.send() races the channel open event.
      connection.onconnectionstatechange = () => {
        if (connection.connectionState !== 'connected') stateHandler(connection.connectionState);
      };
      connection.ondatachannel = ({ channel: nextChannel }) => attachChannel(nextChannel);
      unsubscribe = transport.onMessage(handleSignal);
      if (initiator) {
        attachChannel(connection.createDataChannel('blaze-events'));
        await createOffer();
      }
      restarting = false;
    },
    async restart(options = {}) { return this.start(options); },
    send(message) {
      if (!channel || channel.readyState !== 'open') throw new Error('data channel is not open');
      const encoded = JSON.stringify(message);
      if (new TextEncoder().encode(encoded).byteLength > MAX_FRAME_BYTES) throw new Error('message exceeds frame limit');
      channel.send(encoded);
    },
    onDataMessage(handler) { dataMessageHandler = handler; },
    onStateChange(handler) { stateHandler = handler; },
    get channel() { return channel; },
    close() {
      unsubscribe?.();
      channel?.close();
      connection?.close();
      stateHandler('closed');
    },
  };
}

export { MAX_FRAME_BYTES };
