import { safeSource } from './ConsultationDetails';
export type DatasetSection = { id: string; title: string; body: string; document_title: string;
  verified_at?: string | null; effective_from?: string | null; effective_until?: string | null;
  sources: { title: string; source_url: string }[] };
export function datasetSectionLabel(title: string) {
  const categories: [RegExp, string][] = [
    [/passport|nationalit|citizen|여권|국적/i, '국적·여권'],
    [/funds|financial|잔고|자금|재정|생계/i, '재정·생활비'],
    [/child|dependant|dependent|자녀|부양|동반/i, '동반 가족'],
    [/education|qualification|degree|학력|학위|졸업|재학/i, '학력·재학 상태'],
    [/\bage\b|years old|연령/i, '연령 조건·예외'], [/occupation|직종/i, '직종 요건'],
    [/work experience|경력/i, '경력 요건'], [/skills assessment|기술심사/i, '기술 심사'],
    [/english|영어|어학/i, '어학 요건'], [/health|건강/i, '건강 요건'],
    [/character|품행/i, '품행 요건'], [/nominat|sponsor|지명|후원/i, '지명·후원 요건'],
    [/documents|서류/i, '필요 서류'], [/application|신청 절차/i, '신청 절차'],
    [/cost|charge|fee|비용|수수료/i, '비용·수수료'],
    [/benefit|scholarship|award|지원 내용|장학|지원금/i, '지원 내용'],
    [/stay|residen|체류|거주/i, '체류·거주 조건'],
    [/work|근로|근무/i, '근로·활동 조건'],
    [/period|deadline|기간|마감|일정/i, '신청 시기'],
  ];
  return categories.find(([pattern]) => pattern.test(title))?.[1] || '프로그램별 추가 조건';
}
const explanations: Record<string, string> = {
  '국적·여권': '신청에 사용하는 여권과 국적에 따라 이용할 수 있는 경로가 달라집니다. 복수 국적이나 여권 종류에 따른 조건도 함께 살펴보세요.',
  '재정·생활비': '체류 초기 생활비와 이동 비용 등 재정 준비에 관한 항목입니다. 인정되는 증빙과 본인에게 적용되는 기준을 확인해 준비하세요.',
  '동반 가족': '자녀나 가족 동반 여부에 따라 적용 조건이 달라질 수 있습니다. 본인의 동반 계획과 해당 경로의 가족 관련 조건을 함께 살펴보세요.',
  '학력·재학 상태': '학력·학위·재학 또는 졸업 상태와 관련된 항목입니다. 본인의 이력이 해당 경로의 기준에 맞는지 대조해 보세요.',
  '연령 조건·예외': '연령 조건은 신청 시점과 국적 등 적용 대상에 따라 확인해야 합니다. 생년월일과 신청 예정일을 기준으로 해당 규정을 살펴보세요.',
  '직종 요건': '예정 직무가 이 경로에 해당하는지 살펴보는 항목입니다. 직종 명칭뿐 아니라 실제 담당 업무와 관할 기관의 분류를 함께 확인하세요.',
  '경력 요건': '업무 경험의 분야·기간·증빙과 관련된 항목입니다. 본인의 근무 기간과 담당 업무를 정리해 비교해 보세요.',
  '기술 심사': '직무 능력의 평가나 자격 인정에 관한 항목입니다. 본인 경로의 심사 대상·평가기관·진행 시점을 확인하세요.',
  '어학 요건': '인정되는 언어 능력과 증빙에 관한 항목입니다. 시험 종류·성적·유효기간과 면제 규정의 적용 여부를 함께 살펴보세요.',
  '건강 요건': '건강 관련 심사·안내를 다루는 항목입니다. 본인에게 필요한 절차는 공식 신청 과정의 안내에 따라 확인하세요.',
  '품행 요건': '품행과 관련된 신청 질문·증빙을 다루는 항목입니다. 본인의 체류 이력과 신청 과정에서 요구하는 내용을 확인하세요.',
  '지명·후원 요건': '고용주·기관의 지명이나 후원과 관련된 항목입니다. 본인과 담당 기관이 각각 진행할 절차를 확인하세요.',
  '필요 서류': '신청 경로에서 요구하는 자료를 준비하는 단계입니다. 필수·조건부 자료를 구분하고 발급일·번역·제출 형식을 확인하세요.',
  '신청 절차': '접수 기관과 제출 순서를 살펴보는 항목입니다. 본인의 신청 위치·단계에 맞는 공식 경로를 선택해 진행하세요.',
  '비용·수수료': '해당 경로의 비용 유무와 납부 안내를 확인하는 항목입니다. 본인에게 적용되는 금액과 납부 시점을 확인한 뒤 진행하세요.',
  '지원 내용': '장학금·연수 등 이 제도에서 안내하는 지원 내용을 다루는 항목입니다. 대상·지원 범위와 지급 또는 이용 조건을 함께 살펴보세요.',
  '체류·거주 조건': '현재 거주지와 신청 장소, 체류 상태에 관한 항목입니다. 본인의 상황과 선택한 신청 경로를 대조하세요.',
  '근로·활동 조건': '체류 중 가능한 활동이나 근무 이력에 관한 항목입니다. 허용 범위와 활동 기간, 적용 예외를 함께 확인하세요.',
  '신청 시기': '접수 일정과 적용 기간을 살펴보는 항목입니다. 저장된 자료에 일정이 있더라도 현재 모집 여부는 공식 공고에서 다시 확인하세요.',
  '프로그램별 추가 조건': '이 경로에만 적용되는 추가 요건과 예외를 다룹니다. 자신의 신청 유형과 상황에 해당하는 내용을 확인하세요.',
};
function shortSourceText(section: DatasetSection) {
  // Keep complete, short Korean source sentences. Never crop a long condition mid-clause.
  return section.body.split(/\n+/).map(line => line.trim().replace(/^[-•●]\s*/, '')).find(line =>
    line.length >= 15 && line.length <= 220 && (line.match(/[가-힣]/g)?.length || 0) >= 8
    && !/적용 범위|원문 URL|검증일|source_|POL_/.test(line));
}
export default function ProgramRequirements({ sections }: { sections: DatasetSection[] }) {
  if (!sections.length) return <span>현재 연결된 데이터셋에서 표시할 요건 본문을 찾지 못했습니다.</span>;
  const groups = new Map<string, DatasetSection[]>();
  for (const section of sections) {
    const label = datasetSectionLabel(section.title);
    groups.set(label, [...(groups.get(label) || []), section]);
  }
  return <div>{[...groups].map(([label, records]) => <section key={label} style={{ marginBottom: 20 }}>
    <strong>{label}</strong>
    <p style={{ margin: '8px 0', lineHeight: 1.8 }}>{explanations[label]}</p>
    {[...new Set(records.map(shortSourceText).filter(Boolean))].slice(0, 2).map(text => <p key={text} style={{ margin: '8px 0', lineHeight: 1.8 }}>{text}</p>)}
    <details><summary style={{ color: 'var(--mu)', fontSize: '0.8rem', cursor: 'pointer' }}>공식 원문·예외 규정 보기</summary>
      {records.map(section => <div key={section.id} style={{ margin: '12px 0' }}>
        <p style={{ whiteSpace: 'pre-line' }}>{section.body}</p>
        <small>자료 확인일: {section.verified_at || '미확인'}{section.effective_from ? ` · 적용 시작: ${section.effective_from}` : ''}{section.effective_until ? ` · 적용 종료: ${section.effective_until}` : ''}</small>
        {section.sources.filter(source => safeSource(source.source_url)).map((source,i) => <p key={i}><a href={source.source_url} target="_blank" rel="noopener noreferrer">공식 근거 ↗</a></p>)}
      </div>)}
    </details>
  </section>)}</div>;
}
