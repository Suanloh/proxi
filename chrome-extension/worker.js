import { statusUrl, tokenPattern } from './config.js';

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

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  if (sender.id !== chrome.runtime.id || sender.url !== chrome.runtime.getURL('popup.html') ||
      sender.origin !== new URL(chrome.runtime.getURL('/')).origin ||
      !message || Object.keys(message).length !== 2 || message.type !== 'status' ||
      typeof message.token !== 'string' || !tokenPattern.test(message.token)) return false;
  status(message.token).then(reply);
  return true;
});
