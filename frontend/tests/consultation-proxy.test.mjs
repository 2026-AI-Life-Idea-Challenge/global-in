// Run after `next build --webpack`. Uses a synthetic backend, never a paid API.
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';

const session = 'a'.repeat(32);
const expired = 'b'.repeat(32);
const calls = [];
const owners = new Map();
const payload = { session_id: session, stage: 'result', reply: '공식 근거를 확인하세요.', profile: { nationalities: ['KR'] },
  programs: [{ program_id: 'CA:iec', name: 'IEC', country: 'canada', visa_type: 'working_holiday', summary: '교류 프로그램' }],
  eligibility: [{ program_id: 'CA:iec', overall: '추가 확인 필요', requirements: [] }],
  citations: [{ chunk_id: 'c1', title: '공식 안내', source_url: 'https://canada.ca/' }],
  answer_sections: [{ title: '신청 조건', text: '공식 근거를 확인하세요.', target_name: 'IEC', scope_notes: ['2026년 취업 개시자 안내 기준'], citations: [{ title: '공식 안내', source_url: 'https://canada.ca/', verified_at: '2026-10-28' }] }],
  prep_items: [{ id: 'p1', program_id: 'CA:iec', title: '서류 확인', description: '공식 안내 확인', status: 'check_needed', done: false }],
  support_programs: [{ support_program_id: 'S:test', name: '검증용 지원제도', availability: 'CLOSED', source_verified_at: '2026-10-28', citations: [] }],
  support_eligibility: [{ support_program_id: 'S:test', overall: '추가 확인 필요', requirements: [] }],
  rag_statuses: [{ status: 'partial', development_only: true, unanswered_parts: [{ question_part: '추가 서류' }] }] };
