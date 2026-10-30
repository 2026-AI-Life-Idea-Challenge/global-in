"use client";

import { useState, useRef, useEffect, useLayoutEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import ConsultationDetails, { type ConsultationDetailsData } from "@/components/ConsultationDetails";
import { CHAT_KEY, RESULT_KEY, PROFILE_KEY, COMPARE_KEY, readSaved, saveTab } from '@/lib/consultation';

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

const FLAGS: Record<string, string> = {
  독일: '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  일본: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  호주: '<rect width="30" height="20" fill="#00247d"/><path d="M0 0l14 9M14 0L0 9" stroke="#fff" strokeWidth="1.6"/><path d="M7 0v9M0 4.5h14" stroke="#fff" strokeWidth="3"/><path d="M7 0v9M0 4.5h14" stroke="#cf142b" strokeWidth="1.6"/>',
  미국: '<rect width="30" height="20" fill="#fff"/><rect y="0" width="30" height="1.55" fill="#b22234"/><rect y="3.1" width="30" height="1.55" fill="#b22234"/><rect y="6.2" width="30" height="1.55" fill="#b22234"/><rect y="9.3" width="30" height="1.55" fill="#b22234"/><rect y="12.4" width="30" height="1.55" fill="#b22234"/><rect y="15.5" width="30" height="1.55" fill="#b22234"/><rect y="18.6" width="30" height="1.55" fill="#b22234"/><rect width="13" height="10.8" fill="#3c3b6e"/>',
  캐나다: '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/><path d="M15 4l1.3 3 2-1-.6 4 1.7-.4-.4 1.8 1.5 1-3.5 2.4.2 2.2h-4.4l.2-2.2-3.5-2.4 1.5-1-.4-1.8 1.7.4-.6-4 2 1z" fill="#d52b1e"/>',
  Japan: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  Australia: '<rect width="30" height="20" fill="#00247d"/>',
  Germany: '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  Canada: '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/>',
};

function FlagSvg({ country, size = 20 }: { country?: string | null; size?: number }) {
  if (!country || !FLAGS[country]) return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.6">
      <circle cx="12" cy="12" r="10"/>
      <path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>
    </svg>
  );
  return (
    <svg viewBox="0 0 30 20"
      style={{ width: size, height: Math.round(size * 2 / 3), borderRadius: 2, flexShrink: 0 }}
      dangerouslySetInnerHTML={{ __html: FLAGS[country] }}
    />
  );
}

const SUGGESTIONS = [
  "일본 취업을 알아보고 싶어요",
  "여러 나라를 비교하고 싶어요",
  "국가와 목적부터 정하고 싶어요",
];

const INITIAL_MESSAGES: Message[] = [
  {
    role: "assistant",
    content: "안녕하세요! 궁금한 점을 바로 질문해도 좋고,\n원하는 방향을 함께 찾아봐도 좋아요.\n\n**이번에는 어떤 내용을 알아보고 싶으세요?**",
  },
];

function renderContent(text: string) {
  return text.split("\n").map((line, i, arr) => {
    const parts = line.split(/\*\*(.*?)\*\*/g);
    return (
      <span key={i}>
        {parts.map((part, j) => j % 2 === 1 ? <strong key={j}>{part}</strong> : part)}
        {i < arr.length - 1 && <br />}
      </span>
    );
  });
}

