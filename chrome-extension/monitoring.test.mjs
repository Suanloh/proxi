import assert from 'node:assert/strict';
import test from 'node:test';

function event() {
  return { addListener(listener) { this.fire = listener; } };
}

const state = {};
const badges = new Map();
const popupUrl = 'chrome-extension://proxi/popup.html';
const popup = { id: 'proxi', url: popupUrl, origin: 'chrome-extension://proxi' };
let activeTab;
globalThis.chrome = {
  action: {
    setBadgeBackgroundColor: async () => {},
    setBadgeText: async ({ tabId, text }) => badges.set(tabId, text),
  },
  runtime: { id: 'proxi', getURL: (path) => `chrome-extension://proxi/${path.replace(/^\//, '')}`, onMessage: event() },
  storage: { session: {
    get: async (key) => ({ [key]: structuredClone(state[key]) }),
    set: async (values) => Object.assign(state, structuredClone(values)),
    remove: async (key) => { delete state[key]; },
  } },
  tabs: { query: async () => [activeTab], onUpdated: event(), onRemoved: event(), onReplaced: event() },
};

await import('./worker.js');

const send = (type) => new Promise((resolve) => {
  assert.equal(chrome.runtime.onMessage.fire({ type }, popup, resolve), true);
});

function navigate(id, url) {
  chrome.tabs.onUpdated.fire(id, url ? { url } : { status: 'complete' }, { url });
}

async function observations() {
  return (await send('monitor_state')).events.filter(({ type }) => type === 'navigation');
}

test('only explicit, same-origin tab activity is observed and never stores the full URL', async () => {
  const site = 'https://flights.example';
  activeTab = { id: 10, url: `${site}/initial`, status: 'complete' };
  navigate(10, `${site}/before-opt-in`);
  assert.deepEqual(await observations(), []);
  assert.equal(chrome.runtime.onMessage.fire({ type: 'monitor_start' }, { ...popup, url: `${site}/` }, () => {}), false);
  assert.equal((await send('monitor_start')).session.origin, site);
  assert.equal(badges.get(10), 'MON');

  navigate(11, `${site}/other-tab`);
  navigate(10, `${site}/private?q=secret#fragment`);
  navigate(10, `${site}/next`);
  const entries = await observations();
  assert.equal(entries.length, 2);
  for (const entry of entries) {
    assert.deepEqual(entry, { type: 'navigation', timestamp: entry.timestamp, origin: site });
  }

  navigate(10, undefined);
  navigate(10, `${site}/back`);
  assert.equal((await send('monitor_state')).session, null);
  assert.equal(badges.get(10), '');
  assert.equal((await observations()).length, 2);
});

test('stop and tab closure end observation; unavailable pages cannot opt in', async () => {
  activeTab = { id: 20, url: 'https://example.org/', status: 'complete' };
  await send('monitor_start');
  const stop = send('monitor_stop');
  navigate(20, 'https://example.org/after-stop');
  assert.equal((await stop).session, null);
  assert.equal((await send('monitor_state')).events[0].reason, 'user_stopped');

  await send('monitor_start');
  chrome.tabs.onRemoved.fire(20);
  const closed = await send('monitor_state');
  assert.equal(closed.session, null);
  assert.equal(closed.events[0].reason, 'tab_closed');

  activeTab = { id: 21, url: 'chrome://settings/', status: 'complete' };
  assert.match((await send('monitor_start')).error, /HTTP\(S\)/);
});
