import { NextResponse } from 'next/server';

export async function GET() {
  const key = process.env.INTERNAL_API_KEY;
  if (!key) return NextResponse.json({ error: '자료 조회 서버 설정이 필요합니다.' }, { status: 503 });
  try {
    const result = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8000'}/consult/catalog`, {
      headers: { 'X-Internal-Api-Key': key }, cache: 'no-store', signal: AbortSignal.timeout(15000),
    });
    if (!result.ok) throw new Error('Catalog unavailable');
    return NextResponse.json(await result.json(), { headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return NextResponse.json({ error: '공식 자료 목록을 불러오지 못했습니다. 다시 시도해 주세요.' }, { status: 503 });
  }
}
