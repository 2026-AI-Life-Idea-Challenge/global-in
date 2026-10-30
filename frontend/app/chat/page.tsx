"use client";

import {
  useState,
  useRef,
  useEffect,
  useLayoutEffect,
  Suspense,
} from "react";
import { useSearchParams } from "next/navigation";

import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import ConsultationDetails, {
  type ConsultationDetailsData,
} from "@/components/ConsultationDetails";

import {
  CHAT_KEY,
  PROFILE_KEY,
  readSaved,
  saveTab,
  expireConsultation,
  latestPrograms,
  invalidateResults,
} from "@/lib/consultation";

import { useComparison } from "@/lib/useComparison";
import { COUNTRY_NAMES, CATEGORY_NAMES } from "@/lib/catalog";

interface Message {
  role: "user" | "assistant";
  content: string;
  programs?: Program[];
  details?: ConsultationDetailsData;
}

interface Program {
  id: string | number;
  name: string;
  country?: string | null;
  type?: string;
  tags?: string[];
  desc?: string;
  description?: string;
  condition_summary?: string;
  official_url?: string;
  officialUrl?: string;
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  pinned?: boolean;

  // 각 채팅에 연결된 백엔드 상담 세션 ID
  sessionId?: string | null;
}

const STORAGE_KEY = "global-in-chats";
const ACTIVE_CHAT_KEY = "global-in-active-chat";
const AI_LOGO = "/logo/global-in-icon-512.png";

const FLAGS: Record<string, string> = {
  독일:
    '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  일본:
    '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  호주:
    '<rect width="30" height="20" fill="#00247d"/><path d="M0 0l14 9M14 0L0 9" stroke="#fff" strokeWidth="1.6"/><path d="M7 0v9M0 4.5h14" stroke="#fff" strokeWidth="3"/><path d="M7 0v9M0 4.5h14" stroke="#cf142b" strokeWidth="1.6"/>',
  미국:
    '<rect width="30" height="20" fill="#fff"/><rect y="0" width="30" height="1.55" fill="#b22234"/><rect y="3.1" width="30" height="1.55" fill="#b22234"/><rect y="6.2" width="30" height="1.55" fill="#b22234"/><rect y="9.3" width="30" height="1.55" fill="#b22234"/><rect y="12.4" width="30" height="1.55" fill="#b22234"/><rect y="15.5" width="30" height="1.55" fill="#b22234"/><rect y="18.6" width="30" height="1.55" fill="#b22234"/><rect width="13" height="10.8" fill="#3c3b6e"/>',
  캐나다:
    '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/><path d="M15 4l1.3 3 2-1-.6 4 1.7-.4-.4 1.8 1.5 1-3.5 2.4.2 2.2h-4.4l.2-2.2-3.5-2.4 1.5-1-.4-1.8 1.7.4-.6-4 2 1z" fill="#d52b1e"/>',
  Japan:
    '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  Australia: '<rect width="30" height="20" fill="#00247d"/>',
  Germany:
    '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  Canada:
    '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/>',
};

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

function FlagSvg({
  country,
  size = 20,
}: {
  country?: string | null;
  size?: number;
}) {
  if (!country || !FLAGS[country]) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--mu)"
        strokeWidth="1.6"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20" />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 30 20"
      style={{
        width: size,
        height: Math.round((size * 2) / 3),
        borderRadius: 2,
        flexShrink: 0,
      }}
      dangerouslySetInnerHTML={{ __html: FLAGS[country] }}
    />
  );
}

function renderContent(text: string) {
  return text.split("\n").map((line, i, arr) => {
    const parts = line.split(/\*\*(.*?)\*\*/g);

    return (
      <span key={i}>
        {parts.map((part, j) =>
          j % 2 === 1 ? <strong key={j}>{part}</strong> : part
        )}
        {i < arr.length - 1 && <br />}
      </span>
    );
  });
}

// AI 프로필 이미지
function AiAvatar() {
  return (
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
        overflow: "hidden",
      }}
    >
      <img
        src={AI_LOGO}
        alt="Global-In AI"
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
    </div>
  );
}