function ProgramCard({ program, isCompared, onToggleCompare }: {
  program: Program;
  isCompared: boolean;
  onToggleCompare: (id: string | number) => void;
}) {
  const officialUrl = program.official_url || program.officialUrl;
  const desc = program.desc || program.description || program.condition_summary || "";

  return (
    <div style={{
      background: "#fff",
      border: `1px solid ${isCompared ? "var(--ac)" : "var(--ln)"}`,
      borderRadius: 12, padding: "14px 16px",
      display: "flex", gap: 12, alignItems: "flex-start",
      transition: "border-color 0.15s",
    }}>
      <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--tn)", display: "grid", placeItems: "center", flexShrink: 0, overflow: "hidden" }}>
        <FlagSvg country={program.country} size={20} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {program.type && (
          <span style={{ fontSize: "0.68rem", fontWeight: 600, padding: "2px 7px", borderRadius: 5, background: "var(--tn)", color: "var(--ac)", display: "inline-block", marginBottom: 5 }}>
            {program.type}
          </span>
        )}
        <div style={{ fontWeight: 700, fontSize: "0.88rem", marginBottom: 3, lineHeight: 1.4 }}>{program.name}</div>
        {desc && <div style={{ fontSize: "0.78rem", color: "#555", lineHeight: 1.5, marginBottom: 8 }}>{desc}</div>}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {officialUrl && (
            <a href={officialUrl} target="_blank" rel="noopener noreferrer" style={{
              display: "inline-flex", alignItems: "center", gap: 3, fontSize: "0.78rem",
              color: "var(--ink)", fontWeight: 500, textDecoration: "none",
              border: "1px solid var(--ln)", borderRadius: 8, padding: "5px 10px", background: "#fff",
            }}>
              공식 페이지
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 7h10v10M7 17L17 7"/></svg>
            </a>
          )}
          <label style={{ display: "flex", alignItems: "center", gap: 5, cursor: "pointer", userSelect: "none" }}>
            <div onClick={() => onToggleCompare(program.id)} style={{
              width: 16, height: 16, borderRadius: 4,
              border: `1.5px solid ${isCompared ? "var(--ac)" : "#d0d3de"}`,
              background: isCompared ? "var(--ac)" : "#fff",
              display: "grid", placeItems: "center", cursor: "pointer", flexShrink: 0, transition: "all 0.15s",
            }}>
              {isCompared && <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>}
            </div>
            <span style={{ fontSize: "0.76rem", color: isCompared ? "var(--ac)" : "var(--mu)", fontWeight: isCompared ? 600 : 400 }}>비교하기</span>
          </label>
        </div>
      </div>
    </div>
  );
}

