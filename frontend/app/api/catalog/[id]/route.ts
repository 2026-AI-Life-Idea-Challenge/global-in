import { NextResponse } from 'next/server';
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const key = process.env.INTERNAL_API_KEY;
  if (!key) return NextResponse.json({ error: '자료 조회 서버 설정이 필요합니다.' }, { status: 503 });
  try {
    const { id } = await params;
    const response = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8000'}/consult/catalog/${encodeURIComponent(id)}`, {
      headers: { 'X-Internal-Api-Key': key }, cache: 'no-store', signal: AbortSignal.timeout(15000),
    });
    if (response.status === 404) return NextResponse.json({ error: '자료를 찾지 못했습니다.' }, { status: 404 });
    if (!response.ok) throw new Error('Catalog unavailable');
    return NextResponse.json(await response.json(), { headers: { 'Cache-Control': 'no-store' } });
  } catch { return NextResponse.json({ error: '상세 자료를 불러오지 못했습니다. 다시 시도해 주세요.' }, { status: 503 }); }
}
