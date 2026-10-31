"use client";
import { useEffect, useState } from 'react';
import { useParams, useRouter } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import { useCatalog } from '@/lib/useCatalog';
import { CATEGORY_NAMES, AVAILABILITY_NAMES, catalogCountry } from '@/lib/catalog';
import { safeSource } from '@/components/ConsultationDetails';
import ProgramRequirements, { type DatasetSection } from '@/components/ProgramRequirements';

const FLAGS: Record<string, string> = {
  독일: '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  일본: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  호주: '<rect width="30" height="20" fill="#00247d"/><path d="M0 0l14 9M14 0L0 9" stroke="#fff" strokeWidth="1.6"/><path d="M7 0v9M0 4.5h14" stroke="#fff" strokeWidth="3"/><path d="M7 0v9M0 4.5h14" stroke="#cf142b" strokeWidth="1.6"/>',
  미국: '<rect width="30" height="20" fill="#fff"/><rect y="0" width="30" height="1.55" fill="#b22234"/><rect y="3.1" width="30" height="1.55" fill="#b22234"/><rect y="6.2" width="30" height="1.55" fill="#b22234"/><rect y="9.3" width="30" height="1.55" fill="#b22234"/><rect y="12.4" width="30" height="1.55" fill="#b22234"/><rect y="15.5" width="30" height="1.55" fill="#b22234"/><rect y="18.6" width="30" height="1.55" fill="#b22234"/><rect width="13" height="10.8" fill="#3c3b6e"/>',
  캐나다: '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/><path d="M15 4l1.3 3 2-1-.6 4 1.7-.4-.4 1.8 1.5 1-3.5 2.4.2 2.2h-4.4l.2-2.2-3.5-2.4 1.5-1-.4-1.8 1.7.4-.6-4 2 1z" fill="#d52b1e"/>',
};

type ProgramDetail = {
  id: string; type: string; country: string | null; tags: string[]; name: string;
  desc: string; sub: string; officialUrl: string; details?: string;
  stages?: { id: string; label: string; details: string; sub: string }[];
  links?: { label: string; url: string }[];
};
function FlagSvg({ country, size = 22 }: { country: string; size?: number }) {
  if (!FLAGS[country]) return null;
  return (
    <svg
      viewBox="0 0 30 20"
      style={{ width: size, height: Math.round(size * 2 / 3), borderRadius: 2, flexShrink: 0 }}
      dangerouslySetInnerHTML={{ __html: FLAGS[country] }}
    />
  );
}

