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

  function signal(type, payload) {
    transport.send({ type, target_peer_id: remotePeerId, payload });
  }

  function attachChannel(nextChannel) {
    channel = nextChannel;
    channel.onopen = () => stateHandler('connected');
    channel.onclose = () => stateHandler('disconnected');
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
    if (message.type === 'offer') {
      await connection.setRemoteDescription(message.payload);
      const answer = await connection.createAnswer();
      await connection.setLocalDescription(answer);
      signal('answer', answer);
    } else if (message.type === 'answer') {
      await connection.setRemoteDescription(message.payload);
    } else if (message.type === 'ice' && message.payload) {
      await connection.addIceCandidate(message.payload);
    }
  }

  return {
    async start({ initiator = false } = {}) {
      connection = new RTCPeerConnectionImpl();
      connection.onicecandidate = ({ candidate }) => {
        if (candidate) signal('ice', candidate);
      };
      connection.onconnectionstatechange = () => stateHandler(connection.connectionState);
      connection.ondatachannel = ({ channel: nextChannel }) => attachChannel(nextChannel);
      unsubscribe = transport.onMessage(handleSignal);
      if (initiator) {
        attachChannel(connection.createDataChannel('blaze-events'));
        const offer = await connection.createOffer();
        await connection.setLocalDescription(offer);
        signal('offer', offer);
      }
    },
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
