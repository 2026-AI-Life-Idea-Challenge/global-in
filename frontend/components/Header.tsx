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
        padding: "14px 28px",
      }}>
        <div />

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