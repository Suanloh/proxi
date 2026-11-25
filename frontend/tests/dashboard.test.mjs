import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:http';
import { test } from 'node:test';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium } from 'playwright';

const id = 'c9bd83ee-9c36-46ba-89a2-e7743ff23a5c';
const now = '2026-01-01T01:00:00Z';
const token = 'dashboard-fixture-owner';

async function bind(server) {
  const ready = once(server, 'listening');
  server.listen(0, '127.0.0.1');
  await ready;
  return server.address().port;
}

async function close(server) {
  await new Promise((resolve) => server.close(resolve));
}

function nativeForm(html, button) {
  const form = [...html.matchAll(/<form\b[^>]*>([\s\S]*?)<\/form>/g)].find(([, body]) => body.includes(`>${button}</button>`));
  assert.ok(form, `Form for ${button} is missing`);
  const data = new FormData();
  for (const [tag] of form[1].matchAll(/<input\b[^>]*>/g)) {
    if (!tag.includes('type="hidden"')) continue;
    const name = tag.match(/\bname="([^"]+)"/)?.[1];
    const value = tag.match(/\bvalue="([^"]*)"/)?.[1] ?? '';
    if (name) data.set(name, value.replace(/&quot;|&#x27;|&amp;|&lt;|&gt;/g, (entity) => ({'&quot;': '"', '&#x27;': "'", '&amp;': '&', '&lt;': '<', '&gt;': '>'})[entity]));
  }
  assert.ok([...data.keys()].some((name) => name.startsWith('$ACTION_')));
  return data;
}

