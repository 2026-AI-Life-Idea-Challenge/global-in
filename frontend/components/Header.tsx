"use client";
import Link from 'next/link';

interface HeaderProps {
  rightLabel?: string;
  showNav?: boolean;
}

export default function Header({ rightLabel, showNav = false }: HeaderProps) {
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
      <nav className="mobile-navigation" aria-label="모바일 메뉴">
        <Link href="/chat">상담</Link><Link href="/programs">프로그램</Link><Link href="/compare">비교</Link><Link href="/preparation">플랜</Link><Link href="/profile">프로필</Link>
      </nav>
    </div>
  );
}