export default function ProgramDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { items, loading, error, retry } = useCatalog();
  const rawId = typeof params?.id === 'string' ? params.id : '';
  let id = rawId;
  try { id = decodeURIComponent(rawId); } catch { /* Invalid links remain not found. */ }
  if (id === 'KR_US_WEST') id = 'US:US-WEST-01';
  const [dataset, setDataset] = useState<{ id: string; sections?: DatasetSection[]; error?: string }>({ id: '' });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!id) return;
    const controller = new AbortController();
    Promise.all((id === 'US:US-WEST-01' ? [id, 'KR_US_WEST'] : [id]).map(target => fetch('/api/catalog/' + encodeURIComponent(target), { signal: controller.signal, cache: 'no-store' }).then(async response => { if (target !== id && !response.ok) return { sections: [] }; const data = await response.json(); if (!response.ok) throw new Error(data.error || '상세 자료 조회 실패'); return data; }))).then(results => ({ sections: results.flatMap(result => result.sections || []) }))
            .then(data => { if (!controller.signal.aborted) setDataset({ id, sections: data.sections || [] }); })
      .catch(error => { if (!controller.signal.aborted) setDataset({ id, error: error instanceof Error ? error.message : '조회 실패' }); });
    return () => controller.abort();
  }, [id, revision]);
  const sections = dataset.id === id ? dataset.sections : undefined;
  const requirements = dataset.id === id && dataset.error ? <span role="alert">{dataset.error} <button onClick={() => setRevision(value => value + 1)}>다시 불러오기</button></span>
    : sections ? <ProgramRequirements sections={sections} /> : <span role="status">데이터셋의 요건·서류·절차를 불러오는 중…</span>;
  const item = items.find(p => p.id === id || encodeURIComponent(p.id) === id);
  const family = item?.id.match(/^(AU:subclass_(?:417|462)_)/)?.[1];
  const stages = family ? items.filter(p => p.id.startsWith(family)).sort((a,b) => ['first','second','third'].indexOf(a.id.slice(family.length)) - ['first','second','third'].indexOf(b.id.slice(family.length))) : [];
  const activeStage = Math.max(0, stages.findIndex(p => p.id === item?.id));
  const program: ProgramDetail | undefined = item ? {
    id: item.id, type: item.kind === 'support' ? '지원제도' : '프로그램',
    country: catalogCountry(item), tags: [catalogCountry(item), CATEGORY_NAMES[item.category || ''] || '공식 자료'],
    name: family ? `호주 ${family.includes('417') ? '워킹홀리데이 비자 417' : '워크앤홀리데이 비자 462'}` : item.name, desc: item.description || item.name,
    sub: item.kind === 'support' ? '저장된 모집 상태: ' + (AVAILABILITY_NAMES[item.availability] || '현재 접수 여부 미확인') : '개인별 자격 조건은 상담과 공식 근거를 통해 확인해 주세요.',
    details: item.description + (item.kind === 'support'
      ? ' 지원 대상과 제공 내용, 신청 방법을 구분해 살펴볼 수 있습니다. 비자·체류 자격과 지원제도 신청 자격은 별도로 확인해야 합니다.'
      : ' 아래에서 이 경로의 대상과 조건을 살펴보고, 준비가 필요하면 AI 상담과 개인별 플랜으로 이어갈 수 있습니다.'),
    officialUrl: item.sources.find(source => safeSource(source.source_url))?.source_url || '',
    links: item.sources.filter(source => safeSource(source.source_url)).map(source => ({ label: source.title, url: source.source_url })),
    stages: stages.length > 1 ? stages.map(stage => ({ id: stage.id,
      label: stage.id.endsWith('_first') ? '첫 신청' : stage.id.endsWith('_second') ? '2차 신청' : '3차 신청',
      details: stage.description || stage.name, sub: '신청 단계별 조건은 공식 근거와 상담에서 확인해 주세요.' })) : undefined,
  } : undefined;

  if (!program) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
        <Header rightLabel="프로그램 상세" />
        <div style={{ display: "flex", flex: 1, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px" }}>
          <Sidebar />
          <main style={{ flex: 1, padding: "24px 32px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ textAlign: "center" }}>
              <p role={error ? 'alert' : 'status'} style={{ color: "var(--mu)", marginBottom: 16 }}>{loading ? '프로그램 정보를 불러오는 중…' : error || '프로그램을 찾을 수 없어요.'}</p>
              {error && <button onClick={retry}>다시 불러오기</button>}
              <button onClick={() => router.push("/programs")} style={{ background: "var(--ink)", color: "#fff", border: "none", borderRadius: 10, padding: "10px 20px", cursor: "pointer" }}>
                목록으로
              </button>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      <Header rightLabel="프로그램 상세" />

      <div style={{ display: "flex", flex: 1, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px" }}>
        <Sidebar />

        <main style={{ flex: 1, padding: "24px 32px", minWidth: 0 }}>
          {/* 뒤로가기 */}
          <button
            onClick={() => router.back()}
            style={{
              display: "flex", alignItems: "center", gap: 6, fontSize: "0.82rem",
              color: "var(--mu)", background: "none", border: "none", cursor: "pointer",
              padding: "4px 0", marginBottom: 24,
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 5l-7 7 7 7"/>
            </svg>
            목록으로 돌아가기
          </button>

          {/* 헤더 카드 */}
          <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "28px 32px", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 20, flexWrap: "wrap" }}>
              {/* 국기 아이콘 */}
              <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--tn)", display: "grid", placeItems: "center", flexShrink: 0, overflow: "hidden" }}>
                {program.country ? (
                  <FlagSvg country={program.country} size={36} />
                ) : (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>
                  </svg>
                )}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                {/* 배지 */}
                <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: "0.72rem", fontWeight: 600, padding: "3px 10px", borderRadius: 6, background: "var(--tn)", color: "var(--ac)" }}>
                    {program.type}
                  </span>
                  {program.tags.map(t => (
                    <span key={t} style={{ fontSize: "0.72rem", color: "var(--mu)", padding: "3px 10px", borderRadius: 6, background: "#f0f1f5" }}>{t}</span>
                  ))}
                </div>

                <h1 style={{ margin: "0 0 8px", fontSize: "1.4rem", fontWeight: 800, letterSpacing: "-0.03em", color: "var(--ink)" }}>
                  {program.name}
                </h1>
                <p style={{ margin: 0, fontSize: "0.92rem", color: "#555", lineHeight: 1.6 }}>
                  {program.desc}
                </p>
              </div>
            </div>
          </div>

          <div className="program-detail-grid" style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 16, alignItems: "start" }}>
            {/* 왼쪽: 상세 설명 + 대상 조건 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {program.stages ? (
                /* 탭 UI: 다차 비자 (417/462 등) */
                <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "24px 28px" }}>
                  {/* 탭 버튼 */}
                  <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
                    {program.stages.map((stage, idx) => (
                      <button
                        key={idx}
                        onClick={() => router.replace(`/programs/${encodeURIComponent(stage.id)}`)}
                        style={{
                          padding: "6px 18px",
                          borderRadius: 20,
                          border: activeStage === idx ? "none" : "1px solid var(--ln)",
                          background: activeStage === idx ? "var(--ac)" : "transparent",
                          color: activeStage === idx ? "#fff" : "var(--mu)",
                          fontSize: "0.82rem",
                          fontWeight: activeStage === idx ? 600 : 400,
                          cursor: "pointer",
                          transition: "all 0.15s",
                        }}
                      >
                        {stage.label}
                      </button>
                    ))}
                  </div>
                  {/* 개요 */}
                  <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 개요</div>
                  <p style={{ margin: "0 0 20px", fontSize: "0.9rem", color: "var(--ink)", lineHeight: 1.8 }}>
                    {program.stages[activeStage].details}
                  </p>
                  {/* 대상·조건 */}
                  <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 대상·조건</div>
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ac)", flexShrink: 0, marginTop: 7 }} />
                    <div style={{ fontSize: "0.88rem", color: "var(--ink)", lineHeight: 1.7 }}>{requirements}</div>
                  </div>
                  <p style={{ margin: "12px 0 0", fontSize: "0.8rem", color: "var(--mu)", lineHeight: 1.6 }}>
                    자격 조건과 신청 요건은 변경될 수 있으니, 공식 사이트에서 최신 정보를 꼭 확인하세요.
                  </p>
                </div>
              ) : (
                <>
                  {/* 개요 */}
                  <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "24px 28px" }}>
                    <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 개요</div>
                    <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--ink)", lineHeight: 1.8 }}>
                      {program.details}
                    </p>
                  </div>

                  {/* 대상·조건 */}
                  <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "24px 28px" }}>
                    <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 대상·조건</div>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ac)", flexShrink: 0, marginTop: 7 }} />
                      <div style={{ fontSize: "0.88rem", color: "var(--ink)", lineHeight: 1.7 }}>{requirements}</div>
                    </div>
                    <p style={{ margin: "12px 0 0", fontSize: "0.8rem", color: "var(--mu)", lineHeight: 1.6 }}>
                      자격 조건과 신청 요건은 변경될 수 있으니, 공식 사이트에서 최신 정보를 꼭 확인하세요.
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* 오른쪽: 액션 카드 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* 공식 사이트 */}
              <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "20px 22px" }}>
                <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 공식 사이트</div>
                <p style={{ margin: "0 0 14px", fontSize: "0.82rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  신청 방법, 자격 요건, 최신 공지를 공식 사이트에서 확인하세요.
                </p>
                {program.links ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {program.links.map((link, idx) => (
                      <a
                        key={idx}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                          width: "100%", padding: "11px 0", borderRadius: 10,
                          border: "1.5px solid var(--ink)", background: "#fff",
                          fontSize: "0.88rem", fontWeight: 600, color: "var(--ink)",
                          textDecoration: "none", boxSizing: "border-box",
                        }}
                      >
                        {link.label}
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M7 7h10v10M7 17L17 7"/>
                        </svg>
                      </a>
                    ))}
                  </div>
                ) : (
                  <a
                    href={program.officialUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                      width: "100%", padding: "11px 0", borderRadius: 10,
                      border: "1.5px solid var(--ink)", background: "#fff",
                      fontSize: "0.88rem", fontWeight: 600, color: "var(--ink)",
                      textDecoration: "none", boxSizing: "border-box",
                    }}
                  >
                    공식 사이트 방문
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M7 7h10v10M7 17L17 7"/>
                    </svg>
                  </a>
                )}
              </div>

              {/* AI 상담하기 */}
              <div style={{ background: "#fff", border: "1.5px solid var(--ac)", borderRadius: 16, padding: "20px 22px" }}>
                <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 10 }}>● AI 상담</div>
                <p style={{ margin: "0 0 14px", fontSize: "0.82rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  이 프로그램에 대해 궁금한 점을 AI와 함께 알아보세요.
                </p>
                <button
                  onClick={() => router.push(`/chat?program=${encodeURIComponent(program.name)}&country=${encodeURIComponent(program.country ?? "")}`)}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                    width: "100%", padding: "11px 0", borderRadius: 10,
                    border: "1.5px solid var(--ac)", background: "var(--ac)",
                    fontSize: "0.88rem", fontWeight: 700, color: "#fff",
                    cursor: "pointer", boxSizing: "border-box",
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  AI와 상담하기
                </button>
              </div>

              {/* 안내 */}
              <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 12, padding: "14px 16px" }}>
                <p style={{ margin: 0, fontSize: "0.76rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  DB에 저장된 공식 자료입니다. 개인별 자격 요건과 현재 신청 정보는 공식 사이트에서 확인해 주세요.
                </p>
              </div>
            </div>
          </div>
        </main>
      </div>

      <footer style={{ display: "flex", justifyContent: "space-between", maxWidth: 1040, margin: "0 auto", width: "100%", padding: "20px 20px", fontSize: "0.78rem", color: "#ccc" }}>
        <span>Global-In.</span>
        <span>해외에서의 다음 시작을 함께.</span>
      </footer>
      <style jsx>{`@media (max-width: 767px) { .program-detail-grid { grid-template-columns: minmax(0, 1fr) !important; } }`}</style>
    </div>
  );
}
