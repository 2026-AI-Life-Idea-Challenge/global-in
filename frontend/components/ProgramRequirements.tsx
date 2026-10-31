import { safeSource } from './ConsultationDetails';
import styles from './ProgramRequirements.module.css';
export type DatasetSection = { id: string; title: string; body: string; document_title: string;
  verified_at?: string | null; effective_from?: string | null; effective_until?: string | null;
  sources: { title: string; source_url: string }[] };
export function datasetSectionLabel(title: string) {
  const categories: [RegExp, string][] = [
    [/\bage\b|years old|연령/i, '연령 조건·예외'], [/occupation|직종/i, '직종 요건'],
    [/work experience|경력/i, '경력 요건'], [/skills assessment|기술심사/i, '기술 심사'],
    [/english|영어|어학/i, '어학 요건'], [/health|건강/i, '건강 요건'],
    [/character|품행/i, '품행 요건'], [/nominat|sponsor|지명|후원/i, '지명·후원 요건'],
    [/documents|서류/i, '필요 서류'], [/application|신청 절차/i, '신청 절차'],
  ];
  return categories.find(([pattern]) => pattern.test(title))?.[1] || title;
}
export default function ProgramRequirements({ sections }: { sections: DatasetSection[] }) {
  if (!sections.length) return <span>현재 연결된 데이터셋에서 표시할 요건 본문을 찾지 못했습니다.</span>;
  return <div className={styles.sections}>{sections.map((section,index) => <details className={styles.section} key={section.id} open={index < 2}>
    <summary className={styles.heading}>{datasetSectionLabel(section.title)}</summary>
    <div className={styles.content}>
      <p className={styles.body}>{section.body}</p>
      <div className={styles.metadata}>자료 확인일: {section.verified_at || '미확인'}{section.effective_from ? ` · 적용 시작: ${section.effective_from}` : ''}{section.effective_until ? ` · 적용 종료: ${section.effective_until}` : ''}</div>
      {section.sources.filter(source => safeSource(source.source_url)).map((source,i) => <a className={styles.source} key={i} href={source.source_url} target="_blank" rel="noopener noreferrer">공식 근거 확인 <span aria-hidden="true">↗</span><span className={styles.sourceTitle}>{section.document_title}</span></a>)}
    </div>
  </details>)}</div>;
}