const mock = http.createServer(async (req, res) => {
  assert.equal(req.headers['x-internal-api-key'], 'synthetic-test-key');
  if (!req.url.startsWith('/consult/catalog')) assert.match(req.headers['x-consult-owner'] || '', /^[a-f0-9]{64}$/);
  let text = ''; for await (const part of req) text += part;
  const body = text ? JSON.parse(text) : {};
  calls.push({ method: req.method, url: req.url, body });
  res.setHeader('Content-Type', 'application/json');
  if (req.url.startsWith('/consult/catalog/')) {
    const id = decodeURIComponent(req.url.slice('/consult/catalog/'.length));
    if (id !== 'CA:iec') { res.writeHead(404); res.end('{}'); return; }
    res.end(JSON.stringify({ id, name: 'IEC', sections: [{ id: 'fixture-chunk', title: '테스트 요건', body: '테스트 데이터셋의 신청 요건입니다.', document_title: '테스트 정책', verified_at: '2026-10-28', sources: [{ title: '공식 안내', source_url: 'https://canada.ca/' }] }] })); return;
  }
  if (req.url === '/consult/catalog') {
    res.end(JSON.stringify({ items: [
      ...payload.programs.map(p => ({ id: p.program_id, kind: 'program', name: p.name, country: p.country, category: p.visa_type,
        provider: null, destination_countries: ['CA'], availability: 'UNKNOWN', source_verified_at: '2026-10-28', release_id: 'test', sources: [{ title: '테스트 공식 출처', source_url: 'https://canada.ca/' }] })),
      ...payload.support_programs.map(p => ({ id: p.support_program_id, kind: 'support', name: p.name, country: 'multi_country', category: null,
        provider: '테스트 기관', destination_countries: ['CA'], availability: p.availability, source_verified_at: p.source_verified_at, release_id: 'test', sources: [] })),
    ] })); return;
  }
  if (req.url.includes(expired)) { res.writeHead(404); res.end('{}'); return; }
  if (req.url === '/consult/sessions') owners.set(session, req.headers['x-consult-owner']);
  else if (req.url.includes('/sessions/' + session) && owners.get(session) !== req.headers['x-consult-owner']) { res.writeHead(404); res.end('{}'); return; }
  if (req.method === 'PATCH' && body.invalid) { res.writeHead(422); res.end('{}'); return; }
  const failures = {
    'test-busy': [409, 'session request in progress'],
    'test-capacity': [503, 'consultation capacity reached'],
    'test-generation': [503, 'consultation temporarily unavailable'],
    'test-store': [503, 'session store temporarily unavailable'],
  };
  if (failures[body.message]) {
    const [status, detail] = failures[body.message];
    res.writeHead(status); res.end(JSON.stringify({ detail })); return;
  }
  if (body.profile?.invalid) { res.writeHead(422); res.end(JSON.stringify({ detail: [{ input: 'synthetic-private-value', loc: ['body','profile'] }] })); return; }
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
let ownerCookie;
async function send(method, body) {
  const result = await fetch(base + '/api/chat', { method, headers: { 'Content-Type': 'application/json', ...(ownerCookie ? { Cookie: ownerCookie } : {}) }, body: JSON.stringify(body) });
  const cookie = result.headers.get('set-cookie');
  if (cookie) { assert.match(cookie, /HttpOnly/i); assert.match(cookie, /SameSite=Strict/i); ownerCookie = cookie.split(';')[0]; }
  return result;
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
  assert.deepEqual(data.answer_sections, payload.answer_sections);
  const stolen = await fetch(base + '/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: session, messages: [{ role: 'user', content: '다른 브라우저' }] }) });
  assert.equal(stolen.status, 404); passed++;
  const crossOrigin = await fetch(base + '/api/chat', { method: 'PATCH', headers: { 'Content-Type': 'application/json', Origin: 'https://untrusted.example', Cookie: ownerCookie }, body: JSON.stringify({ session_id: session, profile: {} }) });
  assert.equal(crossOrigin.status, 403); passed++;
  const invalid = await send('POST', { session_id: session, profile_pending: true, profile: { invalid: true }, messages: [{ role: 'user', content: '검증' }] });
  assert.equal(invalid.status, 422); assert.ok(!(await invalid.text()).includes('synthetic-private-value')); passed++;
  const detail = await fetch(base + '/api/catalog/CA%3Aiec'); assert.equal(detail.status, 200);
  assert.equal((await detail.json()).sections[0].body, '테스트 데이터셋의 신청 요건입니다.'); passed++;
  assert.deepEqual(data.support_programs, payload.support_programs);
  assert.deepEqual(data.support_eligibility, payload.support_eligibility);
  assert.deepEqual(data.rag_statuses, payload.rag_statuses);
  result = await send('POST', { session_id: session, messages: [{ role: 'user', content: '준비 항목' }] });
  assert.equal(result.status, 200); assert.equal(calls.filter(c => c.url === '/consult/sessions').length, 1); passed++;
  for (const [message, code, retry] of [
    ['test-busy', 'session_busy', true], ['test-capacity', 'capacity_reached', true],
    ['test-generation', 'consultation_failed', false], ['test-store', 'session_store_unavailable', false],
  ]) {
    const failure = await send('POST', { session_id: session, messages: [{ role: 'user', content: message }] });
    const body = await failure.json();
    assert.equal(body.code, code);
    assert.equal(failure.headers.has('Retry-After'), retry);
    if (code === 'consultation_failed') assert.ok(!body.error.includes('혼잡'));
    passed++;
  }
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
  assert.deepEqual(calls.slice(-2).map(c => c.method), ['POST', 'POST']);
  assert.deepEqual(calls.at(-1).body.profile, { nationalities: ['KR'] }); passed++;
  result = await send('POST', { session_id: session, profile_pending: true, profile: { nationalities: ['KR'] }, messages: [{ role: 'user', content: '재검토 재시도' }] });
  assert.equal(result.status, 200);
  assert.equal(calls.at(-1).method, 'POST');
  assert.deepEqual(calls.at(-1).body.profile, { nationalities: ['KR'] }); passed++;
  assert.ok((await (await fetch(base + '/profile')).text()).includes('type="date"'));
  assert.ok((await (await fetch(base + '/compare')).text()).includes('상담과 목록에서 선택한 실제 프로그램'));
  passed++;
  console.log(`${passed} frontend proxy/SSR checks passed; synthetic backend only.`);
  if (process.env.RUN_BROWSER_TESTS === '1') {
    const { runBrowserChecks } = await import('./consultation-browser.test.mjs');
    await runBrowserChecks(base, payload);
    const { runChatIsolationChecks } = await import('./chat-isolation-browser.test.mjs');
    await runChatIsolationChecks(base);
  }
} finally {
  app.kill(); mock.closeAllConnections(); await new Promise(resolve => mock.close(resolve));
}
