"use client";

export interface ConsultationDetailsData {
  eligibility?: { program_id: string; overall: string; requirements: { requirement_id: string; outcome: string }[] }[];
  citations?: { chunk_id: string; title: string; source_url: string }[];
  prep_items?: { id: string; program_id: string; title: string; description: string; status: string; done: boolean }[];
  follow_up_questions?: { field: string; question: string }[];
}

export function safeSource(url: string) {
  try { return ["http:", "https:"].includes(new URL(url).protocol); } catch { return false; }
}

export default function ConsultationDetails({ data }: { data: ConsultationDetailsData }) {
  return <section aria-label="상담 검토와 공식 근거" style={{ marginTop: 12, lineHeight: 1.7 }}>
    {data.eligibility?.map(item => <details key={item.program_id}>
      <summary>{item.program_id} · {item.overall}</summary>
      <p>항목별 검토 결과이며 최종 비자 발급·선정 결과를 의미하지 않습니다.</p>
      {item.requirements.map((rule, index) => <p key={`${rule.requirement_id}-${index}`}>{rule.requirement_id} · {rule.outcome}</p>)}
    </details>)}
    {!!data.citations?.length && <div><strong>공식 출처</strong><ul>
      {data.citations.filter(item => safeSource(item.source_url)).map((item, index) => <li key={`${item.chunk_id}-${index}`}>
        <a href={item.source_url} target="_blank" rel="noopener noreferrer">{item.title}</a>
      </li>)}
    </ul></div>}
    {!!data.prep_items?.length && <p>준비 항목 {data.prep_items.length}개 · <a href="/preparation">내 계획 확인하기 →</a></p>}
    {data.follow_up_questions?.map((question, index) => <p key={`${question.field}-${index}`}>추가 확인: {question.question}</p>)}
  </section>;
}
