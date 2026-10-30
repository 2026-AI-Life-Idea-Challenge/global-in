"use client";
import { useParams, useRouter } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";

const FLAGS: Record<string, string> = {
  독일: '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  일본: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  호주: '<rect width="30" height="20" fill="#00247d"/><path d="M0 0l14 9M14 0L0 9" stroke="#fff" strokeWidth="1.6"/><path d="M7 0v9M0 4.5h14" stroke="#fff" strokeWidth="3"/><path d="M7 0v9M0 4.5h14" stroke="#cf142b" strokeWidth="1.6"/>',
  미국: '<rect width="30" height="20" fill="#fff"/><rect y="0" width="30" height="1.55" fill="#b22234"/><rect y="3.1" width="30" height="1.55" fill="#b22234"/><rect y="6.2" width="30" height="1.55" fill="#b22234"/><rect y="9.3" width="30" height="1.55" fill="#b22234"/><rect y="12.4" width="30" height="1.55" fill="#b22234"/><rect y="15.5" width="30" height="1.55" fill="#b22234"/><rect y="18.6" width="30" height="1.55" fill="#b22234"/><rect width="13" height="10.8" fill="#3c3b6e"/>',
  캐나다: '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/><path d="M15 4l1.3 3 2-1-.6 4 1.7-.4-.4 1.8 1.5 1-3.5 2.4.2 2.2h-4.4l.2-2.2-3.5-2.4 1.5-1-.4-1.8 1.7.4-.6-4 2 1z" fill="#d52b1e"/>',
};

const PROGRAMS = [
  { id: 1, type: "프로그램", country: "일본", tags: ["일본", "취업"], name: "기술·인문지식·국제업무", desc: "전문 지식과 기술을 활용해 일본에서 일하는 취업 경로.", sub: "담당 직무와 학력·경력 등 요건 확인", officialUrl: "https://www.moj.go.jp/isa/applications/status/gijinkoku.html",
    details: "일본 법무성이 지정하는 재류자격 중 하나로, 전문직 종사자를 대상으로 합니다. 법률·회계·IT·외국어 교육 등 넓은 분야에서 활용되며, 대학 졸업 또는 10년 이상 실무 경험이 필요합니다." },
  { id: 2, type: "지원제도", country: null, tags: ["여러 국가", "과정별 상이", "취업"], name: "K-Move스쿨", desc: "해외취업에 필요한 어학·직무 연수와 취업 연계를 지원.", sub: "맞춤형 교육·연수비·일부 취업 지원", officialUrl: "https://worldjob.or.kr/kmove/kmoveSchool.do",
    details: "한국산업인력공단이 운영하는 해외취업 지원 사업으로, 국가·직종별 맞춤형 교육과 함께 취업 연계까지 지원합니다. 훈련비 및 체재비 일부 지원이 가능하며, 매년 모집 공고를 통해 선발합니다." },
  { id: 3, type: "프로그램", country: "독일", tags: ["독일", "취업"], name: "기회카드 (Chancenkarte)", desc: "독일에서 일자리를 찾기 위한 체류 경로.", sub: "자격 인정 또는 점수 경로·언어·생계 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/opportunity-card",
    details: "2024년 도입된 독일의 새로운 이민 제도로, 숙련 인력이 독일 현지에서 직접 구직 활동을 할 수 있도록 최대 1년간 체류를 허가합니다. 점수 기반 평가(독일어, 경력, 연령, 학력 등)를 통해 선발합니다." },
  { id: 4, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워킹홀리데이 비자 (417)", desc: "호주에서 여행하며 단기 근로를 병행하는 경로.", sub: "여권 국가·연령·이전 참여 이력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417",
    details: "만 18~30세(일부 국가 35세)의 청년을 대상으로 호주 체류와 취업을 동시에 허용하는 비자입니다. 한국 국적자는 최대 3년까지 연장이 가능하며, 지역 근무 조건 충족 시 2·3차 비자를 받을 수 있습니다." },
  { id: 5, type: "프로그램", country: "미국", tags: ["미국", "유학·교환학생"], name: "학생 비자 (F-1)", desc: "미국의 대학 등 교육기관에서 학업을 위한 경로.", sub: "교육기관·학업 과정·I-20 등 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
    details: "미국 SEVP 승인 학교에서 정규 과정 수학을 위한 비자로, 학교로부터 I-20 양식을 받은 뒤 미국 대사관에서 인터뷰를 통해 발급받습니다. 졸업 후 OPT를 통해 최대 3년간 미국 내 취업이 가능합니다." },
  { id: 6, type: "프로그램", country: "캐나다", tags: ["캐나다", "취업"], name: "연방 전문인력 프로그램 (FSW)", desc: "해외 숙련 경력을 바탕으로 검토하는 캐나다 영주권 경로.", sub: "숙련 경력·공인어학·학력 등 요건 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/federal-skilled-workers.html",
    details: "캐나다 Express Entry 시스템을 통해 영주권을 신청하는 대표적인 경로입니다. 1년 이상 숙련 직종 경력, 공인어학성적(IELTS 등), 학력 평가가 필요하며 CRS 점수 기반으로 초청장(ITA)을 발급합니다." },
  { id: 7, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "해외취업정착지원금", desc: "해외취업 후 초기 정착과 경력 개발을 돕는 지원.", sub: "해외취업자의 초기 정착을 위한 지원금", officialUrl: "https://worldjob.or.kr/",
    details: "고용노동부와 한국산업인력공단이 지원하는 사업으로, 해외에 취업한 청년에게 초기 정착금을 지급합니다. 지원 요건(연령·소득 등)과 지원금액은 매년 변경될 수 있으므로 월드잡플러스 공식 사이트에서 최신 공고를 확인하세요." },
];

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
  const id = Number(params?.id);
  const program = PROGRAMS.find(p => p.id === id);

  if (!program) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
        <Header rightLabel="프로그램 상세" />
        <div style={{ display: "flex", flex: 1, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px" }}>
          <Sidebar />
          <main style={{ flex: 1, padding: "24px 32px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ textAlign: "center" }}>
              <p style={{ color: "var(--mu)", marginBottom: 16 }}>프로그램을 찾을 수 없어요.</p>
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

          <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 16, alignItems: "start" }}>
            {/* 왼쪽: 상세 설명 + 대상 조건 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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
                  <span style={{ fontSize: "0.88rem", color: "var(--ink)", lineHeight: 1.7 }}>{program.sub}</span>
                </div>
                <p style={{ margin: "12px 0 0", fontSize: "0.8rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  자격 조건과 신청 요건은 변경될 수 있으니, 공식 사이트에서 최신 정보를 꼭 확인하세요.
                </p>
              </div>
            </div>

            {/* 오른쪽: 액션 카드 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* 공식 사이트 */}
              <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "20px 22px" }}>
                <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 공식 사이트</div>
                <p style={{ margin: "0 0 14px", fontSize: "0.82rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  신청 방법, 자격 요건, 최신 공지를 공식 사이트에서 확인하세요.
                </p>
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
                  화면 시안을 위한 예시 정보예요. 실제 자격 요건과 신청 절차는 공식 사이트에서 확인해 주세요.
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
    </div>
  );
}