// 프로그램 카드
function ProgramCard({
  program,
  isCompared,
  onToggleCompare,
}: {
  program: Program;
  isCompared: boolean;
  onToggleCompare: (id: string | number) => void;
}) {
  const officialUrl = program.official_url || program.officialUrl;

  const desc =
    program.desc ||
    program.description ||
    program.condition_summary ||
    "";

  return (
    <div
      style={{
        background: "#fff",
        border: `1px solid ${isCompared ? "var(--ac)" : "var(--ln)"}`,
        borderRadius: 12,
        padding: "14px 16px",
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
        transition: "border-color 0.15s",
      }}
    >
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          background: "var(--tn)",
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
          overflow: "hidden",
        }}
      >
        <FlagSvg country={program.country} size={20} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {program.type && (
          <span
            style={{
              fontSize: "0.68rem",
              fontWeight: 600,
              padding: "2px 7px",
              borderRadius: 5,
              background: "var(--tn)",
              color: "var(--ac)",
              display: "inline-block",
              marginBottom: 5,
            }}
          >
            {program.type}
          </span>
        )}

        <div
          style={{
            fontWeight: 700,
            fontSize: "0.88rem",
            marginBottom: 3,
            lineHeight: 1.4,
          }}
        >
          {program.name}
        </div>

        {desc && (
          <div
            style={{
              fontSize: "0.78rem",
              color: "#555",
              lineHeight: 1.5,
              marginBottom: 8,
            }}
          >
            {desc}
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          {officialUrl && (
            <a
              href={officialUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 3,
                fontSize: "0.78rem",
                color: "var(--ink)",
                fontWeight: 500,
                textDecoration: "none",
                border: "1px solid var(--ln)",
                borderRadius: 8,
                padding: "5px 10px",
                background: "#fff",
              }}
            >
              공식 페이지
              <svg
                width="10"
                height="10"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M7 7h10v10M7 17L17 7" />
              </svg>
            </a>
          )}

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              cursor: "pointer",
              userSelect: "none",
            }}
          >
            <input
              type="checkbox"
              aria-label={`${program.name} 비교하기`}
              checked={isCompared}
              onChange={() => onToggleCompare(program.id)}
              style={{
                width: 16,
                height: 16,
                borderRadius: 4,
                accentColor: "var(--ac)",
                cursor: "pointer",
                flexShrink: 0,
              }}
            />

            <span
              style={{
                fontSize: "0.76rem",
                color: isCompared ? "var(--ac)" : "var(--mu)",
                fontWeight: isCompared ? 600 : 400,
              }}
            >
              비교하기
            </span>
          </label>
        </div>
      </div>
    </div>
  );
}

