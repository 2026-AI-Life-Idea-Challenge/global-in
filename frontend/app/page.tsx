"use client";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";

const FL: Record<string, string> = {
  일본: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  독일: '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  캐나다: '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/><path d="M15 4l1.3 3 2-1-.6 4 1.7-.4-.4 1.8 1.5 1-3.5 2.4.2 2.2h-4.4l.2-2.2-3.5-2.4 1.5-1-.4-1.8 1.7.4-.6-4 2 1z" fill="#d52b1e"/>',
  호주: '<rect width="30" height="20" fill="#00247d"/><path d="M0 0l14 9M14 0L0 9" stroke="#fff" strokeWidth="1.6"/><path d="M7 0v9M0 4.5h14" stroke="#fff" strokeWidth="3"/><path d="M7 0v9M0 4.5h14" stroke="#cf142b" strokeWidth="1.6"/>',
  미국: '<rect width="30" height="20" fill="#fff"/><rect y="0" width="30" height="1.55" fill="#b22234"/><rect y="3.1" width="30" height="1.55" fill="#b22234"/><rect y="6.2" width="30" height="1.55" fill="#b22234"/><rect y="9.3" width="30" height="1.55" fill="#b22234"/><rect y="12.4" width="30" height="1.55" fill="#b22234"/><rect y="15.5" width="30" height="1.55" fill="#b22234"/><rect y="18.6" width="30" height="1.55" fill="#b22234"/><rect width="13" height="10.8" fill="#3c3b6e"/>',
};

function FlagCircle({ country, style }: { country: string; style: React.CSSProperties }) {
  return (
    <div style={{ position: "absolute", display: "flex", flexDirection: "column", alignItems: "center", gap: 6, fontSize: "0.78rem", color: "var(--mu)", ...style }}>
      <div style={{ width: 68, height: 68, borderRadius: "50%", background: "#fff", boxShadow: "0 4px 18px rgba(30,35,70,.1)", display: "grid", placeItems: "center", border: "1px solid var(--ln)" }}>
        <svg viewBox="0 0 30 20" style={{ width: 36, height: 24, borderRadius: 2 }} dangerouslySetInnerHTML={{ __html: FL[country] }} />
      </div>
      {country}
    </div>
  );
}

const CARDS = [
  { icon: "M3 17l2 2 4-4M3 7l2 2 4-4M13 6h8M13 12h8M13 18h8", title: "나에게 맞는 프로그램 비교", desc: "관심 있는 프로그램의 차이를 한눈에", href: "/compare" },
  { icon: "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20M16.2 7.8l-2.1 6.3-6.3 2.1 2.1-6.3z", title: "내 조건에 맞는지 확인", desc: "충족한 조건과 더 확인할 조건 정리", href: "/programs" },
  { icon: "M3 17l2 2 4-4M3 7l2 2 4-4M13 6h8M13 12h8M13 18h8", title: "준비할 일을 순서대로", desc: "필요한 서류와 할 일을 체크리스트로", href: "/preparation" },
];

const cardMargins = [
  "0 0 6px 0",
  "0 0 6px 0",
  "0 0 0 0",
];

