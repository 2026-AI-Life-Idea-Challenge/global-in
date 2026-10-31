"use client";
import { useState, useEffect } from "react";
import { useCatalog } from "@/lib/useCatalog";
import { useComparison } from "@/lib/useComparison";
import { CATEGORY_NAMES, COUNTRY_NAMES, AVAILABILITY_NAMES, catalogCountry, toCompared, type CatalogItem } from "@/lib/catalog";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import ProgramActions from '@/components/ProgramActions';
import { comparisonRows } from '@/lib/comparisonRows';
import type { ComparedItem } from '@/lib/useComparison';

const FLAGS: Record<string, string> = {
  독일: '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  일본: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  호주: '<rect width="30" height="20" fill="#00247d"/><path d="M0 0l14 9M14 0L0 9" stroke="#fff" strokeWidth="1.6"/><path d="M7 0v9M0 4.5h14" stroke="#fff" strokeWidth="3"/><path d="M7 0v9M0 4.5h14" stroke="#cf142b" strokeWidth="1.6"/>',
  미국: '<rect width="30" height="20" fill="#fff"/><rect y="0" width="30" height="1.55" fill="#b22234"/><rect y="3.1" width="30" height="1.55" fill="#b22234"/><rect y="6.2" width="30" height="1.55" fill="#b22234"/><rect y="9.3" width="30" height="1.55" fill="#b22234"/><rect y="12.4" width="30" height="1.55" fill="#b22234"/><rect y="15.5" width="30" height="1.55" fill="#b22234"/><rect y="18.6" width="30" height="1.55" fill="#b22234"/><rect width="13" height="10.8" fill="#3c3b6e"/>',
  캐나다: '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/><path d="M15 4l1.3 3 2-1-.6 4 1.7-.4-.4 1.8 1.5 1-3.5 2.4.2 2.2h-4.4l.2-2.2-3.5-2.4 1.5-1-.4-1.8 1.7.4-.6-4 2 1z" fill="#d52b1e"/>',
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


type Program = {
  id: string;
  type: string;
  country: string | null;
  tags: string[];
  name: string;
  desc: string;
  sub: string;
  officialUrl: string;
  destinations: string[];
  comparison: ComparedItem;
};

function toLegacyProgram(item: CatalogItem): Program {
  const country = catalogCountry(item);
  const purpose = (item.category === 'study' || item.category === 'student' ? '유학·교환학생' : CATEGORY_NAMES[item.category || ""]) ||
    (item.kind === "support" ? "장학·연수" : "기타");

  const officialUrl = item.sources.find(source => {
    try {
      const url = new URL(source.source_url);
      return url.protocol === "https:" || url.protocol === "http:";
    } catch {
      return false;
    }
  })?.source_url || "";

  return {
    id: item.id,
    type: item.kind === "support" ? "지원제도" : "프로그램",
    country: country === "여러 국가" ? null : country,
    tags: [country, purpose],
    name: item.name,
    desc: item.provider ? `운영 기관: ${item.provider}` :
      "공식 자료를 바탕으로 제공되는 프로그램 정보입니다.",
    sub: item.kind === "support"
      ? `저장된 모집 상태: ${AVAILABILITY_NAMES[item.availability] || "현재 접수 여부 미확인"}`
      : `공식 출처 확인일: ${item.source_verified_at || "자료별 확인 필요"}`,
    officialUrl,
    comparison: toCompared(item),
    destinations: item.kind === 'support' ? item.destination_countries.map(code => COUNTRY_NAMES[code] || code) : [country],
  };
}

const COUNTRIES = ["전체", "독일", "일본", "호주", "미국", "캐나다"];
const PURPOSES = ["전체", "취업", "유학·교환학생", "워킹홀리데이", "장학·연수"];
const TYPES = ["전체", "프로그램", "지원제도"];



const COMPARE_ROWS = comparisonRows.map(row => ({ label: row.label, render: (p: Program) => row.value(p.comparison) }));

export default function ProgramsPage() {
  const router = useRouter();
  const { items, loading, error, retry } = useCatalog();
  const comparison = useComparison();
  const PROGRAMS = items.map(toLegacyProgram);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("전체");
  const [countryFilter, setCountryFilter] = useState("전체");
  const [purposeFilter, setPurposeFilter] = useState("전체");
  const [restored, setRestored] = useState(false);
  const compareIds = comparison.items.map(item => item.id);
  const setCompareIds = (ids: string[]) => {
    if (ids.length === 0) comparison.clear();
  };

  // 자세히 보기 후 뒤로가기 시 필터 복원
  useEffect(() => {
    // Read browser state after hydration without synchronous effect updates.
    const timer = window.setTimeout(() => {
    try {
      const saved = sessionStorage.getItem("programs-filters");
      if (saved) {
        const f = JSON.parse(saved);
        if (f.search !== undefined) setSearch(f.search);
        if (f.typeFilter) setTypeFilter(f.typeFilter);
        if (f.countryFilter) setCountryFilter(f.countryFilter);
        if (f.purposeFilter) setPurposeFilter(f.purposeFilter);
      }
    } catch {}
    setRestored(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (restored) {
      try { sessionStorage.setItem('programs-filters', JSON.stringify({ search, typeFilter, countryFilter, purposeFilter })); } catch { /* Storage may be disabled. */ }
    }
  }, [restored, search, typeFilter, countryFilter, purposeFilter]);

  const filtered = PROGRAMS.filter(p => {
    if (search && !p.name.includes(search) && !p.desc.includes(search)) return false;
    if (typeFilter !== "전체" && p.type !== typeFilter) return false;
    if (countryFilter !== "전체" && !p.destinations.includes(countryFilter)) return false;
    if (purposeFilter !== "전체" && !p.tags.includes(purposeFilter)) return false;
    return true;
  });

  const comparePrograms = PROGRAMS.filter(p => compareIds.includes(p.id));

  function toggleCompare(id: string) {
    const item = items.find(item => item.id === id);
    if (item) comparison.toggle(toCompared(item));
  }

  const chipStyle = (active: boolean) => ({
    display: "flex", alignItems: "center", gap: 5,
    padding: "6px 14px", borderRadius: 20, fontSize: "0.82rem",
    border: `1px solid ${active ? "var(--ink)" : "var(--ln)"}`,
    background: active ? "var(--ink)" : "#fff",
    color: active ? "#fff" : "var(--ink)",
    cursor: "pointer", fontWeight: active ? 600 : 400,
  } as React.CSSProperties);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      <Header rightLabel="해외 활동 탐색" />

      <div style={{ display: "flex", flex: 1, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px" }}>
        <Sidebar />

        <main style={{ flex: 1, padding: "24px 32px", minWidth: 0 }}>
          {/* 헤더 */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: "0.72rem", letterSpacing: "0.14em", color: "var(--ac)", fontWeight: 600, marginBottom: 10 }}>
              ● EXPLORE YOUR POSSIBILITIES
            </div>
            <h2 style={{ margin: "0 0 6px", fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.04em" }}>
              프로그램·지원제도 찾기
            </h2>
            <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--mu)" }}>
              관심 있는 국가와 목적에 맞는 해외 활동 경로와 지원을 찾아보세요.
            </p>
          </div>

          {/* 필터 카드 */}
          <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "20px 24px", marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, border: "1px solid var(--ln)", borderRadius: 10, padding: "10px 14px", marginBottom: 16 }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.8">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
              <input aria-label="프로그램 검색" value={search} onChange={e => setSearch(e.target.value)} placeholder="이름이나 키워드로 검색"
                style={{ flex: 1, border: "none", outline: "none", fontSize: "0.88rem", background: "transparent" }} />
            </div>

            <div style={{ display: "flex", gap: 8, marginBottom: 14, alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", gap: 6 }}>
                {TYPES.map(t => <button key={t} onClick={() => setTypeFilter(t)} style={chipStyle(typeFilter === t)}>{t}</button>)}
              </div>
              <button onClick={() => { setTypeFilter("전체"); setCountryFilter("전체"); setPurposeFilter("전체"); setSearch(""); comparison.clear(); }}
                style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", fontSize: "0.8rem", color: "var(--mu)", cursor: "pointer" }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
                </svg>
                필터 초기화
              </button>
            </div>

            <div style={{ fontSize: "0.78rem", color: "var(--mu)", marginBottom: 14 }}>
              <strong>프로그램</strong>은 해외 활동을 위한 경로, <strong>지원제도</strong>는 교육·비용·취업 연계 지원이에요.
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: "0.78rem", color: "var(--mu)", width: 24, flexShrink: 0 }}>국가</span>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {COUNTRIES.map(c => (
                  <button key={c} onClick={() => setCountryFilter(c)} style={chipStyle(countryFilter === c)}>
                    {c !== "전체" && <FlagSvg country={c} size={18} />}{c}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: "0.78rem", color: "var(--mu)", width: 24, flexShrink: 0 }}>목적</span>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {PURPOSES.map(p => <button key={p} onClick={() => setPurposeFilter(p)} style={chipStyle(purposeFilter === p)}>{p}</button>)}
              </div>
            </div>
          </div>

          {loading && <p role="status">DB 자료를 불러오는 중…</p>}
          {error && <div role="alert" style={{ marginBottom: 16 }}>
            {error} <button onClick={retry}>다시 불러오기</button>
          </div>}
          {!loading && !error && filtered.length === 0 &&
            <p role="status">검색 결과가 없습니다.</p>}

          {/* 결과 카운트 */}
          <div role="status" aria-label={`검색 결과 ${filtered.length}개`} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <span style={{ fontSize: "0.85rem", color: "var(--ink)" }}>
              총 <strong>{filtered.length}개</strong>{" "}
              <span style={{ color: "var(--mu)", fontSize: "0.8rem" }}>
                프로그램 {filtered.filter(p => p.type === "프로그램").length} · 지원제도 {filtered.filter(p => p.type === "지원제도").length}
              </span>
            </span>
            {compareIds.length > 0 && (
              <span style={{ fontSize: "0.8rem", color: "var(--ac)", fontWeight: 600 }}>
                {compareIds.length}개 선택됨 {compareIds.length >= 2 ? "· 아래에서 비교 중" : "· 1개 더 선택하면 비교"}
              </span>
            )}
          </div>

          {/* 비교표 — 필터 아래, 리스트 위 */}
          {comparePrograms.length >= 2 && (
            <div style={{ marginBottom: 20, background: "#fff", border: "1.5px solid var(--ac)", borderRadius: 16, overflow: "hidden" }}>
              <div style={{ padding: "14px 24px", borderBottom: "1px solid var(--ln)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#f7f9ff" }}>
                <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--ink)", display: "flex", alignItems: "center", gap: 8 }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--ac)" strokeWidth="2">
                    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
                  </svg>
                  비교표
                  <span style={{ fontSize: "0.8rem", fontWeight: 400, color: "var(--mu)" }}>{comparePrograms.length}개 선택됨</span>
                </div>
                <button onClick={() => setCompareIds([])} style={{ background: "none", border: "none", fontSize: "0.8rem", color: "var(--mu)", cursor: "pointer" }}>전체 해제</button>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                  <thead>
                    <tr style={{ background: "#f7f8fa" }}>
                      <th style={{ padding: "12px 20px", textAlign: "left", fontWeight: 600, color: "var(--mu)", fontSize: "0.78rem", width: 100 }}>항목</th>
                      {comparePrograms.map(p => (
                        <th key={p.id} style={{ padding: "12px 20px", textAlign: "left", fontWeight: 700, color: "var(--ink)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            {p.country && <FlagSvg country={p.country} size={18} />}{p.name}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {COMPARE_ROWS.map((row, ri) => (
                      <tr key={ri} style={{ borderTop: "1px solid var(--ln)", background: ri % 2 === 0 ? "#fff" : "#fafbfc" }}>
                        <td style={{ padding: "12px 20px", fontWeight: 600, color: "var(--mu)", fontSize: "0.78rem", whiteSpace: "nowrap" }}>{row.label}</td>
                        {comparePrograms.map(p => <td key={p.id} style={{ padding: "12px 20px", color: "var(--ink)", lineHeight: 1.5 }}>{row.render(p)}</td>)}
                      </tr>
                    ))}
                    <tr style={{ borderTop: "1px solid var(--ln)" }}>
                      <td style={{ padding: "12px 20px", fontWeight: 600, color: "var(--mu)", fontSize: "0.78rem" }}>공식 사이트</td>
                      {comparePrograms.map(p => (
                        <td key={p.id} style={{ padding: "12px 20px" }}>
                          <a href={p.officialUrl} target="_blank" rel="noopener noreferrer"
                            style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "0.82rem", color: "var(--ac)", textDecoration: "none", fontWeight: 500 }}>
                            바로가기 <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 7h10v10M7 17L17 7"/></svg>
                          </a>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 프로그램 목록 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filtered.map(p => {
              const isChecked = compareIds.includes(p.id);
              return (
                <div key={p.id} style={{
                  background: "#fff",
                  border: `1px solid ${isChecked ? "var(--ac)" : "var(--ln)"}`,
                  borderRadius: 14, padding: "18px 20px",
                  display: "flex", alignItems: "center", gap: 16,
                  transition: "border-color 0.15s",
                }}>
                  {/* 국기 */}
                  <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--tn)", display: "grid", placeItems: "center", flexShrink: 0, overflow: "hidden" }}>
                    {p.country ? <FlagSvg country={p.country} size={26} /> : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.6">
                        <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>
                      </svg>
                    )}
                  </div>

                  {/* 내용 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", gap: 6, marginBottom: 6, flexWrap: "wrap" }}>
                      <span style={{ fontSize: "0.72rem", fontWeight: 600, padding: "2px 8px", borderRadius: 6, background: "var(--tn)", color: "var(--ac)" }}>{p.type}</span>
                      {p.tags.map(t => <span key={t} style={{ fontSize: "0.72rem", color: "var(--mu)", padding: "2px 8px", borderRadius: 6, background: "#f0f1f5" }}>{t}</span>)}
                    </div>
                    <div style={{ fontWeight: 700, fontSize: "0.95rem", marginBottom: 4 }}>{p.name}</div>
                    <div style={{ fontSize: "0.82rem", color: "#555", marginBottom: 4 }}>{p.desc}</div>
                    <div style={{ fontSize: "0.78rem", color: "var(--mu)" }}>{p.sub}</div>
                  </div>

                  {/* 버튼 영역 */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0, alignItems: "flex-end" }}>
                    {/* 비교하기 체크박스 */}
                    <label style={{ position: 'relative', display: "flex", alignItems: "center", gap: 6, cursor: "pointer", userSelect: "none" }}>
                      <input type="checkbox" aria-label={`${p.name} 비교`} checked={isChecked} onChange={() => toggleCompare(p.id)} style={{ position: 'absolute', opacity: 0, width: 18, height: 18, margin: 0 }} />
                      <div style={{
                        width: 18, height: 18, borderRadius: 5,
                        border: `1.5px solid ${isChecked ? "var(--ac)" : "#d0d3de"}`,
                        background: isChecked ? "var(--ac)" : "#fff",
                        display: "grid", placeItems: "center", cursor: "pointer", flexShrink: 0, transition: "all 0.15s",
                      }}>
                        {isChecked && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>}
                      </div>
                      <span style={{ fontSize: "0.8rem", color: isChecked ? "var(--ac)" : "var(--mu)", fontWeight: isChecked ? 600 : 400 }}>비교하기</span>
                    </label>

                    {/* 자세히 보기 버튼 */}
                    <ProgramActions item={p.comparison} showDetails={false} />
                    <button
                      onClick={() => {
                        try { sessionStorage.setItem("programs-filters", JSON.stringify({ search, typeFilter, countryFilter, purposeFilter })); } catch {}
                        router.push(`/programs/${encodeURIComponent(p.id)}`);
                      }}
                      style={{
                        border: "1px solid var(--ln)", background: "#fff", borderRadius: 10, padding: "8px 14px",
                        fontSize: "0.82rem", display: "flex", alignItems: "center", gap: 4,
                        color: "var(--ink)", fontWeight: 500, cursor: "pointer",
                      }}
                    >
                      자세히 보기
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M5 12h14M12 5l7 7-7 7"/>
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ fontSize: "0.78rem", color: "#ccc", textAlign: "center", marginTop: 24, paddingBottom: 32 }}>
            DB에 저장된 자료입니다. 실제 자격요건과 현재 신청 가능 여부는 공식 기관에서 확인해 주세요.
          </div>
        </main>
      </div>

      <footer style={{ display: "flex", justifyContent: "space-between", maxWidth: 1040, margin: "0 auto", width: "100%", padding: "20px 20px", fontSize: "0.78rem", color: "#ccc" }}>
        <span>Global-In.</span>
        <span>해외에서의 다음 시작을 함께.</span>
      </footer>
    </div>
  );
}
