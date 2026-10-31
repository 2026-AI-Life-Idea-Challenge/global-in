"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

const COUNTRY_CODE: Record<string, string> = {
  일본: "jp",
  독일: "de",
  캐나다: "ca",
  호주: "au",
  미국: "us",
};

const CARDS = [
  
  {
    icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M4 21a8 8 0 0 1 16 0",
    title: "AI와 함께 찾는 나만의 해외 기회",
    desc: "내 프로필을 분석해 맞춤 프로그램과 정보, 준비 체크리스트 제공",
    href: "/chat",
  },
  {
    icon: "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20M16.2 7.8l-2.1 6.3-6.3 2.1 2.1-6.3z",
    title: "나에게 맞는 프로그램 탐색",
    desc: "해외 프로그램의 조건과 혜택을 살펴보고 한눈에 비교",
    href: "/programs",
  },
  {
    icon: "M3 17l2 2 4-4M3 7l2 2 4-4M13 6h8M13 12h8M13 18h8",
    title: "선택한 프로그램별 준비 플랜",
    desc: "프로그램별 준비 일정과 체크리스트를 확인하고 진행 상황 관리",
    href: "/preparation",
  },
];

const cardMargins = ["0 0 6px 0", "0 0 6px 0", "0 0 0 0"];

const FLAG_POSITIONS = [
  { country: "일본",   style: { left: "21%", top: 190 } },
  { country: "미국",   style: { right: "21%", top: 190 } },
  { country: "호주",   style: { left: "8%", top: 420 } },
  { country: "독일",   style: { right: "7%", top: 470 } },
  { country: "캐나다", style: { left: "22%", top: 690 } },
];