test('dashboard renders backend data, forwards filters and approval reviews, and refreshes state', { timeout: 30000 }, async (t) => {
  const calls = [];
  let state = 'PENDING';
  let sessions = 7;
  const backend = createServer((req, res) => {
    req.resume();
    calls.push(`${req.method} ${req.url}`);
    res.setHeader('Content-Type', 'application/json');
    const send = (status, payload) => { res.statusCode = status; res.end(JSON.stringify(payload)); };
    if (req.headers.authorization !== `Bearer ${token}`) return send(401, {});
    const path = new URL(req.url, 'http://localhost').pathname.replace('/api/v1/', '');
    const trust = { score: 80, score_persisted: true, band: 'trusted' };
    const approval = { id, status: state, reason: 'Fixture review reason', expires_at: now, policy_version_ids: [],
      request: { agent_id: id, session_id: id, action: 'catalog.lookup', resource: 'fixture catalog', task_id: id } };
    switch (path) {
      case 'agents': return send(200, [{ id, name: 'Fixture agent', type: 'local', status: 'active', created_at: now }]);
      case `agents/${id}`: return send(200, { id, name: 'Fixture agent', type: 'local', status: 'active', created_at: now });
      case 'dashboard/overview': return send(200, { active_sessions: sessions, pending_approvals: Number(state === 'PENDING') });
      case `dashboard/agents/${id}`: return send(200, { sessions: [], tasks: [], capabilities: [], trust: { ...trust, history: [], restrictions: {mode: 'none', allowed_actions: []} } });
      case 'dashboard/trust': return send(200, [{ ...trust, agent_id: id, active_sessions: sessions }]);
      case 'dashboard/integrations': return send(200, [{ id: 'fixture', name: 'Fixture adapter', status: 'enabled', connection_status: 'unknown', operations: ['catalog.lookup'], detail: 'Test adapter' }]);
      case 'audit-logs': case 'security-events': case 'policies': return send(200, []);
      case 'approvals': return send(200, state === 'PENDING' ? [approval] : []);
      case `approvals/${id}`: return send(200, approval);
      case `approvals/${id}/reject`: return send(409, {});
      case `approvals/${id}/approve`:
        if (req.method !== 'POST') return send(405, {});
        state = 'APPROVED';
        return send(200, { ...approval, status: state });
      default: return send(404, {});
    }
  });
  const apiPort = await bind(backend);
  t.after(() => close(backend));
  const probe = createServer();
  const port = await bind(probe);
  await close(probe);
  const origin = `http://127.0.0.1:${port}`;
  const next = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', String(port)], {
    env: { ...process.env, PROXI_API_BASE_URL: `http://127.0.0.1:${apiPort}/api/v1`, PROXI_SECURE_COOKIES: 'false' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  next.stdout.on('data', (chunk) => { output += chunk; });
  next.stderr.on('data', (chunk) => { output += chunk; });
  t.after(async () => { if (next.exitCode === null && next.signalCode === null) { const exited = once(next, 'exit'); next.kill(); await exited; } });
  let home;
  for (let i = 0; i < 50 && next.exitCode === null; i++) {
    try { home = await fetch(origin); break; } catch { await delay(200); }
  }
  assert.ok(home, output);
  const get = async (path, cookie) => {
    const response = await fetch(`${origin}${path}`, { headers: { cookie }, redirect: 'manual' });
    assert.equal(response.status, 200, path);
    return response.text();
  };
  const signIn = nativeForm(await home.text(), 'Sign in');
  const guest = await fetch(`${origin}/agents`, {redirect: 'manual'});
  if (guest.status === 307) assert.equal(guest.headers.get('location'), '/');
  else assert.match(await guest.text(), /NEXT_REDIRECT;replace;\/;307/);
  const post = async (path, body, cookie = '') => {
    try {
      const response = await fetch(`${origin}${path}`, { method: 'POST', body, headers: { origin, cookie }, redirect: 'manual', signal: AbortSignal.timeout(5000) });
      return {status: response.status, headers: response.headers, html: await response.text()};
    } catch (error) {
      throw new Error(`POST ${path} failed: ${output}\n${calls.slice(-8).join('\n')}`, {cause: error});
    }
  };
  signIn.set('token', 'wrong-token');
  assert.match((await post('/', signIn)).html, /Owner access was not accepted/);
  signIn.set('token', token);
  const signedIn = await post('/', signIn);
  assert.equal(signedIn.status, 303);
  const setCookie = signedIn.headers.get('set-cookie');
  assert.match(setCookie, /HttpOnly/i);
  const cookie = setCookie.split(';')[0];
  for (const [path, label] of Object.entries({ '/': 'Security overview', '/agents': 'Fixture agent',
    [`/agents/${id}`]: 'Fixture agent', '/policies': 'Policies', '/approvals': 'Fixture review reason',
    '/monitor': 'Recently blocked actions', '/trust': 'Trust &amp; risk', '/audit': 'Owner audit trail',
    '/integrations': 'Fixture adapter', '/settings': 'Color theme' })) {
    assert.ok((await get(path, cookie)).includes(label), path);
  }
  assert.match(await get('/', cookie), />7<\/p>/);
  sessions = 9;
  assert.match(await get('/', cookie), />9<\/p>/);
  const beforeFilter = calls.length;
  await get(`/audit?agent_id=${id}&decision=BLOCK&since=2026-01-01&field=action&find=catalog.lookup`, cookie);
  const filtered = calls.slice(beforeFilter).find((call) => call.startsWith('GET /api/v1/audit-logs?'));
  assert.ok(filtered);
  const params = new URLSearchParams(filtered.split('?')[1]);
  assert.equal(params.get('agent_id'), id);
  assert.equal(params.get('decision'), 'BLOCK');
  assert.equal(params.get('action'), 'catalog.lookup');
  assert.ok(params.get('since')?.startsWith('2026-01-01'));
  const path = `/approvals/${id}`;
  const browser = await chromium.launch({ channel: process.env.PROXI_TEST_BROWSER_CHANNEL || undefined });
  t.after(() => browser.close());
  const context = await browser.newContext();
  await context.addCookies([{ name: cookie.split('=')[0], value: cookie.split('=')[1], url: origin }]);
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  await page.goto(`${origin}${path}`);
  page.once('dialog', (dialog) => dialog.dismiss());
  await page.getByRole('button', {name: 'Reject request'}).click();
  assert.equal(calls.some((call) => call.startsWith('POST ')), false);
  page.on('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', {name: 'Reject request'}).click();
  await page.getByRole('alert').filter({ hasText: 'rejected the operation in its current state' }).waitFor();
  await page.getByRole('button', {name: 'Approve request'}).click();
  await page.getByText('APPROVED', {exact: true}).waitFor();
  assert.match(await get('/approvals', cookie), /No requests awaiting review/);
  assert.deepEqual(calls.filter((call) => call.startsWith('POST ')), [
    `POST /api/v1/approvals/${id}/reject`, `POST /api/v1/approvals/${id}/approve`,
  ]);
});
