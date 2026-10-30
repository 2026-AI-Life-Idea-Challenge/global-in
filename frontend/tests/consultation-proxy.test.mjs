// Run after `next build --webpack`. Uses a synthetic backend, never a paid API.
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';

const session = 'a'.repeat(32);
const expired = 'b'.repeat(32);
const calls = [];
const payload = { session_id: session, stage: 'result', reply: '공식 근거를 확인하세요.', profile: { nationalities: ['KR'] },
  programs: [{ program_id: 'CA:iec', name: 'IEC', country: 'canada', visa_type: 'working_holiday', summary: '교류 프로그램' }],
  eligibility: [{ program_id: 'CA:iec', overall: '추가 확인 필요', requirements: [] }],
  citations: [{ chunk_id: 'c1', title: '공식 안내', source_url: 'https://canada.ca/' }],
  prep_items: [{ id: 'p1', program_id: 'CA:iec', title: '서류 확인', description: '공식 안내 확인', status: 'check_needed', done: false }] };
const mock = http.createServer(async (req, res) => {
  assert.equal(req.headers['x-internal-api-key'], 'synthetic-test-key');
  let text = ''; for await (const part of req) text += part;
  const body = text ? JSON.parse(text) : {};
  calls.push({ method: req.method, url: req.url, body });
  res.setHeader('Content-Type', 'application/json');
  if (req.url.includes(expired)) { res.writeHead(404); res.end('{}'); return; }
  if (req.method === 'PATCH' && body.invalid) { res.writeHead(422); res.end('{}'); return; }
  res.end(JSON.stringify(req.url === '/consult/sessions' ? { session_id: session } : payload));
});
mock.listen(0, '127.0.0.1'); await once(mock, 'listening');
const portProbe = http.createServer(); portProbe.listen(0, '127.0.0.1'); await once(portProbe, 'listening');
const port = portProbe.address().port; await new Promise(resolve => portProbe.close(resolve));
const app = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '-p', String(port), '-H', '127.0.0.1'], {
  cwd: process.cwd(), windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
  env: { ...process.env, BACKEND_URL: `http://127.0.0.1:${mock.address().port}`, INTERNAL_API_KEY: 'synthetic-test-key' },
});
let output = ''; app.stdout.on('data', chunk => output += chunk); app.stderr.on('data', chunk => output += chunk);
const base = `http://127.0.0.1:${port}`;
let passed = 0;
async function send(method, body) {
  return fetch(base + '/api/chat', { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}
try {
  const deadline = Date.now() + 45000;
  while (true) {
    try { if ((await fetch(base)).ok) break; } catch { /* Wait for this test's server. */ }
    if (app.exitCode !== null || Date.now() > deadline) throw new Error('Test frontend failed to start: ' + output);
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  let result = await send('POST', { messages: [{ role: 'user', content: '캐나다 워홀' }] });
  assert.equal(result.status, 200); let data = await result.json();
  assert.equal(data.programs[0].program_id, 'CA:iec'); assert.deepEqual(data.eligibility, payload.eligibility);
  assert.deepEqual(data.citations, payload.citations); assert.deepEqual(data.prep_items, payload.prep_items); passed++;
  result = await send('POST', { session_id: session, messages: [{ role: 'user', content: '준비 항목' }] });
  assert.equal(result.status, 200); assert.equal(calls.filter(c => c.url === '/consult/sessions').length, 1); passed++;
  const before = calls.length;
  assert.equal((await send('POST', { messages: [] })).status, 400);
  assert.equal((await send('POST', { session_id: '../bad', messages: [{ role: 'user', content: '질문' }] })).status, 400);
  assert.equal(calls.length, before); passed++;
  assert.equal((await send('POST', { session_id: expired, messages: [{ role: 'user', content: '질문' }] })).status, 404); passed++;
  result = await send('PATCH', { session_id: session, profile: { nationalities: ['KR'], target_country: null } });
  assert.equal(result.status, 200); data = await result.json(); assert.equal(data.content, payload.reply);
  assert.equal(calls.at(-1).body.target_country, null); passed++;
  assert.equal((await send('PATCH', { session_id: session, profile: { invalid: true } })).status, 422);
  assert.equal((await send('PATCH', { session_id: expired, profile: {} })).status, 404); passed++;
  result = await send('POST', { profile: { nationalities: ['KR'] }, messages: [{ role: 'user', content: '일본 취업' }] });
  assert.equal(result.status, 200);
  assert.deepEqual(calls.slice(-3).map(c => c.method), ['POST', 'PATCH', 'POST']); passed++;
  assert.ok((await (await fetch(base + '/profile')).text()).includes('type="date"'));
  assert.ok((await (await fetch(base + '/compare')).text()).includes('상담에서 선택한 실제 프로그램'));
  passed++;
  console.log(`${passed} frontend proxy/SSR checks passed; synthetic backend only.`);
} finally {
  app.kill(); mock.closeAllConnections(); await new Promise(resolve => mock.close(resolve));
}
