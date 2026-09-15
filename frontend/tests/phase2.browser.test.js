import assert from 'node:assert/strict';
import test from 'node:test';
import { chromium } from 'playwright';

const APP_URL = process.env.APP_URL || 'http://127.0.0.1:5173';
const API_URL = process.env.API_URL || 'http://localhost:8000';
async function authenticatedPage(context) {
  const page = await context.newPage();
  await page.goto(APP_URL);
  // Phase 2 is local-first; use a syntactically valid JWT-shaped token so the
  // browser exercises the authenticated route without requiring Neo4j writes.
  const token = await page.evaluate(() => {
    const encode = value => btoa(JSON.stringify(value)).replaceAll('=', '');
    return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: crypto.randomUUID(), exp: Math.floor(Date.now() / 1000) + 3600 })}.acceptance`;
  });
  await page.evaluate(value => localStorage.setItem('burner_access_token', value), token);
  await page.evaluate(url => import('/src/lib/api/client.js').then(({ setBaseUrl }) => setBaseUrl(url)), API_URL);
  // A full reload can wait indefinitely while the SPA keeps long-lived API/WebSocket
  // requests open. Navigate to the authenticated route and wait for the document
  // commit instead; the route guard still exercises token-backed app startup.
  await page.goto(`${APP_URL}/#/`, { waitUntil: 'commit' });
  await page.getByRole('heading', { name: 'Peer sync' }).waitFor();
  // The panel lazily initializes the identity on connect, so obtain the same
  // persisted identity directly before filling the remote peer field.
  const peerId = await page.evaluate(async () => {
    const { identityStore } = await import('/src/lib/local/localRuntime.js');
    return (await identityStore.initialize()).id;
  });
  return { page, peerId };
}

async function appendPost(page, content) {
  await page.evaluate(async postContent => {
    const { identityStore, store } = await import('/src/lib/local/localRuntime.js');
    const { createPostEvent } = await import('/src/lib/protocol/postEvents.js');
    const { appendLocalEvent } = await import('/src/lib/local/localFirst.js');
    const identity = await identityStore.initialize();
    const event = await createPostEvent(identity, { content: postContent, image_url: null, visibility: 'public' }, identityStore);
    await appendLocalEvent(store, event);
  }, content);
}

async function replicaState(page, remotePeerId) {
  return page.evaluate(async peerId => {
    const { store } = await import('/src/lib/local/localRuntime.js');
    const events = await store.getEventsAfter(null, { limit: 100 });
    return {
      cursor: await store.getPeerCursor(peerId),
      events: events.map(event => ({ id: event.event_id, body: event.payload?.content })),
    };
  }, remotePeerId);
}

test('two browser replicas exchange a signed local post', async () => {
  const browser = await chromium.launch({
    headless: true,
    // Playwright contexts need routable host candidates for local two-browser
    // WebRTC; mDNS .local candidates are isolated between contexts on Windows.
    args: ['--disable-features=WebRtcHideLocalIpsWithMdns'],
  });
  const room = `phase2-${Date.now()}`;
  const first = await authenticatedPage(await browser.newContext());
  const second = await authenticatedPage(await browser.newContext());

  await appendPost(first.page, 'two-browser phase 2 post');

  for (const peer of [first, second]) {
    await peer.page.getByLabel('Room ID').fill(room);
  }
  await first.page.getByLabel('Remote peer ID').fill(second.peerId);
  await second.page.getByLabel('Remote peer ID').fill(first.peerId);
  // The signaling server does not replay offers to peers that join later. Join
  // the non-initiator first, then let the lexicographically smaller peer send
  // its offer to an already-connected signaling socket.
  const initiator = first.peerId < second.peerId ? first : second;
  const responder = initiator === first ? second : first;
  await responder.page.getByRole('button', { name: 'Connect peer' }).click();
  await initiator.page.getByRole('button', { name: 'Connect peer' }).click();
  await first.page.getByText(/^(connected|synchronized)$/, { exact: true }).waitFor({ timeout: 15000 });
  await second.page.getByText(/^(connected|synchronized)$/, { exact: true }).waitFor({ timeout: 15000 });
  // Explicitly replay hello after both data handlers are installed; this also
  // makes the acceptance deterministic across WebRTC implementations.
  await first.page.getByRole('button', { name: 'Retry sync' }).click();

  let received = null;
  for (let attempt = 0; attempt < 60 && !received; attempt += 1) {
    received = await second.page.evaluate(async () => {
      const { store } = await import('/src/lib/local/localRuntime.js');
      return (await store.getEventsAfter(null, { limit: 100 })).find(event => event.payload?.content === 'two-browser phase 2 post') || null;
    });
    if (!received) await second.page.waitForTimeout(250);
  }
  assert.ok(received, 'remote replica did not receive the signed post');
  assert.equal(received.payload.content, 'two-browser phase 2 post');

  const initialState = await replicaState(second.page, first.peerId);
  assert.equal(initialState.cursor, received.event_id);
  assert.equal(initialState.events.filter(event => event.id === received.event_id).length, 1);

  await second.page.getByRole('button', { name: 'Disconnect' }).click();
  await second.page.getByText('offline', { exact: true }).waitFor();

  await appendPost(first.page, 'post created while peer was offline');
  const missing = await first.page.evaluate(async () => {
    const { store } = await import('/src/lib/local/localRuntime.js');
    return (await store.getEventsAfter(null, { limit: 100 })).find(event => event.payload?.content === 'post created while peer was offline');
  });

  await second.page.getByRole('button', { name: 'Connect peer' }).click();
  await second.page.getByText(/^(connected|synchronized)$/, { exact: true }).waitFor({ timeout: 15000 });
  await second.page.waitForFunction(async eventId => {
    const { store } = await import('/src/lib/local/localRuntime.js');
    return (await store.getEventsAfter(null, { limit: 100 })).some(event => event.event_id === eventId);
  }, missing.event_id, { timeout: 15000 });

  const resumedState = await replicaState(second.page, first.peerId);
  assert.equal(resumedState.cursor, missing.event_id);
  assert.equal(resumedState.events.filter(event => event.id === received.event_id).length, 1);
  assert.equal(resumedState.events.filter(event => event.id === missing.event_id).length, 1);

  const projection = await second.page.evaluate(async () => {
    const { store } = await import('/src/lib/local/localRuntime.js');
    const { rebuildStore } = await import('/src/lib/projections/projector.js');
    return rebuildStore(store);
  });
  const projectedBodies = Object.values(projection.posts).map(post => post.content);
  assert.equal(projectedBodies.filter(body => body === 'two-browser phase 2 post').length, 1);
  assert.equal(projectedBodies.filter(body => body === 'post created while peer was offline').length, 1);
  await browser.close();
});