const HOW_IT_WORKS = [
  ["기본 정보 알려주기", "국적과 나이 등 간단한 정보를 입력해요. 관심 국가는 미정이어도 돼요."],
  ["대화로 조건 알아보기", "원하는 활동을 이야기하고, 상담에 필요한 질문에 답해요."],
  ["프로그램 비교하기", "관련 프로그램의 차이와 내 조건 검토 결과를 공식 출처와 함께 확인해요."],
  ["준비할 일 확인하기", "서류와 절차, 관련 지원제도를 살펴보고 체크리스트로 준비해요."],
];

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        const el = e.target as HTMLElement;
        if (e.isIntersecting) {
          el.style.opacity = "1";
          el.style.transform = "translateY(0)";
        } else {
          el.style.opacity = "0";
          el.style.transform = "translateY(30px)";
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll(".scroll-up").forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin-slow {
          to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        @keyframes markIn {
          from { background-color: transparent; }
          to   { background-color: #dcdce0; }
        }
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(123,135,214,0.5); }
          50%       { box-shadow: 0 0 0 12px rgba(123,135,214,0); }
        }
        .scroll-up {
          opacity: 0;
          transform: translateY(30px);
          transition: opacity 0.6s ease, transform 0.6s ease;
        }
      `}</style>


      {/* 네비 - 우측 상단 고정 */}
      <div style={{
        position: "fixed", top: 0, right: 0,
        padding: "22px 28px",
        display: "flex", gap: 28,
        color: "#3b3f4d", fontSize: "0.9rem",
        zIndex: 10,
      }}>
        <a style={{ cursor: "pointer" }}>서비스 소개</a>
        <a style={{ cursor: "pointer" }}>이용 방법</a>
      </div>

      {/* Hero */}
      <section style={{ position: "relative", height: 900, overflow: "hidden", textAlign: "center" }}>
        {/* 동심원 */}
        {[580, 900, 1320].map((w) => (
          <div key={w} style={{
            position: "absolute", left: "50%", top: 400,
            width: w, height: w, border: "1px solid #e8eaf3", borderRadius: "50%",
            transform: "translate(-50%, -50%)",
          }} />
        ))}

        {/* 국가 플래그 */}
        {FLAG_POSITIONS.map(({ country, style }) => (
          <div
            key={country}
            style={{
              position: "absolute", display: "flex", flexDirection: "column",
              alignItems: "center", gap: 6, fontSize: "0.78rem", color: "var(--mu)",
              cursor: "default", ...style,
            }}
          >
            <div style={{ width: 52, height: 52, borderRadius: "50%", overflow: "hidden", boxShadow: "0 4px 18px rgba(30,35,70,.1)", border: "1px solid var(--ln)" }}>
              {country === "일본" ? (
                <svg viewBox="0 0 100 100" style={{ width: "100%", height: "100%" }}>
                  <circle cx="50" cy="50" r="50" fill="#fff"/>
                  <circle cx="50" cy="50" r="22" fill="#bc2a3a"/>
                </svg>
              ) : (
                <img
                  src={`/flags/${COUNTRY_CODE[country]}.png`}
                  alt={country}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              )}
            </div>
            {country}
          </div>
        ))}

        {/* 헤드라인 */}
        <div style={{ position: "absolute", left: 0, right: 0, top: 170 }}>
          <div style={{ fontSize: "0.72rem", letterSpacing: "0.16em", color: "var(--mu)", fontWeight: 600, marginBottom: 0, animation: "fadeUp 0.6s ease both" }}>
            <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--ac)", marginRight: 8, verticalAlign: "middle" }} />
            YOUR NEXT CHAPTER
          </div>
          <h1 style={{ fontSize: "clamp(2.2rem,5vw,3.5rem)", lineHeight: 1.2, letterSpacing: "-0.05em", fontWeight: 800, margin: "20px 0", animation: "fadeUp 0.6s ease 0.15s both" }}>
            가능성을 찾고,<br />
            계획으로 완성하다.
          </h1>
          <p style={{ color: "var(--mu)", fontSize: "1.05rem", lineHeight: 2, margin: "0 0 32px", animation: "fadeUp 0.6s ease 0.3s both" }}>
            나에게 맞는 비자·체류 프로그램을 비교하고,<br />
            필요한 서류와 준비할 일을 함께 알아보세요.
          </p>

          <button
            onClick={() => router.push("/chat")}
            style={{
              border: "none",
              background: "linear-gradient(135deg, #5a67b8, #7b87d6)",
              color: "#fff",
              borderRadius: 12,
              padding: "20px 40px",
              fontWeight: 700,
              display: "inline-flex",
              gap: 8,
              alignItems: "center",
              fontSize: "1.05rem",
              animation: "fadeUp 0.6s ease 0.45s both, pulse 2s ease-in-out 1.5s infinite",
              transition: "transform 0.2s, filter 0.2s, box-shadow 0.2s",
              cursor: "pointer",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = "translateY(-3px)";
              e.currentTarget.style.filter = "brightness(1.1)";
              e.currentTarget.style.animation = "none";
              e.currentTarget.style.boxShadow = "0 12px 32px rgba(123,135,214,0.5)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.filter = "brightness(1)";
              e.currentTarget.style.animation = "pulse 2s ease-in-out infinite";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            AI 상담 시작하기
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M7 7h10v10M7 17L17 7"/></svg>
          </button>
        </div>

        {/* 피처 카드 */}
        <div style={{ position: "absolute", left: 0, right: 0, margin: "0 auto", top: 600, width: 460, filter: "drop-shadow(0 20px 40px rgba(123,135,214,.2))", animation: "fadeUp 0.6s ease 0.6s both" }}>
          {CARDS.map((card, i) => (
            <button
              key={card.title}
              onClick={() => router.push(card.href)}
              style={{
                background: "#fff", border: "1px solid var(--ln)", borderRadius: 14,
                padding: "16px 20px", display: "flex", gap: 14, alignItems: "center",
                textAlign: "left", width: "100%", margin: cardMargins[i],
                transition: "transform 0.2s, box-shadow 0.2s", cursor: "pointer",
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.09)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "none"; }}
            >
              <span style={{ width: 38, height: 38, borderRadius: 10, background: "var(--tn)", display: "grid", placeItems: "center", color: "#5a67b8", flexShrink: 0 }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d={card.icon} /></svg>
              </span>
              <div>
                <b style={{ display: "block", fontSize: "0.95rem" }}>{card.title}</b>
                <span style={{ color: "var(--mu)", fontSize: "0.78rem" }}>{card.desc}</span>
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* Explore */}
      <section className="scroll-up" style={{ textAlign: "center", padding: "56px 20px", borderTop: "1px solid var(--ln)" }}>
        <div style={{ fontSize: "0.72rem", letterSpacing: "0.16em", color: "var(--mu)", fontWeight: 600 }}>
          <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--ac)", marginRight: 8, verticalAlign: "middle" }} />
          EXPLORE YOUR POSSIBILITIES
        </div>
        <h2 style={{ fontSize: "2rem", letterSpacing: "-0.04em", margin: "12px 0" }}>어디로 갈지 고민하는 순간부터.</h2>
        <p style={{ color: "var(--mu)", lineHeight: 1.9 }}>
          국가나 목적을 아직 정하지 못했어도 괜찮아요.<br />
          일본·호주·미국·독일·캐나다에서의 시작을 함께 알아봐요.
        </p>
      </section>

      {/* How It Works */}
      <section style={{ background: "#f5f6f8", padding: "72px 20px", textAlign: "center" }}>
        <div className="scroll-up" style={{ fontSize: "0.72rem", letterSpacing: "0.16em", color: "var(--mu)", fontWeight: 600 }}>
          <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--ac)", marginRight: 8, verticalAlign: "middle" }} />
          HOW IT WORKS
        </div>
        <h2 className="scroll-up" style={{ fontSize: "2rem", letterSpacing: "-0.04em", margin: "12px 0 48px", transitionDelay: "0.1s" }}>궁금한 마음을, 준비하는 일상으로.</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 28, textAlign: "left", maxWidth: 960, margin: "0 auto" }}>
          {HOW_IT_WORKS.map(([title, desc], i) => (
            <div key={title} className="scroll-up" style={{ transitionDelay: `${0.15 + i * 0.1}s` }}>
              <small style={{ color: "#6672c4", fontWeight: 600 }}>0{i + 1}</small>
              <b style={{ display: "block", margin: "8px 0", fontSize: "1.05rem" }}>{title}</b>
              <span style={{ color: "var(--mu)", fontSize: "0.9rem" }}>{desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <div className="scroll-up" style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid var(--ln)", padding: "28px 20px", color: "var(--mu)", fontSize: "0.8rem", maxWidth: 1040, margin: "0 auto" }}>
        <span>Global-In.</span>
        <span>해외에서의 다음 시작을 함께.</span>
      </div>
      <p style={{ textAlign: "center", fontSize: "0.7rem", color: "var(--mu)", padding: "8px 0 16px" }}>
        Icons by <a href="https://www.flaticon.com/" title="Flaticon" style={{ color: "var(--mu)" }}>Flaticon</a>
      </p>
    </div>
  );
}