function ChatPageInner() {
  const [sessions] = useState([{ id: "new", title: "새 채팅" }]);
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<(string | number)[]>([]);
  const searchParams = useSearchParams();
  const autoSentRef = useRef(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const didMountRef = useRef(false);
  const requestVersion = useRef(0);
  const pendingRequest = useRef(false);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const saved = readSaved<{ session_id?: string; messages?: Message[]; compareIds?: (string | number)[] }>(CHAT_KEY, {});
      if (saved.session_id && /^[a-f0-9]{32}$/.test(saved.session_id) && Array.isArray(saved.messages)) {
        setSessionId(saved.session_id); setMessages(saved.messages); setCompareIds(saved.compareIds || []);
      }
      setRestored(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (restored) saveTab(CHAT_KEY, { session_id: sessionId, messages, compareIds });
  }, [restored, sessionId, messages, compareIds]);

  // 상세 페이지에서 'AI와 상담하기' 클릭 시 자동으로 해당 프로그램 상담 시작
  useEffect(() => {
    if (!restored || autoSentRef.current) return;
    const program = searchParams.get('program');
    if (!program) return;
    autoSentRef.current = true;
    const timer = setTimeout(() => {
      send(program + '에 대해 자세히 알고 싶어요. 저에게 맞는지 상담해 주세요.');
    }, 400);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restored]);


  useLayoutEffect(() => {
    const html = document.documentElement;
    const previousScrollBehavior = html.style.scrollBehavior;
    html.style.scrollbarGutter = "stable";
    html.style.scrollBehavior = "auto";
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    html.scrollTop = 0;
    document.body.scrollTop = 0;
    if (messagesContainerRef.current) messagesContainerRef.current.scrollTop = 0;
    return () => { html.style.scrollBehavior = previousScrollBehavior; };
  }, []);

  useEffect(() => {
    if (!didMountRef.current) { didMountRef.current = true; return; }
    if (messages.length <= 1) {
      if (messagesContainerRef.current) messagesContainerRef.current.scrollTop = 0;
      return;
    }
    const container = messagesContainerRef.current;
    if (container) container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  function toggleCompare(id: string | number) {
    setCompareIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  }

  const allPrograms: Program[] = [];
  messages.forEach(m => {
    if (m.programs) m.programs.forEach(p => { if (!allPrograms.find(x => x.id === p.id)) allPrograms.push(p); });
  });
  const comparePrograms = allPrograms.filter(p => compareIds.includes(p.id));
  useEffect(() => {
    if (restored) saveTab(COMPARE_KEY, allPrograms.filter(p => compareIds.includes(p.id)));
  // Programme data is refreshed together with messages.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restored, messages, compareIds]);

  async function send(text: string) {
    if (!text.trim() || pendingRequest.current || !restored) return;
    pendingRequest.current = true;
    const version = ++requestVersion.current;
    const userMsg: Message = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: updatedMessages, session_id: sessionId, profile: readSaved<{ profile?: unknown }>(PROFILE_KEY, {}).profile }),
      });
      const data = await res.json();
      if (version !== requestVersion.current) return;
      if (res.status === 404) {
        try { sessionStorage.removeItem(RESULT_KEY); } catch { /* Storage may be disabled. */ }
      }
      if (!res.ok) throw new Error(data.error || data.content || `요청 실패: ${res.status}`);
      if (data.session_id) setSessionId(data.session_id);
      const programs: Program[] = (data.programs ?? []).map((program: { program_id: string; name: string; country: string; visa_type: string; summary: string }) => ({
        id: program.program_id, name: program.name, country: program.country, type: program.visa_type, desc: program.summary,
      }));
      // Keep profile and checklist within this browser tab, not persistent browser storage.
      try { sessionStorage.setItem("global-in-consult-result", JSON.stringify(data)); } catch { /* Storage may be disabled. */ }
      setMessages(prev => [...prev, {
        role: "assistant",
        content: data.content || data.message || "죄송해요, 오류가 발생했어요.",
        programs: programs.length > 0 ? programs : undefined,
        details: data,
      }]);
    } catch (error) {
      if (version !== requestVersion.current) return;
      setMessages(prev => [...prev, { role: "assistant", content: error instanceof Error ? error.message : "연결에 문제가 생겼어요. 잠시 후 다시 시도해 주세요." }]);
    } finally {
      if (version === requestVersion.current) { setLoading(false); pendingRequest.current = false; }
    }
  }

  function startNewChat() {
    requestVersion.current += 1;
    pendingRequest.current = false;
    setMessages(INITIAL_MESSAGES);
    setSessionId(null);
    setInput("");
    setLoading(false);
    setCompareIds([]);
    try { sessionStorage.removeItem("global-in-consult-result"); } catch { /* Storage may be disabled. */ }
    saveTab(COMPARE_KEY, []);
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    if (messagesContainerRef.current) messagesContainerRef.current.scrollTop = 0;
  }

  return (
    <div style={{ height: "100dvh", overflow: "hidden", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      <div style={{ flexShrink: 0 }}>
        <Header rightLabel="맞춤 상담" />
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px", boxSizing: "border-box" }}>
        <Sidebar sessions={sessions} currentSessionId="new" onNewChat={startNewChat} />

        <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0 }}>
          <div style={{ padding: "24px 32px 0", flexShrink: 0 }}>
            <div style={{ fontSize: "0.72rem", letterSpacing: "0.14em", color: "var(--ac)", fontWeight: 600, marginBottom: 10 }}>● PERSONAL CONSULTATION</div>
            <h2 style={{ margin: "0 0 6px", fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.04em" }}>새 채팅</h2>
            <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--mu)" }}>궁금한 내용을 편하게 이야기해 주세요.</p>
            <div style={{ margin: "12px 0 4px", fontSize: "0.82rem", color: "#555", display: "flex", alignItems: "center", gap: 6 }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.7">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"/>
              </svg>
              대화에서 확인한 정보를 바탕으로 안내
            </div>
            <div style={{ fontSize: "0.78rem", color: "#bbb" }}>조건이 달라지면 대화에서 수정해 주세요.</div>
          </div>

          <hr style={{ border: "none", borderTop: "1px solid var(--ln)", margin: "20px 32px", flexShrink: 0 }} />

          <div ref={messagesContainerRef} style={{
            flex: 1, minHeight: 0, overflowY: "auto", overscrollBehavior: "contain",
            padding: "0 32px", display: "flex", flexDirection: "column", gap: 20,
          }}>
            {messages.map((msg, i) => (
              <div key={i}>
                {msg.role === "assistant" ? (
                  <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                    <div style={{ width: 36, height: 36, borderRadius: "50%", border: "1.5px solid var(--ln)", background: "#fff", display: "grid", placeItems: "center", flexShrink: 0 }}>
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--ac)" strokeWidth="1.8">
                        <circle cx="12" cy="12" r="4"/><path d="M4 9a9 9 0 0 1 14-4M20 15a9 9 0 0 1-14 4"/>
                      </svg>
                    </div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--ink)", marginBottom: 8 }}>Global-In</div>
                      <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: "4px 16px 16px 16px", padding: "16px 20px", fontSize: "0.92rem", lineHeight: 1.7, maxWidth: 520, overflowWrap: "anywhere" }}>
                        {renderContent(msg.content)}
                      </div>
                      {msg.details && <ConsultationDetails data={msg.details} />}
                      {msg.programs && msg.programs.length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div style={{ fontSize: "0.76rem", color: "var(--mu)", marginBottom: 8, fontWeight: 600, letterSpacing: "0.04em" }}>
                            ● 추천 프로그램 TOP {msg.programs.length}
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 520 }}>
                            {msg.programs.map(p => (
                              <ProgramCard key={p.id} program={p} isCompared={compareIds.includes(p.id)} onToggleCompare={toggleCompare} />
                            ))}
                          </div>
                          {compareIds.length === 1 && (
                            <div style={{ fontSize: "0.76rem", color: "var(--mu)", marginTop: 6 }}>1개 더 선택하면 비교표가 나타나요.</div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <div style={{ background: "var(--ink)", color: "#fff", borderRadius: "16px 4px 16px 16px", padding: "12px 18px", fontSize: "0.92rem", lineHeight: 1.6, maxWidth: 400, overflowWrap: "anywhere" }}>
                      {msg.content}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {messages.length === 1 && (
              <div style={{ paddingLeft: 50, display: "flex", flexWrap: "wrap", gap: 8, marginTop: -8 }}>
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => send(s)} disabled={loading} style={{ border: "1px solid var(--ln)", background: "#fff", borderRadius: 20, padding: "8px 16px", fontSize: "0.85rem", cursor: loading ? "default" : "pointer", color: "var(--ink)" }}>
                    {s}
                  </button>
                ))}
                <div style={{ width: "100%", fontSize: "0.78rem", color: "#ccc", marginTop: 6 }}>가까운 답변을 고르거나, 아래에 직접 적어 주세요.</div>
              </div>
            )}

            {loading && (
              <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <div style={{ width: 36, height: 36, borderRadius: "50%", border: "1.5px solid var(--ln)", background: "#fff", display: "grid", placeItems: "center", flexShrink: 0 }}>
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="var(--ac)" strokeWidth="1.8">
                    <circle cx="12" cy="12" r="4"/><path d="M4 9a9 9 0 0 1 14-4M20 15a9 9 0 0 1-14 4"/>
                  </svg>
                </div>
                <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: "4px 16px 16px 16px", padding: "16px 20px", color: "var(--mu)", fontSize: "0.88rem" }}>
                  답변을 준비하고 있어요…
                </div>
              </div>
            )}

            {comparePrograms.length >= 2 && (
              <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 14, overflow: "hidden", marginTop: 8 }}>
                <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--ln)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: 700, fontSize: "0.92rem" }}>
                    비교 <span style={{ fontSize: "0.78rem", fontWeight: 400, color: "var(--mu)", marginLeft: 8 }}>{comparePrograms.length}개 선택됨</span> <a href="/compare">비교 화면 열기</a>
                  </div>
                  <button onClick={() => setCompareIds([])} style={{ background: "none", border: "none", fontSize: "0.78rem", color: "var(--mu)", cursor: "pointer" }}>전체 해제</button>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                    <thead>
                      <tr style={{ background: "#f7f8fa" }}>
                        <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600, color: "var(--mu)", fontSize: "0.74rem", width: 80 }}>항목</th>
                        {comparePrograms.map(p => (
                          <th key={p.id} style={{ padding: "10px 16px", textAlign: "left", fontWeight: 700, color: "var(--ink)" }}>{p.name}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { label: "국가", render: (p: Program) => p.country ?? "여러 국가" },
                        { label: "유형", render: (p: Program) => p.type ?? "-" },
                        { label: "설명", render: (p: Program) => p.desc || p.description || p.condition_summary || "-" },
                      ].map((row, ri) => (
                        <tr key={ri} style={{ borderTop: "1px solid var(--ln)", background: ri % 2 === 0 ? "#fff" : "#fafbfc" }}>
                          <td style={{ padding: "10px 16px", fontWeight: 600, color: "var(--mu)", fontSize: "0.74rem", whiteSpace: "nowrap" }}>{row.label}</td>
                          {comparePrograms.map(p => <td key={p.id} style={{ padding: "10px 16px", color: "var(--ink)", lineHeight: 1.5 }}>{row.render(p)}</td>)}
                        </tr>
                      ))}
                      <tr style={{ borderTop: "1px solid var(--ln)" }}>
                        <td style={{ padding: "10px 16px", fontWeight: 600, color: "var(--mu)", fontSize: "0.74rem" }}>공식 사이트</td>
                        {comparePrograms.map(p => {
                          const url = p.official_url || p.officialUrl;
                          return (
                            <td key={p.id} style={{ padding: "10px 16px" }}>
                              {url ? (
                                <a href={url} target="_blank" rel="noopener noreferrer"
                                  style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: "0.78rem", color: "var(--ac)", textDecoration: "none", fontWeight: 500 }}>
                                  바로가기 <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 7h10v10M7 17L17 7"/></svg>
                                </a>
                              ) : "-"}
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

          <div style={{ padding: "20px 32px 16px", flexShrink: 0 }}>
            <form onSubmit={e => { e.preventDefault(); send(input); }} style={{
              display: "flex", alignItems: "flex-end", gap: 10,
              background: "#fff", border: "1px solid var(--ln)", borderRadius: 16,
              padding: "14px 16px", boxShadow: "0 4px 16px rgba(30,35,70,.05)",
            }}>
              <textarea
                value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
                placeholder="편하게 이야기해 주세요." rows={1}
                style={{ flex: 1, minWidth: 0, border: "none", outline: "none", resize: "none", fontSize: "0.92rem", lineHeight: 1.6, background: "transparent", fontFamily: "inherit" }}
              />
              <button type="submit" disabled={!input.trim() || loading} aria-label="메시지 보내기" style={{
                width: 36, height: 36, borderRadius: "50%",
                background: input.trim() ? "var(--ink)" : "#e0e2ea",
                border: "none", display: "grid", placeItems: "center", flexShrink: 0,
                cursor: input.trim() && !loading ? "pointer" : "default", transition: "background 0.15s",
              }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
              </button>
            </form>
            <div style={{ fontSize: "0.75rem", color: "#ccc", textAlign: "center", marginTop: 10 }}>
              화면 시안 · 채팅은 현재 화면을 닫기 전까지 유지돼요. 실제 AI 상담은 연결 전이에요.
            </div>
          </div>
        </main>
      </div>

      <footer style={{ display: "flex", justifyContent: "space-between", maxWidth: 1040, margin: "0 auto", width: "100%", boxSizing: "border-box", padding: "20px 20px", fontSize: "0.78rem", color: "#ccc", flexShrink: 0 }}>
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
