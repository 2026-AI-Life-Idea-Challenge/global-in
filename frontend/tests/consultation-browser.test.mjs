// Browser interactions against synthetic /api/chat responses; never calls an LLM.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';

export async function runBrowserChecks(base, fixture) {
  const require = createRequire(import.meta.url);
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/ko/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_EXECUTABLE });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  let failed = false, expired = false, revision = 1, checks = 0;
  let profileUpdate;
  const result = () => ({ ...fixture, content: `테스트 상담 결과 ${revision}`, reply: `테스트 상담 결과 ${revision}`,
    follow_up_questions: [{ field: 'repeated', question: `테스트 상담 결과 ${revision}`, input_type: 'text' }],
    ...(profileUpdate ? { profile: profileUpdate } : {}),
    answer_sections: fixture.answer_sections.map(section => ({ ...section, text: `테스트 상담 결과 ${revision}` })),
    programs: [ { ...fixture.programs[0], summary: `최신 설명 ${revision}` },
      { program_id: 'AU:417', name: '호주 워홀', country: 'australia', visa_type: 'working_holiday', summary: '공식 근거 확인 필요' },
      { program_id: 'DE:study', name: '독일 유학', country: 'germany', visa_type: 'student', summary: '검증용 후보' },
      { program_id: 'US:study', name: '미국 유학', country: 'usa', visa_type: 'student', summary: '검증용 후보' } ] });
  await page.route('**/api/chat', async route => {
    if (expired) return route.fulfill({ status: 404, json: { error: '만료' } });
    if (failed) return route.fulfill({ status: 503, json: { error: '테스트 오류' } });
    await route.fulfill({ json: result() });
  });
  await page.route('**/api/preparation', async route => {
    const body=route.request().postDataJSON();
    assert.ok(body.profile && typeof body.target_id === 'string');
    await route.fulfill({json:{items:[{id:'personal:'+body.target_id+':evidence',program_id:body.target_id,title:'프로필 기준 증빙 준비',description:'저장된 프로필과 실제 규칙 비교 결과',done:false,status:'todo',citations:[{title:'공식 증빙 안내',source_url:'https://example.org/evidence'}]}]}});
  });
  const saved = async key => page.evaluate(name => JSON.parse(sessionStorage.getItem(name) || 'null'), key);
  async function question(text) {
    await page.getByPlaceholder('편하게 이야기해 주세요.').fill(text);
    await page.getByPlaceholder('편하게 이야기해 주세요.').press('Enter');
    await page.getByText(`테스트 상담 결과 ${revision}`, { exact: true }).last().waitFor();
  }
  try {
    await page.goto(base + '/profile');
    await page.locator('input').first().fill('한국');
    await page.locator('input[type="date"]').fill('1998-05-15');
    await page.locator('input').nth(2).fill('대한민국');
    await page.getByRole('button', { name: '프로필 저장하기', exact: true }).click();
    await page.getByRole('status').filter({ hasText: '프로필을 저장했습니다' }).waitFor();
    assert.equal((await saved('global-in-profile')).profile.date_of_birth, '1998-05-15'); checks++;
    await page.reload(); await page.locator('input[type="date"][value="1998-05-15"]').waitFor(); checks++;
    await page.getByRole('button', { name: /이 정보로 상담하기/ }).click();
    await question('프로그램 추천해줘');
    assert.equal(await page.getByText('추가 확인: 테스트 상담 결과 1', { exact: true }).count(), 0); checks++;
    assert.equal(await page.getByRole('button', { name: /플랜에 추가$/ }).count(), 3); checks++;
    await page.getByText('근거 적용 범위·인용 구절', { exact: true }).first().click();
    await page.getByText('2026년 취업 개시자 안내 기준', { exact: false }).first().waitFor();
    await page.getByRole('link', { name: /공식 안내/ }).first().waitFor(); checks++;
    assert.equal(await page.locator('a[href^="/programs/"]').count(), 0); checks++;
    assert.equal(await page.locator('nav a[href="/compare"]').count(), 0); checks++;
    await page.getByLabel('비교하기').first().check();
    await page.getByLabel('비교하기').nth(1).check();
    await page.waitForFunction(() => JSON.parse(sessionStorage.getItem('global-in-compare') || '[]').length === 2);
    revision = 2; await question('조건 다시 확인해줘');
    await page.goto(base + '/compare');
    await page.getByText('최신 설명 2', { exact: true }).waitFor(); checks++;
    await page.goto(base + '/preparation');
    await page.getByRole('checkbox').first().check();
    await page.reload(); await page.getByRole('checkbox').first().waitFor();
    assert.equal(await page.getByRole('checkbox').first().isChecked(), true); checks++;
    await page.goto(base + '/chat'); await page.getByText('테스트 상담 결과 2', { exact: true }).last().waitFor(); checks++;
    failed = true; await page.goto(base + '/profile');
    await page.locator('input[type="date"]').fill('1999-05-15');
    await page.getByRole('button', { name: '프로필 저장하기', exact: true }).click();
    await page.getByRole('status').filter({ hasText: '재검토에 실패' }).waitFor();
    assert.equal((await saved('global-in-profile')).profile.date_of_birth, '1999-05-15');
    assert.equal((await saved('global-in-chat-state')).profile_pending, true);
    assert.equal(await saved('global-in-consult-result'), null);
    assert.deepEqual(await saved('global-in-compare'), []); checks++;
    failed = false; revision = 3;
    await page.getByRole('button', { name: '프로필 저장하기', exact: true }).click();
    await page.getByRole('status').filter({ hasText: '재검토 결과를 갱신' }).waitFor();
    assert.equal((await saved('global-in-chat-state')).profile_pending, false); checks++;
    expired = true; await page.getByRole('button', { name: '프로필 저장하기', exact: true }).click();
    await page.getByRole('status').filter({ hasText: '상담이 만료' }).waitFor();
    assert.equal(await saved('global-in-chat-state'), null);
    assert.ok(await saved('global-in-profile')); checks++;
    expired = false; await page.getByRole('button', { name: /이 정보로 상담하기/ }).click();
    revision = 4; await question('새 상담');
    expired = true; await page.getByPlaceholder('편하게 이야기해 주세요.').fill('만료 확인');
    await page.getByPlaceholder('편하게 이야기해 주세요.').press('Enter');
    await page.getByText(/상담이 만료되어 이전 결과를 정리했습니다/).waitFor();
    assert.equal((await saved('global-in-chat-state')).session_id, null);
    assert.ok(await saved('global-in-profile')); checks++;
    expired = false; revision = 5; await question('복구 질문'); checks++;
    await page.getByRole('button', { name: '새 채팅', exact: true }).first().click();
    await page.waitForFunction(() => JSON.parse(sessionStorage.getItem('global-in-chat-state') || '{}').session_id === null); checks++;
    await page.setViewportSize({ width: 390, height: 844 });
    for (const path of ['/profile', '/chat', '/compare', '/preparation', '/programs']) {
      await page.goto(base + path);
      await page.getByRole('navigation', { name: '모바일 메뉴' }).waitFor();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Mobile overflow at ${path}`);
    }
    await page.getByRole('status', { name: /검색 결과/ }).waitFor();
    await page.getByRole('button', { name: '지원제도', exact: true }).click();
    await page.getByRole('checkbox', { name: /검증용 지원제도 비교/ }).check();
    await page.getByRole('button', { name: '프로그램', exact: true }).click();
    await page.getByRole('checkbox', { name: /IEC 비교/ }).check();
    await page.goto(base + '/compare');
    await page.getByRole('columnheader', { name: '검증용 지원제도', exact: true }).waitFor();
    await page.getByRole('columnheader', { name: 'IEC', exact: true }).waitFor(); checks++;
    await page.getByRole('link', { name: '테스트 공식 출처', exact: true }).waitFor();
    assert.equal(await page.getByRole('link', { name: '테스트 공식 출처', exact: true }).getAttribute('href'), 'https://canada.ca/'); checks++;
    await page.goto(base + '/programs/CA%3Aiec');
    await page.getByRole('heading', { name: 'IEC', exact: true }).waitFor();
    await page.getByText('테스트 데이터셋의 신청 요건입니다.', { exact: true }).waitFor(); checks++;
    await page.getByRole('link', { name: /테스트 공식 출처/ }).waitFor(); checks++;
    await page.goto(base + '/programs');
    await page.getByRole('textbox', { name: '프로그램 검색' }).fill('존재하지않는테스트');
    await page.reload();
    await page.getByRole('status', { name: '검색 결과 0개', exact: true }).waitFor();
    assert.equal(await page.getByRole('textbox', { name: '프로그램 검색' }).inputValue(), '존재하지않는테스트'); checks++;
    await page.getByRole('textbox', { name: '프로그램 검색' }).fill('');
    let catalogFails = true;
    await page.route('**/api/catalog', route => catalogFails ? route.fulfill({ status: 503, json: { error: '테스트 조회 오류' } }) : route.continue());
    await page.reload(); await page.getByRole('alert').filter({ hasText: '테스트 조회 오류' }).waitFor();
    catalogFails = false; await page.getByRole('button', { name: '다시 불러오기' }).click();
    await page.getByRole('status', { name: '검색 결과 1개', exact: true }).waitFor(); checks++;
    await page.goto(base + '/preparation');
    await page.getByRole('button', { name: '플랜 모두 삭제', exact: true }).click();
    await page.getByRole('heading', { name: '아직 준비 중인 항목이 없어요.', exact: true }).waitFor();
    await page.reload(); await page.getByRole('heading', { name: '아직 준비 중인 항목이 없어요.', exact: true }).waitFor(); checks++;
    await page.goto(base + '/programs');
    await page.getByRole('button', { name: 'IEC 플랜에 추가', exact: true }).click();
    await page.getByRole('button', { name: 'IEC 플랜에 추가', exact: true }).click();
    await page.getByRole('button', { name: '지원제도', exact: true }).click();
    await page.getByRole('button', { name: '검증용 지원제도 플랜에 추가', exact: true }).click();
    await page.getByRole('status').filter({hasText:'개인별 준비 항목'}).last().waitFor();
    await page.goto(base + '/preparation');
    assert.equal(await page.getByRole('checkbox').count(), 2); checks++;
    await mkdir('../tmp/browser-checks', { recursive: true });
    await page.screenshot({ path: '../tmp/browser-checks/plan-controls-mobile.png', fullPage: true });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.screenshot({ path: '../tmp/browser-checks/plan-controls-desktop.png', fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole('textbox', { name: '새 준비 항목' }).fill('여권 준비');
    await page.getByRole('button', { name: '항목 추가', exact: true }).click();
    await page.getByRole('button', { name: '여권 준비 수정', exact: true }).click();
    await page.getByRole('textbox', { name: '준비 항목 이름 수정' }).fill('여권 사본 준비');
    await page.getByRole('button', { name: '수정 저장', exact: true }).click();
    await page.getByRole('checkbox', { name: '여권 사본 준비', exact: true }).check();
    await page.reload(); assert.ok(await page.getByRole('checkbox', { name: '여권 사본 준비', exact: true }).isChecked()); checks++;
    await page.getByRole('button', { name: '여권 사본 준비 삭제', exact: true }).click();
    assert.equal(await page.getByRole('checkbox').count(), 2); checks++;
    await page.getByRole('button', { name: '플랜 모두 삭제', exact: true }).click();
    await page.reload(); await page.getByRole('heading', { name: '아직 준비 중인 항목이 없어요.', exact: true }).waitFor(); checks++;
    await page.goto(base + '/chat'); revision = 6;
    profileUpdate = { nationalities: ['KR', 'CA'], date_of_birth: '1997-04-03', residence_country: 'KR', major: '컴퓨터공학', target_country: 'japan', target_visa_type: 'student' };
    await question('프로필 정보 변경');
    await page.goto(base + '/programs/CA%3Aiec');
    await page.getByRole('heading', { name: 'IEC', exact: true }).waitFor(); checks++;
    await page.goto(base + '/chat');
    await page.getByRole('button', { name: 'IEC 플랜에 추가', exact: true }).last().click();
    await page.getByRole('status').filter({hasText:'개인별 준비 항목'}).last().waitFor();
    await page.goto(base + '/profile');
    await page.locator('input[type="date"][value="1997-04-03"]').waitFor();
    assert.equal(await page.getByPlaceholder('예: 컴퓨터공학').inputValue(), '컴퓨터공학');
    const synced = await saved('global-in-profile');
    assert.deepEqual(synced.form.selectedCountries, ['일본']); assert.deepEqual(synced.form.selectedPurposes, ['유학']);
    assert.deepEqual(synced.profile.nationalities, ['KR','CA']); checks++;
    await page.goto(base + '/preparation'); await page.getByRole('checkbox', { name: '프로필 기준 증빙 준비', exact: true }).waitFor(); checks++;
    await page.goto(base + '/programs');
    await mkdir('../tmp/browser-checks', { recursive: true });
    await page.screenshot({ path: '../tmp/browser-checks/d-mobile.png', fullPage: false }); checks++;
    assert.deepEqual(errors, []);
    console.log(`${checks} real Chromium browser flow checks passed; synthetic API only.`);
  } catch (error) {
    await mkdir('../tmp/browser-checks', { recursive: true });
    await page.screenshot({ path: '../tmp/browser-checks/d-failure.png', fullPage: true });
    throw error;
  } finally { await browser.close(); }
}
