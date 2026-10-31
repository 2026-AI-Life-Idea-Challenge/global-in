import { NextRequest, NextResponse } from "next/server";
import { consultationOwner, CrossOriginConsultation } from '@/lib/consultationOwner';

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";
// 백엔드 응답을 최대 120초 기다리므로(아래 AbortSignal) 배포 플랫폼의 함수 실행 한도도 그만큼 확보한다.
export const maxDuration = 130;

async function consultationFailure(response: Response) {
  const body = await response.json().catch(() => ({}));
  const detail = typeof body?.detail === 'string' ? body.detail : '';
  let code = 'consultation_failed';
  let error = '상담 답변 생성 중 서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
  let retry = false;
  if (response.status === 404) {
    code = 'session_expired'; error = '상담이 만료됐습니다. 새 채팅을 시작해 주세요.';
  } else if (response.status === 409) {
    code = 'session_busy'; error = '이 상담의 이전 요청을 처리 중입니다. 잠시 후 다시 질문해 주세요.'; retry = true;
  } else if (response.status === 422) {
    code = 'invalid_input'; error = '저장된 프로필 또는 메시지의 입력 형식이 맞지 않습니다. 프로필에서 입력 내용을 확인한 뒤 다시 저장해 주세요.';
  } else if (response.status === 401 || response.status === 403) {
    code = 'server_authentication'; error = '상담 서버 인증 설정을 확인해야 합니다.';
  } else if (detail === 'consultation capacity reached') {
    code = 'capacity_reached'; error = '상담 서버가 혼잡합니다. 잠시 후 다시 시도해 주세요.'; retry = true;
  } else if (detail === 'session store temporarily unavailable') {
    code = 'session_store_unavailable'; error = '상담 기록 저장소에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.';
  }
  // Log only a controlled code; backend validation details may contain profile data.
  console.error('[/api/chat] backend failure', { status: response.status, code });
  return NextResponse.json({ error, code }, {
    status: response.status,
    ...(retry ? { headers: { 'Retry-After': '2' } } : {}),
  });
}

export async function POST(req: NextRequest) {
  const apiKey = process.env.INTERNAL_API_KEY;
  if (!apiKey) return NextResponse.json({ error: "상담 서버 설정이 필요합니다." }, { status: 503 });
  try {
    const owner = await consultationOwner(req, apiKey);
    const headers = { "Content-Type": "application/json", "X-Internal-Api-Key": apiKey, "X-Consult-Owner": owner };
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
        return consultationFailure(sessionRes);
      }
      const sessionData = await sessionRes.json();
      sessionId = sessionData.session_id;
    }
    const profile = (!existingSessionId || body.profile_pending === true) ? body.profile : undefined;

    // 백엔드로 메시지 전송
    const msgRes = await fetch(`${BACKEND}/consult/sessions/${sessionId}/messages`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message: lastUserMessage.content, profile }),
      signal: AbortSignal.timeout(120000),
    });

    if (!msgRes.ok) {
      return consultationFailure(msgRes);
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
      support_programs: data.support_programs ?? [],
      support_eligibility: data.support_eligibility ?? [],
      rag_statuses: data.rag_statuses ?? [],
      answer_sections: data.answer_sections ?? [],
    });
  } catch (err) {
    if (err instanceof CrossOriginConsultation) return NextResponse.json({ error: '다른 사이트에서 보낸 상담 요청은 허용하지 않습니다.' }, { status: 403 });
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
    const owner = await consultationOwner(req, apiKey);
    const body = await req.json();
    if (!body || !/^[a-f0-9]{32}$/.test(body.session_id || '') || !body.profile || typeof body.profile !== 'object' || Array.isArray(body.profile)) {
      return NextResponse.json({ error: '프로필과 상담 세션을 확인해 주세요.' }, { status: 400 });
    }
    const result = await fetch(`${BACKEND}/consult/sessions/${body.session_id}/profile`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-Internal-Api-Key': apiKey, 'X-Consult-Owner': owner },
      body: JSON.stringify(body.profile), signal: AbortSignal.timeout(120000),
    });
    if (!result.ok) {
      return consultationFailure(result);
    }
    const data = await result.json();
    return NextResponse.json({ ...data, content: data.reply });
  } catch (err) {
    if (err instanceof CrossOriginConsultation) return NextResponse.json({ error: '다른 사이트에서 보낸 상담 요청은 허용하지 않습니다.' }, { status: 403 });
    return NextResponse.json({ error: '재검토 서버에 연결할 수 없습니다. 다시 시도해 주세요.' }, { status: 503 });
  }
}
