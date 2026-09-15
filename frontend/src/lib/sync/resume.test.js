import assert from 'node:assert/strict';
import test from 'node:test';

import { createResumeController } from './resume.js';

test('resume controller retries connection and resyncs after reconnect', async () => {
  let attempts = 0;
  let resyncs = 0;
  const statuses = [];
  const controller = createResumeController({
    connect: async () => { attempts += 1; if (attempts < 3) throw new Error('offline'); },
    resync: async () => { resyncs += 1; },
    onStatus: status => statuses.push(status),
    maxAttempts: 3,
    delayMs: 0,
  });

  await controller.resume();
  assert.equal(attempts, 3);
  assert.equal(resyncs, 1);
  assert.deepEqual(statuses, ['reconnecting', 'reconnecting', 'reconnecting', 'connected']);
});

test('resume controller stops after bounded attempts', async () => {
  const controller = createResumeController({ connect: async () => { throw new Error('offline'); }, maxAttempts: 2, delayMs: 0 });
  await assert.rejects(controller.resume(), /offline/);
});