export default function Home() {
  const router = useRouter();

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <Header showNav />

      {/* Hero */}
      <section style={{ position: "relative", height: 900, overflow: "hidden", textAlign: "center" }}>
        {/* 3 concentric rings */}
        {[580, 900, 1320].map(w => (
          <div key={w} style={{
            position: "absolute", left: "50%", top: 400,
            width: w, height: w, border: "1px solid #e8eaf3", borderRadius: "50%",
            transform: "translate(-50%, -50%)"
          }} />
        ))}

        {/* Country flags */}
        <FlagCircle country="일본" style={{ left: "21%", top: 190 }} />
        <FlagCircle country="미국" style={{ right: "21%", top: 190 }} />
        <FlagCircle country="호주" style={{ left: "8%", top: 420 }} />
        <FlagCircle country="독일" style={{ right: "7%", top: 470 }} />
        <FlagCircle country="캐나다" style={{ left: "22%", top: 690 }} />

        {/* Center headline */}
        <div style={{ position: "absolute", left: 0, right: 0, top: 170 }}>
          <div style={{ fontSize: "0.72rem", letterSpacing: "0.16em", color: "var(--mu)", fontWeight: 600, marginBottom: 0 }}>
            <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--ac)", marginRight: 8, verticalAlign: "middle" }} />
            YOUR NEXT CHAPTER
          </div>
          <h1 style={{ fontSize: "clamp(2.2rem,5vw,3.5rem)", lineHeight: 1.2, letterSpacing: "-0.05em", fontWeight: 800, margin: "20px 0" }}>
            해외에서의 시작,<br />
            내 <mark style={{ background: "#dcdce0", padding: "0 4px" }}>조건에</mark> 맞게.
          </h1>
          <p style={{ color: "var(--mu)", fontSize: "1.05rem", lineHeight: 2, margin: "0 0 32px" }}>
            나에게 맞는 비자·체류 프로그램을 비교하고,<br />
            필요한 서류와 준비할 일을 함께 알아보세요.
          </p>
          <button
            onClick={() => router.push("/chat")}
            style={{ border: "1px solid var(--ink)", background: "var(--ink)", color: "#fff", borderRadius: 12, padding: "18px 34px", fontWeight: 600, display: "inline-flex", gap: 8, alignItems: "center", fontSize: "1rem" }}
          >
            상담 시작하기
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M7 7h10v10M7 17L17 7"/></svg>
          </button>
        </div>

        {/* Staggered feature cards */}
        <div style={{ position: "absolute", left: "50%", top: 600, width: 460, transform: "translateX(-50%)", filter: "drop-shadow(0 20px 40px rgba(123,135,214,.2))" }}>
          {CARDS.map((card, i) => (
            <button
              key={card.title}
              onClick={() => router.push(card.href)}
              style={{
                background: "#fff", border: "1px solid var(--ln)", borderRadius: 14,
                padding: "16px 20px", display: "flex", gap: 14, alignItems: "center",
                textAlign: "left", width: "100%",
                margin: cardMargins[i],  // cardMargins에 bottom 포함시키기
              }}
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
      <section style={{ textAlign: "center", padding: "56px 20px", borderTop: "1px solid var(--ln)" }}>
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
        <div style={{ fontSize: "0.72rem", letterSpacing: "0.16em", color: "var(--mu)", fontWeight: 600 }}>
          <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--ac)", marginRight: 8, verticalAlign: "middle" }} />
          HOW IT WORKS
        </div>
        <h2 style={{ fontSize: "2rem", letterSpacing: "-0.04em", margin: "12px 0 48px" }}>궁금한 마음을, 준비하는 일상으로.</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 28, textAlign: "left", maxWidth: 960, margin: "0 auto" }}>
          {[
            ["기본 정보 알려주기", "국적과 나이 등 간단한 정보를 입력해요. 관심 국가는 미정이어도 돼요."],
            ["대화로 조건 알아보기", "원하는 활동을 이야기하고, 상담에 필요한 질문에 답해요."],
            ["프로그램 비교하기", "관련 프로그램의 차이와 내 조건 검토 결과를 공식 출처와 함께 확인해요."],
            ["준비할 일 확인하기", "서류와 절차, 관련 지원제도를 살펴보고 체크리스트로 준비해요."],
          ].map(([title, desc], i) => (
            <div key={title}>
              <small style={{ color: "#6672c4", fontWeight: 600 }}>0{i + 1}</small>
              <b style={{ display: "block", margin: "8px 0", fontSize: "1.05rem" }}>{title}</b>
              <span style={{ color: "var(--mu)", fontSize: "0.9rem" }}>{desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid var(--ln)", padding: "28px 20px", marginTop: 0, color: "var(--mu)", fontSize: "0.8rem", maxWidth: 1040, margin: "0 auto" }}>
        <span>Global-In.</span>
        <span>해외에서의 다음 시작을 함께.</span>
      </div>
    </div>
  );
}