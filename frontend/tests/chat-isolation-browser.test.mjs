import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

export async function runChatIsolationChecks(base) {
  const require=createRequire(import.meta.url);
  const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/ko/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
  const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_EXECUTABLE});
  const context=await browser.newContext({viewport:{width:1280,height:900}});
  const page=await context.newPage();
  const oldId='a'.repeat(32), calls=[], memory=new Map([[oldId,{profile:{nationalities:['KR'],target_country:'australia'},questions:['호주 워홀 설명']}]]);
  let sequence=0, count=0;
  const chats=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('global-in-chats') || '[]'));
  const state=()=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('global-in-chat-state') || '{}'));
  await page.route('**/api/chat',async route=>{
    const body=route.request().postDataJSON(); calls.push(body);
    const id=body.session_id || (++sequence).toString(16).padStart(32,'0');
    const entry=memory.get(id) || {profile:{...body.profile},questions:[]};
    const question=body.messages.filter(message=>message.role==='user').at(-1).content;
    entry.questions.push(question);
    if(question.includes('일본'))entry.profile.target_country='japan';
    memory.set(id,entry);
    await route.fulfill({json:{session_id:id,content:'답변: '+entry.questions.join(' / '),profile:entry.profile,programs:[],support_programs:[]}});
  });
  async function send(text){
    await page.getByPlaceholder('편하게 이야기해 주세요.').fill(text);
    const pending=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/chat' && response.request().method()==='POST');
    await page.getByPlaceholder('편하게 이야기해 주세요.').press('Enter');
    const response=await pending;
    const data=await response.json();
    await page.getByText(data.content,{exact:true}).last().waitFor();

  }
  async function blank(){
    await page.waitForFunction(()=>JSON.parse(sessionStorage.getItem('global-in-chat-state') || '{}').session_id===null);
    assert.equal((await state()).messages.filter(message=>message.role==='user').length,0); count++;
  }
  try {
    await page.goto(base+'/chat');
    await page.evaluate(id=>{
      sessionStorage.setItem('global-in-profile',JSON.stringify({profile:{nationalities:['KR'],target_country:'australia'},explicitProfile:{nationalities:['KR']}}));
      sessionStorage.setItem('global-in-chat-state',JSON.stringify({session_id:id}));
      localStorage.setItem('global-in-active-chat','old-au');
      localStorage.setItem('global-in-chats',JSON.stringify([{id:'old-au',title:'호주 워홀 상담',sessionId:id,profile:{nationalities:['KR'],target_country:'australia'},messages:[{role:'user',content:'호주 워홀 설명'},{role:'assistant',content:'이전 호주 답변'}]}]));
    },oldId);
    await page.reload(); await blank(); assert.equal((await chats()).length,1); count++;
    await page.getByRole('button',{name:'호주 워홀 상담',exact:true}).click();
    await page.getByText('이전 호주 답변',{exact:true}).waitFor(); assert.equal((await chats()).length,1); count++;
    await page.getByRole('button',{name:'AI 상담',exact:true}).click(); await blank(); assert.equal((await chats()).length,1); count++;
    await send('여러 나라 비교해줘');
    assert.equal(calls.at(-1).session_id,null); assert.equal(calls.at(-1).profile.target_country,undefined);
    const comparisonId=(await state()).session_id;
    assert.notEqual(comparisonId,oldId); assert.equal((await chats()).length,2); count++;
    await send('비교 계속'); assert.equal(calls.at(-1).session_id,comparisonId); count++;
    await page.getByRole('button',{name:'호주 워홀 상담',exact:true}).click();
    await send('호주 이어서'); assert.equal(calls.at(-1).session_id,oldId); count++;
    await page.getByRole('button',{name:'여러 나라 비교해줘',exact:true}).click();
    await send('내 비교 이어서'); assert.equal(calls.at(-1).session_id,comparisonId);
    assert.ok(!memory.get(comparisonId).questions.some(text=>text.includes('호주'))); count++;
    await page.getByRole('button',{name:'새 채팅',exact:true}).click(); await blank();
    await page.getByRole('button',{name:'호주 워홀 상담',exact:true}).click(); assert.equal((await chats()).length,2); count++;
    await page.getByRole('button',{name:'새 채팅',exact:true}).click(); await blank();
    await send('일본 취업'); assert.equal(calls.at(-1).session_id,null); assert.equal(calls.at(-1).profile.target_country,undefined); assert.equal((await chats()).length,3); count++;
    await page.goto(base+'/programs'); await page.goto(base+'/chat'); await blank(); assert.equal((await chats()).length,3); count++;
    await page.getByRole('button',{name:'일본 취업',exact:true}).click();
    await page.setViewportSize({width:390,height:844});
    await page.getByRole('navigation',{name:'모바일 메뉴'}).getByRole('link',{name:'상담',exact:true}).click();
    await blank(); assert.equal((await chats()).length,3); count++;
    await send('새 대화'); assert.equal(calls.at(-1).session_id,null); assert.equal(calls.at(-1).profile.target_country,undefined); count++;
    console.log(`${count} chat entry/history/profile isolation browser checks passed; synthetic sessions only.`);
  } finally {await browser.close();}
}
