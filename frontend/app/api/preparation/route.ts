import { NextRequest, NextResponse } from 'next/server';
import { consultationOwner, CrossOriginConsultation } from '@/lib/consultationOwner';

export async function POST(request: NextRequest) {
  const key = process.env.INTERNAL_API_KEY;
  if (!key) return NextResponse.json({ error: '준비 계획 서버 설정이 필요합니다.' }, { status: 503 });
  try {
    await consultationOwner(request, key);
    const body = await request.json();
    const response = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8000'}/consult/preparation`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Internal-Api-Key': key },
      body: JSON.stringify(body), cache: 'no-store', signal: AbortSignal.timeout(20000),
    });
    if (!response.ok) return NextResponse.json({ error: response.status === 422 ? '프로필 입력값을 확인해 주세요.' : '준비 항목을 생성하지 못했습니다. 다시 시도해 주세요.' }, { status: [404,422].includes(response.status) ? response.status : 503 });
    return NextResponse.json(await response.json(), { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({ error: '준비 항목을 불러오지 못했습니다.' }, { status: error instanceof CrossOriginConsultation ? 403 : 503 });
  }
}
