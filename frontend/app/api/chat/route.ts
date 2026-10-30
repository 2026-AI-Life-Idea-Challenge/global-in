import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const apiKey = process.env.INTERNAL_API_KEY;
  if (!apiKey) return NextResponse.json({ error: "상담 서버 설정이 필요합니다." }, { status: 503 });
  const headers = { "Content-Type": "application/json", "X-Internal-Api-Key": apiKey };
  try {
    const body = await req.json();
    const { messages, session_id: existingSessionId } = body as {
      messages: { role: string; content: string }[];
      session_id?: string;
    };

    if (!Array.isArray(messages) || messages.some(m => !m || typeof m.content !== "string")) {
      return NextResponse.json({ error: "메시지 형식을 확인해 주세요." }, { status: 400 });
    }
    const lastUserMessage = [...messages].reverse().find(m => m.role === "user");
    if (!lastUserMessage?.content.trim() || lastUserMessage.content.length > 2000) {
      return NextResponse.json({ error: "메시지는 1~2000자로 입력해 주세요." }, { status: 400 });
    }
    if (existingSessionId && (typeof existingSessionId !== "string" || !/^[a-f0-9]{32}$/.test(existingSessionId))) {
      return NextResponse.json({ error: "상담 세션 형식을 확인해 주세요." }, { status: 400 });
    }
    // 세션 없으면 새로 생성
    let sessionId = existingSessionId;
    if (!sessionId) {
      const sessionRes = await fetch(`${BACKEND}/consult/sessions`, {
        method: "POST",
        headers,
        signal: AbortSignal.timeout(15000),
      });
      if (!sessionRes.ok) {
        throw new Error(`세션 생성 실패: ${sessionRes.status}`);
      }
      const sessionData = await sessionRes.json();
      sessionId = sessionData.session_id;
    }
      // Apply a saved profile once when starting or retrying a failed recheck.
      if ((!existingSessionId || body.profile_pending === true) && body.profile && typeof body.profile === 'object' && !Array.isArray(body.profile)) {
        const profileRes = await fetch(`${BACKEND}/consult/sessions/${sessionId}/profile`, {
          method: 'PATCH', headers, body: JSON.stringify(body.profile), signal: AbortSignal.timeout(120000),
        });
        if (!profileRes.ok) return NextResponse.json({ error: profileRes.status === 404 ? '상담이 만료됐습니다. 새 상담을 시작해 주세요.' : '프로필 반영에 실패했습니다. 저장한 정보는 유지됩니다. 다시 시도해 주세요.' }, { status: profileRes.status });
      }

    // 백엔드로 메시지 전송
    const msgRes = await fetch(`${BACKEND}/consult/sessions/${sessionId}/messages`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message: lastUserMessage.content }),
      signal: AbortSignal.timeout(120000),
    });

    if (!msgRes.ok) {
      if (msgRes.status === 404) return NextResponse.json({ error: "상담이 만료됐습니다. 새 채팅을 시작해 주세요." }, { status: 404 });
      throw new Error(`메시지 전송 실패: ${msgRes.status}`);
    }

    const data = await msgRes.json();

    return NextResponse.json({
      content: data.reply,
      session_id: sessionId,
      stage: data.stage,
      follow_up_questions: data.follow_up_questions ?? [],
      programs: data.programs ?? [],
      profile: data.profile,
      eligibility: data.eligibility ?? [],
      prep_items: data.prep_items ?? [],
      citations: data.citations ?? [],
    });
  } catch (err) {
    console.error("[/api/chat] error:", err);
    return NextResponse.json(
      { content: "서버 연결에 문제가 생겼어요. 잠시 후 다시 시도해 주세요." },
      { status: 500 }
    );
  }
}

export async function PATCH(req: NextRequest) {
  const apiKey = process.env.INTERNAL_API_KEY;
  if (!apiKey) return NextResponse.json({ error: '상담 서버 설정이 필요합니다.' }, { status: 503 });
  try {
    const body = await req.json();
    if (!body || !/^[a-f0-9]{32}$/.test(body.session_id || '') || !body.profile || typeof body.profile !== 'object' || Array.isArray(body.profile)) {
      return NextResponse.json({ error: '프로필과 상담 세션을 확인해 주세요.' }, { status: 400 });
    }
    const result = await fetch(`${BACKEND}/consult/sessions/${body.session_id}/profile`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-Internal-Api-Key': apiKey },
      body: JSON.stringify(body.profile), signal: AbortSignal.timeout(120000),
    });
    if (!result.ok) return NextResponse.json({ error: result.status === 404 ? '상담이 만료됐습니다. 새 채팅을 시작해 주세요.' : '프로필 재검토에 실패했습니다. 입력 내용을 확인해 주세요.' }, { status: result.status });
    const data = await result.json();
    return NextResponse.json({ ...data, content: data.reply });
  } catch {
    return NextResponse.json({ error: '재검토 서버에 연결할 수 없습니다. 다시 시도해 주세요.' }, { status: 503 });
  }
}
