"use client";

import { useState, useRef, useEffect, useLayoutEffect } from "react";
import Sidebar from "@/components/Sidebar";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "일본 취업을 알아보고 싶어요",
  "여러 나라를 비교하고 싶어요",
  "국가와 목적부터 정하고 싶어요",
];

const INITIAL_MESSAGES: Message[] = [
  {
    role: "assistant",
    content:
      "안녕하세요! 궁금한 점을 바로 질문해도 좋고,\n원하는 방향을 함께 찾아봐도 좋아요.\n\n**이번에는 어떤 내용을 알아보고 싶으세요?**",
  },
];

function renderContent(text: string) {
  return text.split("\n").map((line, i, arr) => {
    const parts = line.split(/\*\*(.*?)\*\*/g);

    return (
      <span key={i}>
        {parts.map((part, j) =>
          j % 2 === 1 ? <strong key={j}>{part}</strong> : part,
        )}
        {i < arr.length - 1 && <br />}
      </span>
    );
  });
}

export default function ChatPage() {
  const [sessions] = useState([{ id: "new", title: "새 채팅" }]);
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const didMountRef = useRef(false);

  // 상담 페이지에서도 다른 탭과 동일하게 세로 스크롤바 공간을 확보합니다.
  // 페이지 전체는 스크롤되지 않지만, 스크롤바 공간을 예약해 탭 전환 시 좌우 밀림을 방지합니다.
  useLayoutEffect(() => {
    const html = document.documentElement;
    const previousScrollBehavior = html.style.scrollBehavior;
    html.style.scrollbarGutter = "stable";
    html.style.scrollBehavior = "auto";

    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    html.scrollTop = 0;
    document.body.scrollTop = 0;

    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = 0;
    }

    return () => {
      html.style.scrollBehavior = previousScrollBehavior;
      // scrollbar-gutter는 전역 레이아웃에서 계속 유지해도 안전한 설정이며,
      // 페이지 이동 시 원래 설정으로 돌리려면 아래 줄의 주석을 해제하세요.
      // html.style.scrollbarGutter = "";
    };
  }, []);

  // 첫 렌더에서는 자동으로 아래로 이동하지 않습니다.
  // 이후 메시지/로딩 상태가 바뀔 때만 메시지 영역 내부를 아래로 스크롤합니다.
  useEffect(() => {
    if (!didMountRef.current) {
      didMountRef.current = true;
      return;
    }

    if (messages.length <= 1) {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = 0;
      }
      return;
    }

    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, loading]);

  async function send(text: string) {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];

    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: updatedMessages }),
      });

      if (!res.ok) {
        throw new Error(`요청 실패: ${res.status}`);
      }

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            data.content ||
            data.message ||
            "죄송해요, 오류가 발생했어요.",
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "연결에 문제가 생겼어요. 잠시 후 다시 시도해 주세요.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function startNewChat() {
    setMessages(INITIAL_MESSAGES);
    setInput("");
    setLoading(false);

    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = 0;
    }
  }

  return (
    <div
      style={{
        height: "100dvh",
        overflow: "hidden",
        background: "var(--bg)",
        display: "flex",
        flexDirection: "column",
      }}
    >

      <div
        style={{
          display: "flex",
          flex: 1,
          minHeight: 0,
          maxWidth: 1040,
          margin: "20px auto 0",
          width: "100%",
          padding: "0 20px",
          boxSizing: "border-box",
        }}
      >
        <Sidebar
          sessions={sessions}
          currentSessionId="new"
          onNewChat={startNewChat}
        />

        <main
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            minHeight: 0,
          }}
        >
          <div style={{ padding: "24px 32px 0", flexShrink: 0 }}>
            <div
              style={{
                fontSize: "0.72rem",
                letterSpacing: "0.14em",
                color: "var(--ac)",
                fontWeight: 600,
                marginBottom: 10,
              }}
            >
              ● PERSONAL CONSULTATION
            </div>

            <h2
              style={{
                margin: "0 0 6px",
                fontSize: "1.6rem",
                fontWeight: 800,
                letterSpacing: "-0.04em",
              }}
            >
              새 채팅
            </h2>

            <p
              style={{
                margin: 0,
                fontSize: "0.88rem",
                color: "var(--mu)",
              }}
            >
              궁금한 내용을 편하게 이야기해 주세요.
            </p>

            <div
              style={{
                margin: "12px 0 4px",
                fontSize: "0.82rem",
                color: "#555",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--mu)"
                strokeWidth="1.7"
              >
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
              </svg>
              내 프로필 반영 중
            </div>

            <div style={{ fontSize: "0.78rem", color: "#bbb" }}>
              예시 프로필로 시작한 화면이에요.
            </div>
          </div>

          <hr
            style={{
              border: "none",
              borderTop: "1px solid var(--ln)",
              margin: "20px 32px",
              flexShrink: 0,
            }}
          />

          <div
            ref={messagesContainerRef}
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: "auto",
              overscrollBehavior: "contain",
              padding: "0 32px",
              display: "flex",
              flexDirection: "column",
              gap: 20,
            }}
          >
            {messages.map((msg, i) => (
              <div key={i}>
                {msg.role === "assistant" ? (
                  <div
                    style={{
                      display: "flex",
                      gap: 14,
                      alignItems: "flex-start",
                    }}
                  >
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: "50%",
                        border: "1.5px solid var(--ln)",
                        background: "#fff",
                        display: "grid",
                        placeItems: "center",
                        flexShrink: 0,
                      }}
                    >
                      <svg
                        width="17"
                        height="17"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="var(--ac)"
                        strokeWidth="1.8"
                      >
                        <circle cx="12" cy="12" r="4" />
                        <path d="M4 9a9 9 0 0 1 14-4M20 15a9 9 0 0 1-14 4" />
                      </svg>
                    </div>

                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: "0.82rem",
                          fontWeight: 600,
                          color: "var(--ink)",
                          marginBottom: 8,
                        }}
                      >
                        Global-In
                      </div>

                      <div
                        style={{
                          background: "#fff",
                          border: "1px solid var(--ln)",
                          borderRadius: "4px 16px 16px 16px",
                          padding: "16px 20px",
                          fontSize: "0.92rem",
                          lineHeight: 1.7,
                          maxWidth: 520,
                          overflowWrap: "anywhere",
                        }}
                      >
                        {renderContent(msg.content)}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                    }}
                  >
                    <div
                      style={{
                        background: "var(--ink)",
                        color: "#fff",
                        borderRadius: "16px 4px 16px 16px",
                        padding: "12px 18px",
                        fontSize: "0.92rem",
                        lineHeight: 1.6,
                        maxWidth: 400,
                        overflowWrap: "anywhere",
                      }}
                    >
                      {msg.content}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {messages.length === 1 && (
              <div
                style={{
                  paddingLeft: 50,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                  marginTop: -8,
                }}
              >
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => send(suggestion)}
                    disabled={loading}
                    style={{
                      border: "1px solid var(--ln)",
                      background: "#fff",
                      borderRadius: 20,
                      padding: "8px 16px",
                      fontSize: "0.85rem",
                      cursor: loading ? "default" : "pointer",
                      color: "var(--ink)",
                    }}
                  >
                    {suggestion}
                  </button>
                ))}

                <div
                  style={{
                    width: "100%",
                    fontSize: "0.78rem",
                    color: "#ccc",
                    marginTop: 6,
                  }}
                >
                  가까운 답변을 고르거나, 아래에 직접 적어 주세요.
                </div>
              </div>
            )}

            {loading && (
              <div
                style={{
                  display: "flex",
                  gap: 14,
                  alignItems: "flex-start",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    border: "1.5px solid var(--ln)",
                    background: "#fff",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                  }}
                >
                  <svg
                    width="17"
                    height="17"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--ac)"
                    strokeWidth="1.8"
                  >
                    <circle cx="12" cy="12" r="4" />
                    <path d="M4 9a9 9 0 0 1 14-4M20 15a9 9 0 0 1-14 4" />
                  </svg>
                </div>

                <div
                  style={{
                    background: "#fff",
                    border: "1px solid var(--ln)",
                    borderRadius: "4px 16px 16px 16px",
                    padding: "16px 20px",
                    color: "var(--mu)",
                    fontSize: "0.88rem",
                  }}
                >
                  답변을 준비하고 있어요…
                </div>
              </div>
            )}
          </div>

          <div
            style={{
              padding: "20px 32px 16px",
              flexShrink: 0,
            }}
          >
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send(input);
              }}
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: 10,
                background: "#fff",
                border: "1px solid var(--ln)",
                borderRadius: 16,
                padding: "14px 16px",
                boxShadow: "0 4px 16px rgba(30,35,70,.05)",
              }}
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(input);
                  }
                }}
                placeholder="편하게 이야기해 주세요."
                rows={1}
                style={{
                  flex: 1,
                  minWidth: 0,
                  border: "none",
                  outline: "none",
                  resize: "none",
                  fontSize: "0.92rem",
                  lineHeight: 1.6,
                  background: "transparent",
                  fontFamily: "inherit",
                }}
              />

              <button
                type="submit"
                disabled={!input.trim() || loading}
                aria-label="메시지 보내기"
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  background: input.trim() ? "var(--ink)" : "#e0e2ea",
                  border: "none",
                  display: "grid",
                  placeItems: "center",
                  flexShrink: 0,
                  cursor: input.trim() && !loading ? "pointer" : "default",
                  transition: "background 0.15s",
                }}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#fff"
                  strokeWidth="2.2"
                >
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            </form>

            <div
              style={{
                fontSize: "0.75rem",
                color: "#ccc",
                textAlign: "center",
                marginTop: 10,
              }}
            >
              화면 시안 · 채팅은 현재 화면을 닫기 전까지 유지돼요. 실제 AI 상담은 연결 전이에요.
            </div>
          </div>
        </main>
      </div>

      <footer
        style={{
          display: "flex",
          justifyContent: "space-between",
          maxWidth: 1040,
          margin: "0 auto",
          width: "100%",
          boxSizing: "border-box",
          padding: "20px 20px",
          fontSize: "0.78rem",
          color: "#ccc",
          flexShrink: 0,
        }}
      >
        <span>Global-In.</span>
        <span>해외에서의 다음 시작을 함께.</span>
      </footer>
    </div>
  );
}
