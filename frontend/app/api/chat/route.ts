import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://localhost:8000";
const API_KEY = "GloBalINAIChallENGEKeYOFSeCurEOutSidErS4";

const headers = {
  "Content-Type": "application/json",
  "X-Internal-Api-Key": API_KEY,
};

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages, session_id: existingSessionId } = body as {
      messages: { role: string; content: string }[];
      session_id?: string;
    };

    // 세션 없으면 새로 생성
    let sessionId = existingSessionId;
    if (!sessionId) {
      const sessionRes = await fetch(`${BACKEND}/consult/sessions`, {
        method: "POST",
        headers,
      });
      if (!sessionRes.ok) {
        throw new Error(`세션 생성 실패: ${sessionRes.status}`);
      }
      const sessionData = await sessionRes.json();
      sessionId = sessionData.session_id;
    }

    // 마지막 유저 메시지 추출
    const lastUserMessage = [...messages].reverse().find(m => m.role === "user");
    if (!lastUserMessage) {
      return NextResponse.json({ error: "유저 메시지 없음" }, { status: 400 });
    }

    // 백엔드로 메시지 전송
    const msgRes = await fetch(`${BACKEND}/consult/sessions/${sessionId}/messages`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message: lastUserMessage.content }),
    });

    if (!msgRes.ok) {
      throw new Error(`메시지 전송 실패: ${msgRes.status}`);
    }

    const data = await msgRes.json();

    return NextResponse.json({
      content: data.reply,
      session_id: sessionId,
      stage: data.stage,
      follow_up_questions: data.follow_up_questions ?? [],
      programs: data.programs ?? [],
    });
  } catch (err) {
    console.error("[/api/chat] error:", err);
    return NextResponse.json(
      { content: "서버 연결에 문제가 생겼어요. 잠시 후 다시 시도해 주세요." },
      { status: 500 }
    );
  }
}
