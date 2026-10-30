"use client";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";

export default function PreparationPage() {
  const router = useRouter();

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      <Header rightLabel="플랜" />

      <div style={{ display: "flex", flex: 1, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px" }}>
        <Sidebar />

        <main style={{ flex: 1, padding: "24px 32px", minWidth: 0 }}>
          {/* 헤더 */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: "0.72rem", letterSpacing: "0.14em", color: "var(--ac)", fontWeight: 600, marginBottom: 10 }}>
              ● MY PLAN
            </div>
            <h2 style={{ margin: "0 0 6px", fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.04em" }}>
              플랜
            </h2>
            <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--mu)" }}>
              선택한 프로그램과 지원제도의 준비 계획을 한눈에 확인해 보세요.
            </p>
          </div>

          {/* 빈 상태 카드 */}
          <div style={{
            background: "#fff", border: "1px solid var(--ln)", borderRadius: 16,
            padding: "60px 40px", display: "flex", flexDirection: "column",
            alignItems: "center", textAlign: "center",
          }}>
            <div style={{
              width: 56, height: 56, borderRadius: 16, background: "var(--tn)",
              display: "grid", placeItems: "center", marginBottom: 20,
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.5">
                <path d="M22 13V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12c0 1.1.9 2 2 2h8"/>
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
                <path d="M16 19h6M19 16v6"/>
              </svg>
            </div>

            <h3 style={{ margin: "0 0 8px", fontSize: "1.05rem", fontWeight: 700 }}>
              아직 준비 중인 항목이 없어요.
            </h3>
            <p style={{ margin: "0 0 28px", fontSize: "0.88rem", color: "var(--mu)", lineHeight: 1.6 }}>
              프로그램을 찾아보거나 AI 상담한 뒤 준비 계획에 추가해 보세요.
            </p>

            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={() => router.push("/programs")}
                style={{
                  background: "var(--ink)", color: "#fff", border: "none",
                  borderRadius: 10, padding: "11px 22px", fontSize: "0.88rem",
                  fontWeight: 600, display: "flex", alignItems: "center", gap: 8,
                  cursor: "pointer",
                }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20M16.2 7.8l-2.1 6.3-6.3 2.1 2.1-6.3z"/>
                </svg>
                프로그램 찾아보기
              </button>

              <button
                onClick={() => router.push("/chat")}
                style={{
                  background: "#fff", color: "var(--ink)", border: "1px solid var(--ln)",
                  borderRadius: 10, padding: "11px 22px", fontSize: "0.88rem",
                  fontWeight: 500, display: "flex", alignItems: "center", gap: 8,
                  cursor: "pointer",
                }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--ac)" strokeWidth="1.8">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                AI 상담하기
              </button>
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