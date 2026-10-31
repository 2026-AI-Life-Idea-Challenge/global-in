"use client";
import ProgramActions from './ProgramActions';

type Requirement = { requirement_id: string; outcome: string; reason?: string | null; description?: string | null; pending_reviews?: { authority_id?: string; questions?: string[] }[] };

export interface ConsultationDetailsData {
  profile?: Record<string, unknown>;
  programs?: { program_id: string; name: string }[];
  answer_sections?: { title: string; text: string; target_name?: string | null; scope_notes?: string[]; citations: { title: string; source_url: string; verified_at?: string | null; quote?: string | null }[] }[];
  eligibility?: { program_id: string; overall: string; requirements: Requirement[] }[];
  citations?: { chunk_id: string; title: string; source_url: string }[];
  prep_items?: { id: string; program_id: string; title: string; description: string; status: string; done: boolean; citations?: { title: string; source_url: string }[] }[];
  follow_up_questions?: { field: string; question: string }[];
  support_programs?: { support_program_id: string; name: string; availability: string; source_verified_at?: string | null; citations?: { title: string; source_url: string }[] }[];
  support_eligibility?: { support_program_id: string; overall: string; requirements: Requirement[] }[];
  rag_statuses?: { status: string; development_only: boolean; unanswered_parts: { question_part: string }[] }[];
}

export function safeSource(url: string) {
  try { return ["http:", "https:"].includes(new URL(url).protocol); } catch { return false; }
}

export default function ConsultationDetails({ data, reply = '' }: { data: ConsultationDetailsData; reply?: string }) {
  return <section aria-label="상담 검토와 공식 근거" style={{ marginTop: 12, lineHeight: 1.7 }}>
    {data.rag_statuses?.some(item => item.development_only) && <p>현재 검색된 근거를 이용한 개발 검증 결과입니다. 최종 법률·자격 승인과 구분해 주세요.</p>}
    {[...new Set(data.rag_statuses?.flatMap(item => item.unanswered_parts.map(part => part.question_part)) || [])].map(part => <p key={part}>근거 추가 확인: {part}</p>)}
    {data.eligibility?.map(item => <details key={item.program_id}>
      <summary>{data.programs?.find(p => p.program_id === item.program_id)?.name || '프로그램'} · {item.overall}</summary>
      <p>항목별 검토 결과이며 최종 비자 발급·선정 결과를 의미하지 않습니다.</p>
      {item.requirements.map((rule, index) => <div key={`${rule.requirement_id}-${index}`}><p>확인 항목 {index + 1} · {rule.outcome}{rule.reason && ` · ${rule.reason}`}</p>{rule.description && <p>{rule.description}</p>}{rule.pending_reviews?.flatMap(review => review.questions || []).map((question,j) => <p key={j}>기관에 확인할 내용: {question}</p>)}</div>)}
    </details>)}
    {!!data.support_programs?.length && <div><strong>연결 후보 지원제도</strong>
      {data.support_programs.slice(0, Math.max(0, 3 - Math.min(data.programs?.length || 0, 3))).map(item => <article key={item.support_program_id} style={{ border: '1px solid var(--ln)', padding: 12, marginTop: 8 }}>
        <strong>{item.name}</strong><p>저장된 모집 상태: {({ OPEN: '접수 중으로 기록됨', CLOSED: '접수 종료로 기록됨', UPCOMING: '접수 예정으로 기록됨', UNKNOWN: '접수 여부 확인 필요' } as Record<string, string>)[item.availability] || '확인 필요'} · 확인일: {item.source_verified_at || '미확인'}</p>
        <p>목록 연결은 신청 자격이나 현재 접수 가능 여부를 확정하지 않습니다.</p>
        <ProgramActions item={{ id: item.support_program_id, name: item.name, kind: 'support', type: '지원제도', availability: item.availability, verifiedAt: item.source_verified_at, sources: item.citations }} prepItems={data.prep_items} showDetails={false} showCompare />
        {item.citations?.filter(c => safeSource(c.source_url)).map((c, index) => <p key={index}><a href={c.source_url} target="_blank" rel="noopener noreferrer">{c.title}</a></p>)}
      </article>)}
    </div>}
    {data.support_eligibility?.map(item => <details key={item.support_program_id}><summary>{data.support_programs?.find(p => p.support_program_id === item.support_program_id)?.name || '지원제도'} · {item.overall}</summary>
      {item.requirements.map((rule, index) => <div key={`${rule.requirement_id}-${index}`}><p>확인 항목 {index + 1} · {rule.outcome}{rule.reason && ` · ${rule.reason}`}</p>{rule.description && <p>{rule.description}</p>}{rule.pending_reviews?.flatMap(review => review.questions || []).map((question,j) => <p key={j}>기관에 확인할 내용: {question}</p>)}</div>)}
    </details>)}
    {!!data.citations?.length && <div><strong>공식 출처</strong>
      {!!data.answer_sections?.length && <details><summary>근거 적용 범위·인용 구절</summary>{data.answer_sections.map((section,index) => <div key={index}>
        <p>{section.target_name} · {section.title}</p>
        {section.scope_notes?.map(note => <p key={note}>{note}</p>)}
        {[...new Set(section.citations.map(c => c.quote).filter(Boolean))].map(quote => <blockquote key={quote}>{quote}</blockquote>)}
      </div>)}</details>}
      <ul>
      {data.citations.filter(item => safeSource(item.source_url)).map((item, index) => <li key={`${item.chunk_id}-${index}`}>
        <a href={item.source_url} target="_blank" rel="noopener noreferrer">{item.title}</a>
      </li>)}
    </ul></div>}
    {!!data.prep_items?.length && <p>준비 항목 {data.prep_items.length}개 · <a href="/preparation">내 계획 확인하기 →</a></p>}
    {data.follow_up_questions?.filter(question => !reply.replace(/\s+/g, '').includes(question.question.replace(/\s+/g, ''))).map((question, index) => <p key={`${question.field}-${index}`}>추가 확인: {question.question}</p>)}
  </section>;
}