function ChatPageInner() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);

  const [isHydrated, setIsHydrated] = useState(false);
  const [profilePending, setProfilePending] = useState(false);

  const comparison = useComparison();
  const compareIds = comparison.items.map((item) => item.id);
  const comparePrograms: Program[] = comparison.items;

  const searchParams = useSearchParams();

  const autoSentRef = useRef(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const didMountRef = useRef(false);
  const requestVersion = useRef(0);
  const pendingRequest = useRef(false);

  // --------------------------------------------------
  // 1. Local Storage에서 채팅 목록 및 현재 채팅 복원
  // --------------------------------------------------

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const activeId = localStorage.getItem(ACTIVE_CHAT_KEY);

      let parsed: ChatSession[] = [];

      if (saved) {
        const data = JSON.parse(saved);

        if (Array.isArray(data)) {
          parsed = data.filter(
            (chat): chat is ChatSession =>
              chat &&
              typeof chat.id === "string" &&
              typeof chat.title === "string" &&
              Array.isArray(chat.messages)
          );
        }
      }

      setSessions(parsed);

      const activeChat = parsed.find((chat) => chat.id === activeId);

      if (activeChat) {
        setCurrentChatId(activeChat.id);
        setMessages(activeChat.messages ?? INITIAL_MESSAGES);
        setSessionId(activeChat.sessionId ?? null);
      } else {
        setCurrentChatId(null);
        setMessages(INITIAL_MESSAGES);
        setSessionId(null);
      }

      // 기존 버전에서 저장된 상담 상태 복원
      const savedConsultation = readSaved<{
        session_id?: string;
        profile_pending?: boolean;
      }>(CHAT_KEY, {});

      if (
        !activeChat &&
        savedConsultation.session_id &&
        /^[a-f0-9]{32}$/.test(savedConsultation.session_id)
      ) {
        setSessionId(savedConsultation.session_id);
      }

      setProfilePending(savedConsultation.profile_pending === true);
    } catch (error) {
      console.error("채팅 목록을 불러오지 못했습니다.", error);

      setSessions([]);
      setCurrentChatId(null);
      setMessages(INITIAL_MESSAGES);
      setSessionId(null);
    } finally {
      setIsHydrated(true);
    }
  }, []);

  // --------------------------------------------------
  // 2. Local Storage에 채팅 목록 자동 저장
  // --------------------------------------------------

  useEffect(() => {
    if (!isHydrated) return;

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    } catch (error) {
      console.error("채팅 목록을 저장하지 못했습니다.", error);
    }
  }, [sessions, isHydrated]);

  // --------------------------------------------------
  // 3. 마지막으로 선택한 채팅 ID 저장
  // --------------------------------------------------

  useEffect(() => {
    if (!isHydrated) return;

    try {
      localStorage.setItem(ACTIVE_CHAT_KEY, currentChatId ?? "");
    } catch (error) {
      console.error("현재 채팅 정보를 저장하지 못했습니다.", error);
    }
  }, [currentChatId, isHydrated]);

  // --------------------------------------------------
  // 4. 현재 채팅의 메시지 및 sessionId 동기화
  // --------------------------------------------------

  useEffect(() => {
    if (!isHydrated || !currentChatId) return;

    setSessions((prev) =>
      prev.map((chat) =>
        chat.id === currentChatId
          ? {
              ...chat,
              messages,
              sessionId,
            }
          : chat
      )
    );
  }, [messages, sessionId, currentChatId, isHydrated]);

  // --------------------------------------------------
  // 5. Session Storage에 현재 상담 상태 저장
  // --------------------------------------------------

  useEffect(() => {
    if (!isHydrated) return;

    saveTab(CHAT_KEY, {
      session_id: sessionId,
      messages,
      compareIds,
      profile_pending: profilePending,
    });
  }, [
    isHydrated,
    sessionId,
    messages,
    compareIds,
    profilePending,
  ]);

  // --------------------------------------------------
  // 6. 입력창 높이 자동 조절
  // --------------------------------------------------

  useLayoutEffect(() => {
    const textarea = inputRef.current;

    if (!textarea) return;

    const MAX_HEIGHT = 160;

    textarea.style.height = "auto";

    const nextHeight = Math.min(textarea.scrollHeight, MAX_HEIGHT);

    textarea.style.height = `${nextHeight}px`;

    textarea.style.overflowY =
      textarea.scrollHeight > MAX_HEIGHT ? "auto" : "hidden";
  }, [input]);

  // --------------------------------------------------
  // 7. 상세 페이지에서 AI와 상담하기를 클릭한 경우
  // --------------------------------------------------

  useEffect(() => {
    if (!isHydrated || autoSentRef.current) return;

    const program = searchParams?.get("program");

    if (!program) return;

    autoSentRef.current = true;

    const timer = window.setTimeout(() => {
      send(
        program +
          "에 대해 자세히 알고 싶어요. 저에게 맞는지 상담해 주세요."
      );
    }, 400);

    return () => window.clearTimeout(timer);

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isHydrated, searchParams]);

  // --------------------------------------------------
  // 8. 페이지 최초 진입 시 스크롤 초기화
  // --------------------------------------------------

  useLayoutEffect(() => {
    const html = document.documentElement;

    const previousScrollBehavior = html.style.scrollBehavior;
    const previousScrollbarGutter = html.style.scrollbarGutter;

    html.style.scrollbarGutter = "stable";
    html.style.scrollBehavior = "auto";

    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "auto",
    });

    html.scrollTop = 0;
    document.body.scrollTop = 0;

    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = 0;
    }

    return () => {
      html.style.scrollBehavior = previousScrollBehavior;
      html.style.scrollbarGutter = previousScrollbarGutter;
    };
  }, []);

  // --------------------------------------------------
  // 9. 메시지가 추가되면 대화 영역 아래로 스크롤
  // --------------------------------------------------

  useEffect(() => {
    if (!isHydrated) return;

    if (!didMountRef.current) {
      didMountRef.current = true;
      return;
    }

    const container = messagesContainerRef.current;

    if (!container) return;

    if (messages.length <= 1) {
      container.scrollTop = 0;
      return;
    }

    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading, isHydrated]);

  // --------------------------------------------------
  // 10. 프로그램 비교 기능
  // --------------------------------------------------

  function toggleCompare(id: string | number) {
    const program = latestPrograms(messages).find(
      (item) => item.id === id
    );

    if (program) {
      comparison.toggle(program);
    }
  }

  // 메시지에 포함된 프로그램이 변경되면 비교 가능한 항목 갱신
  useEffect(() => {
    if (!isHydrated) return;

    comparison.refresh(latestPrograms(messages));

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isHydrated, messages]);

  // --------------------------------------------------
  // 11. 채팅 이름 변경
  // --------------------------------------------------

  function renameChat(id: string, title: string) {
    setSessions((prev) =>
      prev.map((chat) =>
        chat.id === id ? { ...chat, title } : chat
      )
    );
  }

  // --------------------------------------------------
  // 12. 채팅 상단 고정 / 고정 해제
  // --------------------------------------------------

  function togglePinChat(id: string) {
    setSessions((prev) =>
      prev.map((chat) =>
        chat.id === id
          ? { ...chat, pinned: !chat.pinned }
          : chat
      )
    );
  }

  // --------------------------------------------------
  // 13. 진행 중인 요청 무효화
  // --------------------------------------------------

  function cancelPendingRequest() {
    requestVersion.current += 1;
    pendingRequest.current = false;
    setLoading(false);
  }

  // --------------------------------------------------
  // 14. 채팅 삭제
  // --------------------------------------------------

  function deleteChat(id: string) {
    const remainingSessions = sessions.filter(
      (chat) => chat.id !== id
    );

    setSessions(remainingSessions);

    if (currentChatId !== id) return;

    cancelPendingRequest();

    if (remainingSessions.length > 0) {
      const sortedRemaining = [...remainingSessions].sort(
        (a, b) => Number(!!b.pinned) - Number(!!a.pinned)
      );

      const nextChat = sortedRemaining[0];

      setCurrentChatId(nextChat.id);
      setMessages(nextChat.messages ?? INITIAL_MESSAGES);
      setSessionId(nextChat.sessionId ?? null);
    } else {
      setCurrentChatId(null);
      setMessages(INITIAL_MESSAGES);
      setSessionId(null);
    }

    setInput("");
    setProfilePending(false);
    comparison.clear();

    try {
      sessionStorage.removeItem("global-in-consult-result");
    } catch {
      // Storage may be disabled.
    }
  }

  // --------------------------------------------------
  // 15. 새 채팅 시작
  // --------------------------------------------------

  function startNewChat() {
    cancelPendingRequest();

    setMessages(INITIAL_MESSAGES);
    setSessionId(null);
    setCurrentChatId(null);
    setInput("");
    setProfilePending(false);

    comparison.clear();

    try {
      sessionStorage.removeItem("global-in-consult-result");
    } catch {
      // Storage may be disabled.
    }

    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = 0;
    }
  }

  // --------------------------------------------------
  // 16. 기존 채팅 선택
  // --------------------------------------------------

  function selectChat(id: string) {
    const selected = sessions.find((chat) => chat.id === id);

    if (!selected) return;

    cancelPendingRequest();

    setCurrentChatId(selected.id);
    setMessages(selected.messages ?? INITIAL_MESSAGES);
    setSessionId(selected.sessionId ?? null);
    setInput("");
    setProfilePending(false);

    comparison.clear();

    try {
      sessionStorage.removeItem("global-in-consult-result");
    } catch {
      // Storage may be disabled.
    }

    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = 0;
    }
  }

  // --------------------------------------------------
  // 17. 메시지 전송
  // --------------------------------------------------

  async function send(text: string) {
    const trimmedText = text.trim();

    if (!isHydrated || !trimmedText || pendingRequest.current) {
      return;
    }

    pendingRequest.current = true;

    const version = ++requestVersion.current;

    // 현재 채팅 ID와 백엔드 세션 ID를 요청 시작 시점에 고정
    let chatId = currentChatId;
    const requestSessionId = sessionId;

    const userMsg: Message = {
      role: "user",
      content: trimmedText,
    };

    const updatedMessages = [...messages, userMsg];

    // 새 채팅이면 첫 메시지를 보내는 시점에 채팅 생성
    if (!chatId) {
      chatId = crypto.randomUUID();

      const newChat: ChatSession = {
        id: chatId,
        title:
          trimmedText.length > 25
            ? trimmedText.slice(0, 25) + "..."
            : trimmedText,
        messages: updatedMessages,
        pinned: false,
        sessionId: null,
      };

      setSessions((prev) => [newChat, ...prev]);
      setCurrentChatId(chatId);
    } else {
      setSessions((prev) =>
        prev.map((chat) =>
          chat.id === chatId
            ? { ...chat, messages: updatedMessages }
            : chat
        )
      );
    }

    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      const profile = readSaved<{ profile?: unknown }>(
        PROFILE_KEY,
        {}
      ).profile;

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: updatedMessages,
          session_id: requestSessionId,
          profile_pending: profilePending,
          profile,
        }),
      });

      const data = await res.json();

      // 채팅을 전환하거나 새 채팅을 시작했다면 이전 응답 무시
      if (version !== requestVersion.current) return;

      // 상담 세션 만료 처리
      if (res.status === 404) {
        expireConsultation();

        setSessionId(null);
        setProfilePending(false);

        comparison.clear();

        const expiredMessages = [
          ...invalidateResults(updatedMessages),
          {
            role: "assistant" as const,
            content:
              "상담이 만료되어 이전 결과를 정리했습니다. 저장한 프로필은 유지됩니다. 질문을 다시 보내면 새 상담을 시작합니다.",
          },
        ];

        setMessages(expiredMessages);

        setSessions((prev) =>
          prev.map((chat) =>
            chat.id === chatId
              ? {
                  ...chat,
                  messages: expiredMessages,
                  sessionId: null,
                }
              : chat
          )
        );

        return;
      }

      if (!res.ok) {
        throw new Error(
          data.error ||
            data.content ||
            `요청 실패: ${res.status}`
        );
      }

      // 백엔드에서 생성한 상담 세션 ID 저장
      const nextSessionId = data.session_id ?? requestSessionId;

      setSessionId(nextSessionId);

      setSessions((prev) =>
        prev.map((chat) =>
          chat.id === chatId
            ? {
                ...chat,
                sessionId: nextSessionId,
              }
            : chat
        )
      );

      setProfilePending(false);

      // 백엔드 프로그램 데이터를 프론트엔드 형식으로 변환
      const programs: Program[] = (data.programs ?? [])
        .slice(0, 3)
        .map(
          (program: {
            program_id: string;
            name: string;
            country: string;
            visa_type: string;
            summary: string;
          }) => ({
            id: program.program_id,
            name: program.name,
            country:
              COUNTRY_NAMES[program.country] || program.country,
            type:
              CATEGORY_NAMES[program.visa_type] ||
              program.visa_type,
            desc: program.summary,
          })
        );

      // 상담 결과를 현재 브라우저 탭에 저장
      try {
        sessionStorage.setItem(
          "global-in-consult-result",
          JSON.stringify(data)
        );
      } catch {
        // Storage may be disabled.
      }

      const assistantMessage: Message = {
        role: "assistant",
        content:
          data.content ||
          data.message ||
          "죄송해요, 오류가 발생했어요.",
        programs: programs.length > 0 ? programs : undefined,
        details: data,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      if (version !== requestVersion.current) return;

      console.error("채팅 API 요청 오류:", error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            error instanceof Error
              ? error.message
              : "연결에 문제가 생겼어요. 잠시 후 다시 시도해 주세요.",
        },
      ]);
    } finally {
      if (version === requestVersion.current) {
        setLoading(false);
        pendingRequest.current = false;
      }
    }
  }

  // --------------------------------------------------
  // 18. 현재 채팅 제목
  // --------------------------------------------------

  const currentTitle =
    sessions.find((chat) => chat.id === currentChatId)?.title ||
    "새 채팅";

  // Local Storage 복원 전 화면 조작 방지
  if (!isHydrated) {
    return (
      <div
        style={{
          height: "100dvh",
          display: "grid",
          placeItems: "center",
          background: "var(--bg)",
          color: "var(--mu)",
          fontSize: "0.9rem",
        }}
      >
        상담 내용을 불러오고 있어요...
      </div>
    );
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
      <div style={{ flexShrink: 0 }}>
        <Header rightLabel="맞춤 상담" />
      </div>

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
          currentSessionId={currentChatId ?? ""}
          onNewChat={startNewChat}
          onSelectSession={selectChat}
          onRenameSession={renameChat}
          onDeleteSession={deleteChat}
          onTogglePinSession={togglePinChat}
        />

        <main
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            minHeight: 0,
            overflow: "hidden",
          }}
        >
          {/* 상담 상단 + 대화 내용: 하나의 영역으로 함께 스크롤 */}
          <div
            ref={messagesContainerRef}
            style={{
              flex: "1 1 0%",
              minHeight: 0,
              overflowY: "auto",
              overflowX: "hidden",
              overscrollBehavior: "contain",
              scrollbarGutter: "stable",
              display: "flex",
              flexDirection: "column",
              paddingBottom: 20,
            }}
          >
            {/* 상담 페이지 상단 */}
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
                {currentTitle}
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
                대화에서 확인한 정보를 바탕으로 안내
              </div>

              <div style={{ fontSize: "0.78rem", color: "#bbb" }}>
                조건이 달라지면 대화에서 수정해 주세요.
              </div>

              {profilePending && (
                <p role="status">
                  프로필은 저장됐지만 재검토가 완료되지 않았습니다.
                  다음 질문을 보내면 반영을 다시 시도합니다.{" "}
                  <a href="/profile">프로필 확인</a>
                </p>
              )}
            </div>

            <hr
              style={{
                border: "none",
                borderTop: "1px solid var(--ln)",
                margin: "20px 32px",
                flexShrink: 0,
              }}
            />

            {/* 대화 내용 */}
            <div
              style={{
                padding: "0 32px 20px",
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
                      <AiAvatar />

                      <div style={{ minWidth: 0, flex: 1 }}>
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

                        {/* 상세 상담 결과 */}
                        {msg.details && (
                          <ConsultationDetails data={msg.details} />
                        )}

                        {/* 추천 프로그램 */}
                        {msg.programs && msg.programs.length > 0 && (
                          <div style={{ marginTop: 12 }}>
                            <div
                              style={{
                                fontSize: "0.76rem",
                                color: "var(--mu)",
                                marginBottom: 8,
                                fontWeight: 600,
                                letterSpacing: "0.04em",
                              }}
                            >
                              ● 검토할 프로그램 후보 {msg.programs.length}개
                            </div>

                            <div
                              style={{
                                display: "flex",
                                flexDirection: "column",
                                gap: 8,
                                maxWidth: 520,
                              }}
                            >
                              {msg.programs.map((program) => (
                                <ProgramCard
                                  key={program.id}
                                  program={program}
                                  isCompared={compareIds.includes(
                                    program.id
                                  )}
                                  onToggleCompare={toggleCompare}
                                />
                              ))}
                            </div>

                            {compareIds.length === 1 && (
                              <div
                                style={{
                                  fontSize: "0.76rem",
                                  color: "var(--mu)",
                                  marginTop: 6,
                                }}
                              >
                                1개 더 선택하면 비교표가 나타나요.
                              </div>
                            )}
                          </div>
                        )}
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

              {/* 추천 질문 */}
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

              {/* 답변 로딩 */}
              {loading && (
                <div
                  style={{
                    display: "flex",
                    gap: 14,
                    alignItems: "flex-start",
                  }}
                >
                  <AiAvatar />

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

              {/* 프로그램 비교 */}
              {comparePrograms.length >= 2 && (
                <div
                  style={{
                    background: "#fff",
                    border: "1px solid var(--ln)",
                    borderRadius: 14,
                    overflow: "hidden",
                    marginTop: 8,
                  }}
                >
                  <div
                    style={{
                      padding: "14px 20px",
                      borderBottom: "1px solid var(--ln)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: "0.92rem" }}>
                      비교
                      <span
                        style={{
                          fontSize: "0.78rem",
                          fontWeight: 400,
                          color: "var(--mu)",
                          marginLeft: 8,
                        }}
                      >
                        {comparePrograms.length}개 선택됨
                      </span>

                      {" "}
                      <a href="/compare">비교 화면 열기</a>
                    </div>

                    <button
                      onClick={comparison.clear}
                      style={{
                        background: "none",
                        border: "none",
                        fontSize: "0.78rem",
                        color: "var(--mu)",
                        cursor: "pointer",
                      }}
                    >
                      전체 해제
                    </button>
                  </div>

                  <div style={{ overflowX: "auto" }}>
                    <table
                      style={{
                        width: "100%",
                        borderCollapse: "collapse",
                        fontSize: "0.82rem",
                      }}
                    >
                      <thead>
                        <tr style={{ background: "#f7f8fa" }}>
                          <th
                            style={{
                              padding: "10px 16px",
                              textAlign: "left",
                              fontWeight: 600,
                              color: "var(--mu)",
                              fontSize: "0.74rem",
                              width: 80,
                            }}
                          >
                            항목
                          </th>

                          {comparePrograms.map((program) => (
                            <th
                              key={program.id}
                              style={{
                                padding: "10px 16px",
                                textAlign: "left",
                                fontWeight: 700,
                                color: "var(--ink)",
                              }}
                            >
                              {program.name}
                            </th>
                          ))}
                        </tr>
                      </thead>

                      <tbody>
                        {[
                          {
                            label: "국가",
                            render: (program: Program) =>
                              program.country ?? "여러 국가",
                          },
                          {
                            label: "유형",
                            render: (program: Program) =>
                              program.type ?? "-",
                          },
                          {
                            label: "설명",
                            render: (program: Program) =>
                              program.desc ||
                              program.description ||
                              program.condition_summary ||
                              "-",
                          },
                        ].map((row, rowIndex) => (
                          <tr
                            key={rowIndex}
                            style={{
                              borderTop: "1px solid var(--ln)",
                              background:
                                rowIndex % 2 === 0 ? "#fff" : "#fafbfc",
                            }}
                          >
                            <td
                              style={{
                                padding: "10px 16px",
                                fontWeight: 600,
                                color: "var(--mu)",
                                fontSize: "0.74rem",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {row.label}
                            </td>

                            {comparePrograms.map((program) => (
                              <td
                                key={program.id}
                                style={{
                                  padding: "10px 16px",
                                  color: "var(--ink)",
                                  lineHeight: 1.5,
                                }}
                              >
                                {row.render(program)}
                              </td>
                            ))}
                          </tr>
                        ))}

                        <tr style={{ borderTop: "1px solid var(--ln)" }}>
                          <td
                            style={{
                              padding: "10px 16px",
                              fontWeight: 600,
                              color: "var(--mu)",
                              fontSize: "0.74rem",
                            }}
                          >
                            공식 사이트
                          </td>

                          {comparePrograms.map((program) => {
                            const url =
                              program.official_url ||
                              program.officialUrl;

                            return (
                              <td
                                key={program.id}
                                style={{ padding: "10px 16px" }}
                              >
                                {url ? (
                                  <a
                                    href={url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                      display: "inline-flex",
                                      alignItems: "center",
                                      gap: 3,
                                      fontSize: "0.78rem",
                                      color: "var(--ac)",
                                      textDecoration: "none",
                                      fontWeight: 500,
                                    }}
                                  >
                                    바로가기
                                    <svg
                                      width="10"
                                      height="10"
                                      viewBox="0 0 24 24"
                                      fill="none"
                                      stroke="currentColor"
                                      strokeWidth="2"
                                    >
                                      <path d="M7 7h10v10M7 17L17 7" />
                                    </svg>
                                  </a>
                                ) : (
                                  "-"
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 메시지 입력창: 스크롤 영역 바깥에 고정 */}
          <div
            style={{
              padding: "20px 32px 10px",
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
                alignItems: "center",
                gap: 10,
                background: "#fff",
                border: "1px solid var(--ln)",
                borderRadius: 16,
                padding: "14px 16px",
                boxShadow: "0 4px 16px rgba(30,35,70,.05)",
              }}
            >
              <textarea
                ref={inputRef}
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
                  minHeight: 24,
                  maxHeight: 160,
                  height: 24,
                  border: "none",
                  outline: "none",
                  resize: "none",
                  overflowY: "hidden",
                  overflowX: "hidden",
                  fontSize: "0.92rem",
                  lineHeight: 1.6,
                  background: "transparent",
                  fontFamily: "inherit",
                  padding: 0,
                  boxSizing: "border-box",
                  scrollbarWidth: "thin",
                  alignSelf: "center",
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
                  cursor:
                    input.trim() && !loading ? "pointer" : "default",
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
              상담 기록은 이 브라우저에 저장되며, 안내 결과와 공식 출처를 함께 확인해 주세요.
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

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageInner />
    </Suspense>
  );
}