export function createSignalingTransport({ url, roomId, peerId, WebSocketImpl = globalThis.WebSocket }) {
  let socket;
  const handlers = new Set();
  let connected = false;

  function endpoint() {
    const base = url.replace(/\/$/, '');
    return `${base}/sync/signaling/${encodeURIComponent(roomId)}?peer_id=${encodeURIComponent(peerId)}`;
  }

  return {
    connect() {
      if (socket && connected) return Promise.resolve();
      socket = new WebSocketImpl(endpoint());
      return new Promise((resolve, reject) => {
        socket.onopen = () => { connected = true; resolve(); };
        socket.onerror = () => reject(new Error('signaling connection failed'));
        socket.onclose = () => { connected = false; };
        socket.onmessage = ({ data }) => {
          try { handlers.forEach(handler => handler(JSON.parse(data))); } catch { /* ignore malformed signaling */ }
        };
      });
    },
    send(message) {
      if (!socket || !connected) throw new Error('signaling transport is not connected');
      socket.send(JSON.stringify(message));
    },
    onMessage(handler) { handlers.add(handler); return () => handlers.delete(handler); },
    close() { socket?.close(); connected = false; },
    get connected() { return connected; },
  };
}
