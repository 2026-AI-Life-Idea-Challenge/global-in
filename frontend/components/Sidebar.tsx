"use client";
import { useRouter, usePathname } from "next/navigation";

interface SidebarProps {
  sessions?: { id: string; title: string }[];
  currentSessionId?: string;
  onNewChat?: () => void;
}

const NAV = [
  {
    label: "AI 상담", href: "/chat",
    icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  },
  {
    label: "프로그램·지원제도 찾기", href: "/programs",
    icon: "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20M16.2 7.8l-2.1 6.3-6.3 2.1 2.1-6.3z",
  },
  {
    label: "내 준비", href: "/preparation",
    icon: "M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2m-6 9l2 2 4-4",
  },
];

export default function Sidebar({ sessions = [], currentSessionId, onNewChat }: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const isChat = pathname?.startsWith("/chat");

  return (
    <aside style={{
      width: 210, flexShrink: 0, display: "flex", flexDirection: "column",
      borderRight: "1px solid var(--ln)", background: "var(--bg)",
      minHeight: "calc(100vh - 90px)",
    }}>

      {/* 새 채팅 버튼 (chat일 때만) */}
      {isChat && (
        <div style={{ padding: "20px 16px 14px" }}>
          <button
            onClick={onNewChat}
            style={{
              width: "100%", border: "1px solid var(--ln)", background: "#fff",
              borderRadius: 10, padding: "10px 0", fontSize: "0.88rem",
              fontWeight: 600, display: "flex", alignItems: "center",
              justifyContent: "center", gap: 6, cursor: "pointer", color: "var(--ink)",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            새 채팅
          </button>
        </div>
      )}

      {/* 둘러보기 */}
      <div style={{ padding: isChat ? "0 16px 14px" : "20px 16px 14px" }}>
        <button
          onClick={() => router.push("/")}
          style={{
            width: "100%", textAlign: "left", background: "none", border: "none",
            padding: "6px 8px", fontSize: "0.82rem", color: "var(--mu)",
            borderRadius: 8, display: "flex", alignItems: "center", gap: 6,
            cursor: "pointer",
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          </svg>
          둘러보기
        </button>
      </div>

      {/* 네비게이션 */}
      <nav style={{ padding: "0 16px 14px", borderBottom: "1px solid var(--ln)" }}>
        {NAV.map(item => {
          const active = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <button
              key={item.href}
              onClick={() => router.push(item.href)}
              style={{
                width: "100%", textAlign: "left",
                background: active ? "var(--tn)" : "none",
                border: "none", padding: "9px 10px", fontSize: "0.86rem",
                color: active ? "var(--ac)" : "#3b3f4d", borderRadius: 9,
                display: "flex", alignItems: "center", gap: 9,
                fontWeight: active ? 600 : 400, marginBottom: 2, cursor: "pointer",
              }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                <path d={item.icon}/>
              </svg>
              <span style={{ lineHeight: 1.3 }}>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* 채팅 목록 */}
      {isChat && (
        <div style={{ flex: 1, overflowY: "auto", padding: "14px 16px" }}>
          {sessions.length > 0 && (
            <div style={{
              fontSize: "0.72rem", color: "var(--mu)", fontWeight: 600,
              letterSpacing: "0.06em", marginBottom: 8, paddingLeft: 2,
            }}>
              채팅 목록
            </div>
          )}
          {sessions.map(s => (
            <button
              key={s.id}
              onClick={() => router.push(`/chat/${s.id}`)}
              style={{
                width: "100%", textAlign: "left",
                background: s.id === currentSessionId ? "var(--tn)" : "none",
                border: "none", padding: "8px 10px", fontSize: "0.83rem",
                borderRadius: 8, cursor: "pointer", color: "var(--ink)",
                display: "flex", alignItems: "center", gap: 8, marginBottom: 2,
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--ac)" strokeWidth="1.7">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {s.title}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* 내 프로필 */}
      <div style={{ marginTop: "auto", padding: "16px", borderTop: "1px solid var(--ln)" }}>
        <button
          onClick={() => router.push("/profile")}
          style={{
            background: "none", border: "none", display: "flex", alignItems: "center",
            gap: 8, fontSize: "0.86rem", color: "#3b3f4d", cursor: "pointer", padding: "6px 4px",
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"/>
          </svg>
          내 프로필
        </button>
      </div>
    </aside>
  );
}