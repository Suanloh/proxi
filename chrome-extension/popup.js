import { dashboardUrl, tokenPattern } from './config.js';

const el = (id) => document.getElementById(id);
el('dashboard').href = dashboardUrl;
let token = '';
let refreshing = false;

const labels = {
  ActionAllowed: 'Allowed', ActionHeld: 'Approval required', ActionBlocked: 'Blocked',
  CapabilityRevoked: 'Capability revoked', SessionRevoked: 'Agent session revoked',
  AuthenticationDenied: 'Authentication denied', ExpiredCredentialAttempt: 'Expired agent credential attempt',
  PolicyViolation: 'Security notification: policy violation', CapabilityViolation: 'Security notification: capability violation',
};

const obsLabels = {
  monitoring_started: 'Monitoring started',
  navigation: 'Navigation',
  monitoring_stopped: 'Monitoring stopped',
};

function renderMonitoring(session, events = [], error = '') {
  const statusEl = el('monitor-status');
  const errEl = el('monitor-error');

  errEl.textContent = error;
  errEl.hidden = !error;

  if (session) {
    const badge = document.createElement('span');
    badge.className = 'badge-mon';
    badge.textContent = 'MON';
    statusEl.replaceChildren(badge, document.createTextNode(`Observing ${session.origin}`));
    el('monitor-start').hidden = true;
    el('monitor-stop').hidden = false;
  } else {
    statusEl.textContent = 'Not monitoring any tab.';
    el('monitor-start').hidden = false;
    el('monitor-stop').hidden = true;
  }

  el('observed-events').replaceChildren(...events.map((evt) => {
    const item = document.createElement('li');
    item.textContent = [
      new Date(evt.timestamp).toLocaleTimeString(),
      obsLabels[evt.type] ?? evt.type,
      evt.origin,
      evt.reason ? `(${evt.reason})` : '',
    ].filter(Boolean).join(' · ');
    return item;
  }));
}

function render(message, status) {
  el('connection').textContent = message;
  el('protection').textContent = !status ? 'Unknown' : status.controlled_browser === 'configured' ?
    'Configured for supported PROXI actions only' : 'Not configured';
  el('operations').textContent = status?.operations.join(', ') ?? 'Unavailable';
  el('events').replaceChildren(...(status?.events ?? []).map(event => {
    const item = document.createElement('li');
    item.textContent = [new Date(event.created_at).toLocaleTimeString(), labels[event.event_type] ?? event.event_type,
      event.action, event.reason].filter(Boolean).join(' · ');
    return item;
  }));
}

async function refresh() {
  if (!token || refreshing) return;
  refreshing = true;
  try {
    const reply = await chrome.runtime.sendMessage({ type: 'status', token });
    if (!reply) throw new Error('Companion worker did not reply.');
    if (reply.unpair) token = '';
    el('token').required = !token;
    render(reply.status ? 'Connected to local PROXI.' : reply.error, reply.status);
  } catch {
    render('Companion could not get a response.', null);
  } finally {
    refreshing = false;
  }
}

async function updateMonitoring(type) {
  try {
    const reply = await chrome.runtime.sendMessage({ type });
    if (!reply) {
      showMonitorError('Tab monitoring did not respond. Reopen the popup, or reload PROXI Companion at chrome://extensions.');
      return;
    }
    if (reply.error) {
      showMonitorError(reply.error);
      return;
    }
    renderMonitoring(reply.session, reply.events);
  } catch {
    showMonitorError('Could not reach PROXI Companion. Reopen the popup, or reload the extension at chrome://extensions.');
  }
}

function showMonitorError(message) {
  el('monitor-error').textContent = message;
  el('monitor-error').hidden = false;
}

el('monitor-start').addEventListener('click', () => updateMonitoring('monitor_start'));
el('monitor-stop').addEventListener('click', () => updateMonitoring('monitor_stop'));

el('pair').addEventListener('submit', (event) => {
  event.preventDefault();
  if (refreshing) return;
  const entered = el('token').value.trim();
  el('token').value = '';
  if (entered) {
    if (!tokenPattern.test(entered)) {
      token = '';
      el('token').required = true;
      render('Invalid pairing token format.', null);
      return;
    }
    token = entered;
  }
  refresh();
});

updateMonitoring('monitor_state');

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'session' && (changes.monitoredSession || changes.observedEvents)) {
    updateMonitoring('monitor_state');
  }
});

setInterval(refresh, 5000);