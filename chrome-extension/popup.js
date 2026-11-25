import { dashboardUrl, tokenPattern } from './config.js';

const el = (id) => document.getElementById(id);
el('dashboard').href = dashboardUrl;
let token = '';
let refreshing = false;
const labels = { ActionAllowed: 'Allowed', ActionHeld: 'Approval required', ActionBlocked: 'Blocked',
  CapabilityRevoked: 'Capability revoked', SessionRevoked: 'Agent session revoked',
  AuthenticationDenied: 'Authentication denied', ExpiredCredentialAttempt: 'Expired agent credential attempt',
  PolicyViolation: 'Security notification: policy violation', CapabilityViolation: 'Security notification: capability violation' };

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
    if (reply.unpair) token = '';
    el('token').required = !token;
    render(reply.status ? 'Connected to local PROXI.' : reply.error, reply.status);
  } catch {
    render('Companion could not get a response.', null);
  } finally {
    refreshing = false;
  }
}

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
setInterval(refresh, 5000);
