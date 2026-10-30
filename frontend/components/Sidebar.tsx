
"use client";

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

interface SidebarProps {
  sessions?: {
    id: string;
    title: string;
    pinned?: boolean;
  }[];
  currentSessionId?: string;
  onNewChat?: () => void;
  onSelectSession?: (id: string) => void;
  onRenameSession?: (id: string, title: string) => void;
  onDeleteSession?: (id: string) => void;
  onTogglePinSession?: (id: string) => void;
}

type ModalType = "rename" | "delete" | null;

const NAV = [
  {
    label: "AI 상담",
    href: "/chat",
    icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  },
  {
    label: "프로그램·지원제도 찾기",
    href: "/programs",
    icon: "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20M16.2 7.8l-2.1 6.3-6.3 2.1 2.1-6.3z",
  },
  {
    label: "플랜",
    href: "/preparation",
    icon: "M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2m-6 9l2 2 4-4",
  },
];

export default function Sidebar({
  sessions = [],
  currentSessionId,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  onTogglePinSession,
}: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const isChat = pathname?.startsWith("/chat");

  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  // 모달 상태
  const [modalType, setModalType] = useState<ModalType>(null);
  const [modalChatId, setModalChatId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  // 모달에 표시할 채팅
  const modalChat = sessions.find(
    (chat) => chat.id === modalChatId
  );

  // 고정된 채팅을 위쪽으로 정렬
  const sortedSessions = [...sessions].sort(
    (a, b) => Number(!!b.pinned) - Number(!!a.pinned)
  );

  // 모달 열기
  function openRenameModal(id: string, currentTitle: string) {
    setRenameValue(currentTitle);
    setModalChatId(id);
    setModalType("rename");
    setOpenMenuId(null);
  }

  function openDeleteModal(id: string) {
    setModalChatId(id);
    setModalType("delete");
    setOpenMenuId(null);
  }

  // 모달 닫기
  function closeModal() {
    setModalType(null);
    setModalChatId(null);
    setRenameValue("");
  }

  // 이름 변경 확정
  function confirmRename() {
    const trimmedTitle = renameValue.trim();

    if (!trimmedTitle || !modalChatId) return;

    onRenameSession?.(modalChatId, trimmedTitle);
    closeModal();
  }

  // 삭제 확정
  function confirmDelete() {
    if (!modalChatId) return;

    onDeleteSession?.(modalChatId);
    closeModal();
  }

  // ESC 키로 모달 닫기
  useEffect(() => {
    if (!modalType) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        closeModal();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [modalType, modalChatId]);

  return (
    <>
      <aside
        style={{
          width: 210,
          minWidth: 210,
          flex: "0 0 210px",
          height: "calc(100dvh - 130px)",
          minHeight: "calc(100dvh - 130px)",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid var(--ln)",
          background: "var(--bg)",
          position: "sticky",
          top: 91,
          alignSelf: "flex-start",
        }}
      >
        {/* 로고 */}
        <div
          style={{
            padding: "20px 16px 14px",
            display: "flex",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <img
            src="/logo/global-in-logo.svg"
            alt="Global-In"
            style={{
              width: "90%",
              maxWidth: "90%",
              height: "auto",
              cursor: "pointer",
            }}
            onClick={() => router.push("/")}
          />
        </div>

        {/* 새 채팅 버튼 */}
        {isChat && (
          <div
            style={{
              padding: "20px 16px 14px",
              flexShrink: 0,
            }}
          >
            <button
              onClick={onNewChat}
              style={{
                width: "100%",
                border: "1px solid var(--ln)",
                background: "#fff",
                borderRadius: 10,
                padding: "10px 0",
                fontSize: "0.88rem",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                cursor: "pointer",
                color: "var(--ink)",
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
              새 채팅
            </button>
          </div>
        )}

        {/* 둘러보기 */}
        <div
          style={{
            padding: isChat ? "0 16px 14px" : "20px 16px 14px",
            flexShrink: 0,
          }}
        >
          <button
            onClick={() => router.push("/")}
            style={{
              width: "100%",
              textAlign: "left",
              background: "none",
              border: "none",
              padding: "6px 8px",
              fontSize: "0.82rem",
              color: "var(--mu)",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              gap: 6,
              cursor: "pointer",
            }}
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            </svg>
            둘러보기
          </button>
        </div>

        {/* 네비게이션 */}
        <nav
          style={{
            padding: "0 16px 14px",
            borderBottom: "1px solid var(--ln)",
            flexShrink: 0,
          }}
        >
          {NAV.map((item) => {
            const active =
              pathname === item.href ||
              pathname?.startsWith(item.href + "/");

            return (
              <button
                key={item.href}
                onClick={() => router.push(item.href)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  background: active ? "var(--tn)" : "none",
                  border: "none",
                  padding: "9px 10px",
                  fontSize: "0.86rem",
                  color: active ? "var(--ac)" : "#3b3f4d",
                  borderRadius: 9,
                  display: "flex",
                  alignItems: "center",
                  gap: 9,
                  fontWeight: active ? 600 : 400,
                  marginBottom: 2,
                  cursor: "pointer",
                }}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                >
                  <path d={item.icon} />
                </svg>
                <span style={{ lineHeight: 1.3 }}>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* 채팅 목록 */}
        {isChat && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              flex: 1,
              minHeight: 0,
              overflow: "hidden",
            }}
          >
            {/* 고정되는 제목 */}
            {sessions.length > 0 && (
              <div
                style={{
                  flexShrink: 0,
                  padding: "14px 16px 8px",
                  background: "var(--bg)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.72rem",
                    color: "var(--mu)",
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    paddingLeft: 2,
                  }}
                >
                  채팅 목록
                </div>
              </div>
            )}

            {/* 실제 채팅 항목만 스크롤 */}
            <div
              style={{
                flex: 1,
                minHeight: 0,
                overflowY: "auto",
                overflowX: "hidden",
                padding: "0 10px 14px 16px",
                overscrollBehavior: "contain",
              }}
            >
              {sortedSessions.map((s) => (
                <div
                  key={s.id}
                  style={{
                    position: "relative",
                    display: "flex",
                    alignItems: "center",
                    width: "100%",
                    marginBottom: 2,
                    borderRadius: 8,
                    background:
                      s.id === currentSessionId
                        ? "var(--tn)"
                        : "transparent",
                  }}
                >
                  {/* 채팅 선택 */}
                  <button
                    onClick={() => {
                      setOpenMenuId(null);
                      onSelectSession?.(s.id);
                    }}
                    style={{
                      flex: 1,
                      minWidth: 0,
                      textAlign: "left",
                      background: "transparent",
                      border: "none",
                      padding: "8px 4px 8px 10px",
                      fontSize: "0.83rem",
                      borderRadius: 8,
                      cursor: "pointer",
                      color: "var(--ink)",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <svg
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--ac)"
                      strokeWidth="1.7"
                      style={{ flexShrink: 0 }}
                    >
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>

                    <span
                      style={{
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        flex: 1,
                      }}
                    >
                      {s.title}
                    </span>

                    {s.pinned && (
                      <svg
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="var(--ac)"
                        strokeWidth="2"
                        style={{ flexShrink: 0 }}
                      >
                        <path d="M16 3l5 5-4 1-4 4-1 4-2-2-4 4-2-2 4-4-2-2 4-1 4-4z" />
                      </svg>
                    )}
                  </button>

                  {/* 점 3개 메뉴 버튼 */}
                  <button
                    aria-label={`${s.title} 메뉴`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpenMenuId(
                        openMenuId === s.id ? null : s.id
                      );
                    }}
                    style={{
                      width: 30,
                      height: 30,
                      flexShrink: 0,
                      border: "none",
                      borderRadius: 7,
                      background:
                        openMenuId === s.id
                          ? "#e9ebf5"
                          : "transparent",
                      color: "var(--mu)",
                      cursor: "pointer",
                      display: "grid",
                      placeItems: "center",
                      marginRight: 2,
                      fontSize: 19,
                      lineHeight: 1,
                    }}
                  >
                    ⋯
                  </button>

                  {/* 메뉴 팝업 */}
                  {openMenuId === s.id && (
                    <>
                      <div
                        onClick={() => setOpenMenuId(null)}
                        style={{
                          position: "fixed",
                          inset: 0,
                          zIndex: 20,
                        }}
                      />

                      <div
                        style={{
                          position: "absolute",
                          right: 4,
                          top: 34,
                          width: 150,
                          padding: 5,
                          background: "#fff",
                          border: "1px solid var(--ln)",
                          borderRadius: 10,
                          boxShadow: "0 6px 20px rgba(0,0,0,0.12)",
                          zIndex: 21,
                        }}
                      >
                        {/* 이름 변경 */}
                        <button
                          onClick={() =>
                            openRenameModal(s.id, s.title)
                          }
                          style={menuItemStyle}
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.8"
                          >
                            <path d="M12 20h9" />
                            <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" />
                          </svg>
                          이름 변경
                        </button>

                        {/* 상단 고정 */}
                        <button
                          onClick={() => {
                            onTogglePinSession?.(s.id);
                            setOpenMenuId(null);
                          }}
                          style={menuItemStyle}
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.8"
                          >
                            <path d="M16 3l5 5-4 1-4 4-1 4-2-2-4 4-2-2 4-4-2-2 4-1 4-4z" />
                          </svg>
                          {s.pinned ? "고정 해제" : "상단 고정"}
                        </button>

                        <div
                          style={{
                            height: 1,
                            background: "var(--ln)",
                            margin: "4px 2px",
                          }}
                        />

                        {/* 삭제 */}
                        <button
                          onClick={() => openDeleteModal(s.id)}
                          style={{
                            ...menuItemStyle,
                            color: "#dc4545",
                          }}
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.8"
                          >
                            <path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6" />
                          </svg>
                          대화 삭제
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 내 프로필 */}
        <div
          style={{
            marginTop: "auto",
            padding: "10px 16px 22px",
            borderTop: "1px solid var(--ln)",
            flexShrink: 0,
          }}
        >
          <button
            onClick={() => router.push("/profile")}
            style={{
              background: "none",
              border: "none",
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: "0.86rem",
              color: "#3b3f4d",
              cursor: "pointer",
              padding: "6px 4px",
            }}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z" />
            </svg>
            내 프로필
          </button>
        </div>
      </aside>

      {/* ================================== */}
      {/* 이름 변경 / 삭제 공통 모달 */}
      {/* ================================== */}
      {modalType && (
        <div
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) {
              closeModal();
            }
          }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            background: "rgba(20, 27, 38, 0.48)",
            backdropFilter: "blur(3px)",
            WebkitBackdropFilter: "blur(3px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
            boxSizing: "border-box",
            animation: "modalFadeIn 0.18s ease",
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="chat-modal-title"
            onMouseDown={(e) => e.stopPropagation()}
            style={{
              width: "100%",
              maxWidth: 440,
              background: "#fff",
              borderRadius: 20,
              padding: "28px",
              boxSizing: "border-box",
              boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
              animation: "modalSlideIn 0.22s ease",
            }}
          >
            {/* 모달 상단 */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 22,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    width: 42,
                    height: 42,
                    borderRadius: 12,
                    background:
                      modalType === "rename"
                        ? "#e9f5f7"
                        : "#fff0f0",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                  }}
                >
                  {modalType === "rename" ? (
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#286978"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" />
                    </svg>
                  ) : (
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#dc4545"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6" />
                      <path d="M10 11v5m4-5v5" />
                    </svg>
                  )}
                </div>

                <div>
                  <h3
                    id="chat-modal-title"
                    style={{
                      margin: 0,
                      fontSize: "1.12rem",
                      fontWeight: 750,
                      color: "#202633",
                      letterSpacing: "-0.03em",
                    }}
                  >
                    {modalType === "rename"
                      ? "채팅 이름 변경"
                      : "채팅 삭제"}
                  </h3>

                  <p
                    style={{
                      margin: "4px 0 0",
                      fontSize: "0.76rem",
                      color: "#9299a6",
                    }}
                  >
                    {modalType === "rename"
                      ? "대화 이름을 새롭게 설정해 보세요."
                      : "대화 관리"}
                  </p>
                </div>
              </div>

              {/* 닫기 버튼 */}
              <button
                onClick={closeModal}
                aria-label="팝업 닫기"
                style={{
                  width: 32,
                  height: 32,
                  border: "none",
                  borderRadius: 8,
                  background: "#f3f5f7",
                  color: "#727987",
                  cursor: "pointer",
                  display: "grid",
                  placeItems: "center",
                  fontSize: 20,
                }}
              >
                ×
              </button>
            </div>

            {/* 이름 변경 내용 */}
            {modalType === "rename" && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  confirmRename();
                }}
              >
                <label
                  htmlFor="chat-rename-input"
                  style={{
                    display: "block",
                    fontSize: "0.83rem",
                    fontWeight: 600,
                    color: "#414957",
                    marginBottom: 9,
                  }}
                >
                  새로운 채팅 이름
                </label>

                <input
                  id="chat-rename-input"
                  autoFocus
                  maxLength={60}
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  placeholder="채팅 이름을 입력해 주세요."
                  style={{
                    width: "100%",
                    height: 48,
                    boxSizing: "border-box",
                    border: "1px solid #dce2e8",
                    borderRadius: 10,
                    padding: "0 14px",
                    outline: "none",
                    fontSize: "0.9rem",
                    color: "#202633",
                    background: "#fbfcfd",
                    fontFamily: "inherit",
                    transition: "border-color 0.15s",
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = "#286978";
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = "#dce2e8";
                  }}
                />

                <div
                  style={{
                    marginTop: 7,
                    fontSize: "0.72rem",
                    color: "#a0a6b1",
                    textAlign: "right",
                  }}
                >
                  {renameValue.length}/60
                </div>

                {/* 버튼 */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: 9,
                    marginTop: 25,
                  }}
                >
                  <button
                    type="button"
                    onClick={closeModal}
                    style={cancelButtonStyle}
                  >
                    취소
                  </button>

                  <button
                    type="submit"
                    disabled={!renameValue.trim()}
                    style={{
                      ...primaryButtonStyle,
                      opacity: renameValue.trim() ? 1 : 0.5,
                      cursor: renameValue.trim()
                        ? "pointer"
                        : "not-allowed",
                    }}
                  >
                    변경하기
                  </button>
                </div>
              </form>
            )}

            {/* 삭제 내용 */}
            {modalType === "delete" && (
              <>
                <div
                  style={{
                    background: "#fff8f8",
                    border: "1px solid #f5e3e3",
                    borderRadius: 12,
                    padding: "16px",
                    marginBottom: 22,
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.84rem",
                      fontWeight: 600,
                      color: "#3d4552",
                      marginBottom: 7,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {modalChat?.title || "선택한 채팅"}
                  </div>

                  <p
                    style={{
                      margin: 0,
                      fontSize: "0.8rem",
                      color: "#737b88",
                      lineHeight: 1.6,
                    }}
                  >
                    이 대화를 정말 삭제하시겠어요?
                    <br />
                    삭제한 대화는 복구할 수 없습니다.
                  </p>
                </div>

                {/* 버튼 */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: 9,
                  }}
                >
                  <button
                    type="button"
                    onClick={closeModal}
                    style={cancelButtonStyle}
                  >
                    취소
                  </button>

                  <button
                    type="button"
                    onClick={confirmDelete}
                    style={{
                      ...primaryButtonStyle,
                      background: "#dc4545",
                    }}
                  >
                    삭제하기
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* 모달 애니메이션 */}
      <style jsx global>{`
        @keyframes modalFadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes modalSlideIn {
          from {
            opacity: 0;
            transform: translateY(12px) scale(0.98);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>
    </>
  );
}

// 공통 취소 버튼 스타일
const cancelButtonStyle: React.CSSProperties = {
  minWidth: 86,
  height: 42,
  padding: "0 17px",
  border: "1px solid #e0e4e9",
  borderRadius: 9,
  background: "#fff",
  color: "#596170",
  fontSize: "0.83rem",
  fontWeight: 600,
  cursor: "pointer",
};

// 공통 확인 버튼 스타일
const primaryButtonStyle: React.CSSProperties = {
  minWidth: 100,
  height: 42,
  padding: "0 18px",
  border: "none",
  borderRadius: 9,
  background: "#286978",
  color: "#fff",
  fontSize: "0.83rem",
  fontWeight: 600,
  cursor: "pointer",
};

// 채팅 메뉴 버튼 스타일
const menuItemStyle: React.CSSProperties = {
  width: "100%",
  display: "flex",
  alignItems: "center",
  gap: 9,
  padding: "9px 10px",
  border: "none",
  borderRadius: 7,
  background: "transparent",
  color: "var(--ink)",
  fontSize: "0.8rem",
  textAlign: "left",
  cursor: "pointer",
};
