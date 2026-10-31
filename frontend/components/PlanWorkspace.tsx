"use client";
import Link from 'next/link';
import { useState, type CSSProperties } from 'react';
import { useRouter } from 'next/navigation';
import { personalizePlan, usePlans } from '@/lib/plans';
import { programName, programDescription } from '@/lib/catalog';
import { safeSource } from './ConsultationDetails';

const button: CSSProperties = { border: '1px solid var(--ln)', background: '#fff', borderRadius: 10, padding: '8px 14px', fontSize: '0.8rem', color: 'var(--ink)', cursor: 'pointer' };
const field: CSSProperties = { ...button, width: '100%', boxSizing: 'border-box', textAlign: 'left' };
const card: CSSProperties = { border: '1px solid var(--ln)', borderRadius: 14, background: '#fff', overflow: 'hidden' };
const muted: CSSProperties = { fontSize: '0.78rem', color: 'var(--mu)', lineHeight: 1.8 };
const badge: CSSProperties = { fontSize: '0.66rem', color: 'var(--ac)', background: 'var(--tn)', padding: '3px 6px', borderRadius: 5 };

export default function PlanWorkspace({ planner, onNotice }: { planner: ReturnType<typeof usePlans>; onNotice: (message: string) => void }) {
  const router = useRouter();
  const [selected, setSelected] = useState('');
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState('');
  const [stage, setStage] = useState('preparation');
  const [editing, setEditing] = useState<{ id: string; title: string; description: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const plan = planner.plans.find(row => row.target.id === selected) || planner.plans[0];
  if (!plan) return null;
  const targetId = String(plan.target.id);
  const name = programName(targetId, plan.target.name);
  const pending = plan.items.filter(item => item.status !== 'todo' && item.evidence?.length);
  function change(action: () => void) {
    try { action(); onNotice('플랜을 저장했습니다.'); return true; }
    catch (error) { onNotice(error instanceof Error ? error.message : '저장 실패'); return false; }
  }
  const ask = (question: string) => router.push('/chat?program=' + encodeURIComponent(name) + '&question=' + encodeURIComponent(question));
  return <section aria-label="상담 준비 체크리스트">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
      <strong style={{ fontSize: '0.85rem' }}>준비 중인 프로그램 {planner.plans.length}개</strong>
      <button style={button} onClick={() => change(planner.clear)}>플랜 모두 삭제</button>
    </div>
    <div role="tablist" aria-label="준비 중인 프로그램" style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
      {planner.plans.map(row => {
        const active = row.target.id === plan.target.id;
        const done = row.items.filter(item => item.done).length;
        return <button key={row.target.id} role="tab" aria-selected={active} onClick={() => { setSelected(String(row.target.id)); setEditing(null); }} style={{ ...button, width: 220, maxWidth: '100%', padding: 16, textAlign: 'left', background: active ? 'var(--tn)' : '#fff', borderColor: active ? 'var(--ac)' : 'var(--ln)' }}>
          <span style={{ display: 'flex', justifyContent: 'space-between', ...muted }}><span>{row.target.country}</span><span>{row.target.kind === 'support' ? '지원제도' : '프로그램'}</span></span>
          <strong style={{ display: 'block', fontSize: '0.84rem', margin: '10px 0', lineHeight: 1.6 }}>{programName(String(row.target.id), row.target.name)}</strong>
          <span style={muted}>할 일 {row.items.length}개 중 {done}개 완료</span>
          <div role="progressbar" aria-label={`${row.target.name} 준비 진행률`} aria-valuemin={0} aria-valuemax={row.items.length} aria-valuenow={done} style={{ height: 3, background: 'var(--ln)', marginTop: 8 }}><div style={{ height: '100%', background: 'var(--ac)', width: `${100 * done / Math.max(1, row.items.length)}%` }} /></div>
        </button>;
      })}
    </div>
    <p style={muted}>완료 수는 할 일의 진행 상황이며, 신청 자격이나 비자 승인을 뜻하지 않아요. 플랜은 이 브라우저에 저장됩니다.</p>
    <article style={{ ...card, background: 'var(--bg)', padding: 22, margin: '16px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div><span style={badge}>{plan.target.kind === 'support' ? '지원제도' : '프로그램'}</span><span style={muted}>　{plan.target.country} · {plan.target.type}</span><h3 style={{ margin: '10px 0 4px', fontSize: '1.15rem' }}>{name}</h3></div>
        <Link style={{ ...button, textDecoration: 'none' }} href={'/programs/' + encodeURIComponent(targetId)}>프로그램·지원제도 정보 보기 ↗</Link>
      </div>
      <p style={muted}>{programDescription(targetId, plan.target.desc || '선택한 경로의 준비 항목을 확인하세요.')}</p>
    </article>
    {!!pending.length && <section aria-label="확인이 필요한 조건" style={{ ...card, padding: 20, background: '#fffcf5', borderColor: '#ead9ad', margin: '18px 0 26px' }}>
      <strong style={{ fontSize: '0.86rem' }}>ⓘ 확인이 필요한 조건</strong>
      {pending.map(item => <div key={item.id} style={{ borderTop: '1px solid #ead9ad', marginTop: 12, paddingTop: 12 }}>
        <small style={{ color: '#9b7328' }}>{item.status === 'blocked' ? '부족 조건 보완 필요' : '사용자 정보·정책 근거 확인 필요'}</small>
        <p style={{ margin: '6px 0', fontSize: '0.82rem', fontWeight: 600 }}>{item.title}</p>
        <p style={{ ...muted, margin: 0 }}>아래 할 일과 공식 근거를 확인하고 상담에서 본인 정보를 보완해 주세요.</p>
      </div>)}
    </section>}
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap', margin: '22px 0 8px' }}>
      <div><h3 style={{ margin: 0, fontSize: '1rem' }}>준비 체크리스트</h3><p style={{ ...muted, margin: '6px 0' }}>AI가 제안한 준비 초안이에요. 필요한 할 일을 추가하거나 조정해 주세요.</p></div>
      <button style={button} onClick={() => setAdding(value => !value)}>＋ 할 일 추가</button>
    </div>
    <p style={{ display: 'flex', gap: 8 }}><span style={{ ...badge, color: 'var(--mu)', background: '#f0f1f5' }}>공식 준비 항목</span><span style={badge}>AI 추천</span><span style={{ ...badge, background: '#e9f4ee', color: '#458475' }}>내가 추가</span></p>
    {adding && <form style={{ ...card, padding: 16, marginBottom: 12, display: 'grid', gap: 10 }} onSubmit={event => { event.preventDefault(); if (title.trim() && change(() => planner.append(targetId, title, stage))) { setTitle(''); setAdding(false); } }}>
      <input style={field} aria-label="새 준비 항목" placeholder="추가할 준비 항목" required maxLength={200} value={title} onChange={event => setTitle(event.target.value)} />
      <select style={field} aria-label="준비 단계" value={stage} onChange={event => setStage(event.target.value)}><option value="preparation">신청 전 준비</option><option value="application">신청 준비</option><option value="after_arrival">승인·입국 후 준비</option></select>
      <div><button type="submit" style={button}>항목 추가</button>{' '}<button type="button" style={button} onClick={() => setAdding(false)}>취소</button></div>
    </form>}
    {[['preparation', '01 신청 전 준비'], ['application', '02 신청 준비'], ['after_arrival', '03 승인·입국 후 준비']].map(([phase, label]) => {
      const items = plan.items.filter(item => (item.stage || 'preparation') === phase);
      if (!items.length) return null;
      return <details key={phase} open style={{ ...card, marginBottom: 14 }}>
        <summary style={{ padding: '17px 20px', cursor: 'pointer', fontSize: '0.84rem', color: 'var(--ac)' }}>{label}<span style={{ float: 'right', color: 'var(--mu)' }}>{items.filter(item => item.done).length} / {items.length} 완료</span></summary>
        {items.map(item => <article key={item.id} style={{ borderTop: '1px solid var(--ln)', padding: '18px 20px' }}>
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 }}><input type="checkbox" checked={item.done} onChange={() => change(() => planner.toggle(targetId, item.id))} style={{ accentColor: 'var(--ac)', marginTop: 3, flexShrink: 0 }} /><span style={{ textDecoration: item.done ? 'line-through' : 'none', lineHeight: 1.7 }}>{item.title}</span><span aria-hidden="true" style={{ ...badge, flexShrink: 0 }}>{item.origin === 'manual' ? '내가 추가' : item.origin === 'official' ? '공식 준비 항목' : 'AI 추천'}</span></label>
          <div style={{ marginLeft: 25 }}>
            <p style={{ ...muted, margin: '7px 0' }}>{item.description}</p>
            {item.status !== 'todo' && <p style={{ fontSize: '0.73rem', color: '#9b7328', margin: '6px 0' }}>ⓘ {item.status === 'blocked' ? '선행 조건 보완 필요' : '추가 확인 · 실제 요건과 제출 자료는 신청 경로별로 확인하세요.'}</p>}
            {item.citations?.filter(source => safeSource(source.source_url)).slice(0, 2).map((source,index) => <a key={index} style={{ display: 'block', ...muted, color: 'var(--ac)', textDecoration: 'none' }} href={source.source_url} target="_blank" rel="noopener noreferrer">공식 정보 확인하기 ↗</a>)}
            {!!item.evidence?.length && <details style={muted}><summary>관련 요건·검토 근거 확인</summary>{item.evidence.map((entry,index) => <div key={index}><p>{entry.outcome} · {entry.reason}</p><p>{entry.text}</p></div>)}</details>}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 10 }}><button style={{ ...button, padding: '4px 8px', fontSize: '0.72rem' }} onClick={() => ask(item.title + ' 준비 방법을 알려줘')}>이 할 일에 대해 AI에게 질문</button><button style={{ ...button, padding: '4px 8px', fontSize: '0.72rem' }} aria-label={`${item.title} 수정`} onClick={() => setEditing({ id: item.id, title: item.title, description: item.description })}>수정</button><button style={{ ...button, padding: '4px 8px', fontSize: '0.72rem' }} aria-label={`${item.title} 삭제`} onClick={() => change(() => planner.remove(targetId, item.id))}>삭제</button></div>
            {editing?.id === item.id && <form style={{ display: 'grid', gap: 8, marginTop: 12 }} onSubmit={event => { event.preventDefault(); if (editing.title.trim() && change(() => planner.edit(targetId, editing.id, editing.title, editing.description))) setEditing(null); }}><input style={field} aria-label="준비 항목 이름 수정" maxLength={200} required value={editing.title} onChange={event => setEditing({ ...editing, title: event.target.value })} /><textarea style={field} aria-label="준비 항목 설명 수정" maxLength={2000} value={editing.description} onChange={event => setEditing({ ...editing, description: event.target.value })} /><div><button style={button}>수정 저장</button>{' '}<button type="button" style={button} onClick={() => setEditing(null)}>취소</button></div></form>}
          </div>
        </article>)}
      </details>;
    })}
    <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10, marginTop: 18 }}>
      <button style={{ ...button, background: 'var(--ink)', color: '#fff' }} onClick={() => ask('내 상황에 맞춰 준비 순서를 알려줘')}>AI에게 준비 방법 물어보기</button>
      <button style={{ ...button, color: '#b24a62' }} onClick={() => change(() => planner.removePlan(targetId))}>준비 목록에서 제거</button>
    </div>
    <p style={muted}><button style={button} disabled={busy} onClick={async () => { setBusy(true); try { await personalizePlan(plan.target, [], true); onNotice('현재 프로필 기준으로 준비 항목을 갱신했습니다.'); } catch (error) { onNotice(error instanceof Error ? error.message : '갱신 실패'); } finally { setBusy(false); } }}>{busy ? '검토 중…' : '준비 항목 다시 검토'}</button>{' '}<button style={button} onClick={() => router.push('/profile')}>조건 수정·재상담</button></p>
  </section>;
}
