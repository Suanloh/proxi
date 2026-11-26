import { statusUrl, tokenPattern } from './config.js';

const MAX_OBSERVED_EVENTS = 25;
let monitoringQueue = Promise.resolve();

function runMonitoring(operation) {
  const result = monitoringQueue.then(operation);
  monitoringQueue = result.catch(() => {});
  return result;
}

function pageOrigin(url) {
  try {
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.origin : null;
  } catch {
    return null;
  }
}

async function status(token) {
  try {
    const response = await fetch(statusUrl, {
      method: 'POST', credentials: 'omit', redirect: 'error', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: '{}', signal: AbortSignal.timeout(5000),
    });
    if (response.status === 401) return { error: 'Pairing expired or invalid. Mint a new token.', unpair: true };
    if (response.status === 403) return { error: 'Backend rejected this companion. Check the configured Chrome extension ID.' };
    if (!response.ok) return { error: 'Local backend could not provide status.' };
    return { status: await response.json() };
  } catch {
    return { error: 'Local backend disconnected. Protection status is unknown.' };
  }
}

async function getSession() {
  const { monitoredSession } = await chrome.storage.session.get('monitoredSession');
  return monitoredSession || null;
}

async function getObservedEvents() {
  const { observedEvents = [] } = await chrome.storage.session.get('observedEvents');
  return observedEvents;
}

async function recordObservation({ type, origin, reason }) {
  const entry = {
    type,
    timestamp: new Date().toISOString(),
    origin,
    ...(reason ? { reason } : {}),
  };
  const current = await getObservedEvents();
  const updated = [entry, ...current].slice(0, MAX_OBSERVED_EVENTS);
  await chrome.storage.session.set({ observedEvents: updated });
  return updated;
}

async function stopMonitoring(reason = 'user_stopped') {
  const session = await getSession();
  if (!session) return { session: null, events: await getObservedEvents() };

  await chrome.storage.session.remove('monitoredSession');
  await chrome.action.setBadgeText({ tabId: session.tabId, text: '' }).catch(() => {});
  const events = await recordObservation({
    type: 'monitoring_stopped',
    origin: session.origin,
    reason,
  });
  return { session: null, events };
}

async function startMonitoring() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const origin = pageOrigin(tab?.url);
  if (!Number.isInteger(tab?.id) || !origin || tab.status === 'loading') {
    return { error: 'Open a fully loaded HTTP(S) page and try again.' };
  }

  const existing = await getSession();
  if (existing) return { session: existing, events: await getObservedEvents() };

  const session = { tabId: tab.id, origin };
  await chrome.action.setBadgeBackgroundColor({ tabId: tab.id, color: '#0d9488' });
  await chrome.action.setBadgeText({ tabId: tab.id, text: 'MON' });
  try {
    await chrome.storage.session.set({ monitoredSession: session });
  } catch (error) {
    await chrome.action.setBadgeText({ tabId: tab.id, text: '' }).catch(() => {});
    throw error;
  }

  const events = await recordObservation({ type: 'monitoring_started', origin });
  return { session, events };
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!changeInfo.url && !changeInfo.status) return;
  runMonitoring(async () => {
    const session = await getSession();
    if (session?.tabId !== tabId) return;

    // A completed navigation may no longer expose its URL after activeTab is revoked.
    if (changeInfo.url || tab.url || changeInfo.status === 'complete') {
      if (pageOrigin(changeInfo.url ?? tab.url) !== session.origin) {
        await stopMonitoring('origin_changed');
      } else if (changeInfo.url) {
        await recordObservation({ type: 'navigation', origin: session.origin });
      }
    }
  }).catch(() => {});
});

function stopForTab(tabId, reason) {
  runMonitoring(async () => {
    if ((await getSession())?.tabId === tabId) await stopMonitoring(reason);
  }).catch(() => {});
}

chrome.tabs.onRemoved.addListener((tabId) => stopForTab(tabId, 'tab_closed'));
chrome.tabs.onReplaced.addListener((_addedTabId, removedTabId) => stopForTab(removedTabId, 'tab_replaced'));

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  const expectedOrigin = chrome.runtime.getURL('/').slice(0, -1);
  if (
    sender.id !== chrome.runtime.id ||
    sender.url !== chrome.runtime.getURL('popup.html') ||
    sender.origin !== expectedOrigin ||
    !message ||
    typeof message.type !== 'string'
  ) {
    return false;
  }

  const keys = Object.keys(message);

  if (message.type === 'status' && keys.length === 2 &&
      typeof message.token === 'string' && tokenPattern.test(message.token)) {
    status(message.token).then(reply);
    return true;
  }

  if (keys.length === 1) {
    const operation = {
      monitor_state: async () => ({ session: await getSession(), events: await getObservedEvents() }),
      monitor_start: startMonitoring,
      monitor_stop: () => stopMonitoring('user_stopped'),
    };
    if (Object.hasOwn(operation, message.type)) {
      runMonitoring(operation[message.type]).then(reply, () => reply({ error: 'Tab monitoring is unavailable.' }));
      return true;
    }
  }

  return false;
});