export function createResumeController({ connect, resync = async () => {}, onStatus = () => {}, maxAttempts = 5, delayMs = 250, backoff = 2 }) {
  let stopped = false;
  return {
    async resume() {
      stopped = false;
      let lastError;
      for (let attempt = 1; attempt <= maxAttempts && !stopped; attempt += 1) {
        onStatus('reconnecting');
        try {
          await connect();
          await resync();
          onStatus('connected');
          return;
        } catch (error) {
          lastError = error;
          if (attempt < maxAttempts) await new Promise(resolve => setTimeout(resolve, delayMs * backoff ** (attempt - 1)));
        }
      }
      onStatus('failed');
      throw lastError || new Error('reconnect stopped');
    },
    stop() { stopped = true; },
  };
}
