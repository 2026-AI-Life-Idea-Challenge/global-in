"use client";
import { useRouter } from "next/navigation";

interface HeaderProps {
  rightLabel?: string;
  showNav?: boolean;
}

export default function Header({ rightLabel, showNav = false }: HeaderProps) {
  const router = useRouter();
  return (
    <div style={{ padding: "24px 20px 0", position: "relative", zIndex: 5 }}>
      <div style={{
        maxWidth: 1040, margin: "0 auto",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        background: "#fff", border: "1px solid var(--ln)", borderRadius: 24,
        padding: "14px 28px", boxShadow: "0 8px 24px rgba(30,35,70,.06)",
      }}>
        <button
          onClick={() => router.push("/")}
          style={{
            display: "flex", gap: 10, alignItems: "center",
            fontWeight: 800, fontSize: "1.3rem", letterSpacing: "-0.03em",
            border: 0, background: "none", padding: 0, cursor: "pointer",
          }}
        >
          <img src="/logo/global-in-logo.svg" alt="Global-In" style={{ height: 32 }} />
        </button>

        {showNav ? (
          <div style={{ display: "flex", gap: 28, color: "#3b3f4d", fontSize: "0.9rem" }}>
            <a style={{ cursor: "pointer" }}>서비스 소개</a>
            <a style={{ cursor: "pointer" }}>이용 방법</a>
          </div>
        ) : rightLabel ? (
          <span style={{ fontSize: "0.72rem", letterSpacing: "0.16em", color: "var(--mu)", fontWeight: 600 }}>
            <span style={{
              display: "inline-block", width: 6, height: 6, borderRadius: "50%",
              background: "var(--ac)", marginRight: 8, verticalAlign: "middle",
            }} />
            {rightLabel}
          </span>
        ) : null}
      </div>
    </div>
  );
}