"use client";
import Link from 'next/link';
import { useParams } from 'next/navigation';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { useCatalog } from '@/lib/useCatalog';
import { useComparison } from '@/lib/useComparison';
import { AVAILABILITY_NAMES, CATEGORY_NAMES, catalogCountry, toCompared } from '@/lib/catalog';
import { safeSource } from '@/components/ConsultationDetails';

export default function ProgramDetailPage() {
  const params = useParams<{ id: string }>();
  const { items, loading, error, retry } = useCatalog();
  const comparison = useComparison();
  const item = items.find(p => p.id === params.id || encodeURIComponent(p.id) === params.id);
  return <div style={{ minHeight: '100dvh', background: 'var(--bg)' }}>
    <Header rightLabel="공식 자료 상세" />
    <div style={{ display: 'flex', maxWidth: 1040, margin: '20px auto', padding: '0 20px' }}>
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0, padding: 24 }}>
        <Link href="/programs">← 프로그램·지원제도 목록</Link>
        {loading && <p role="status">현재 DB 자료를 불러오는 중…</p>}
        {error && <div role="alert">{error} <button onClick={retry}>다시 불러오기</button></div>}
        {!loading && !error && !item && <p role="status">현재 DB에서 이 자료를 찾지 못했습니다. 이전 숫자 링크는 목록에서 다시 선택해 주세요.</p>}
        {item && <>
          <h1 style={{ fontSize: '1.5rem', overflowWrap: 'anywhere' }}>{item.name}</h1>
          <p>{catalogCountry(item)} · {item.kind === 'support' ? '지원제도' : CATEGORY_NAMES[item.category || ''] || '프로그램'}</p>
          <p>자료 ID: {item.id}</p>
          {item.provider && <p>운영 기관: {item.provider}</p>}
          <p>확인일: {item.source_verified_at || '아래 원문별 확인일 참조'}</p>
          {item.kind === 'support' && <p>저장된 모집 상태: {AVAILABILITY_NAMES[item.availability] || '현재 접수 여부 미확인'}. 확인일 이후 접수 여부는 운영기관 공지를 확인하세요.</p>}
          <p>공식 자료와 원문 출처입니다. 개인에게 적용되는 조건·예외는 상담에서 근거와 함께 확인해 주세요.</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, margin: '20px 0' }}>
            <Link href={'/chat?program=' + encodeURIComponent(item.name)}>이 자료로 상담하기 →</Link>
            <label><input type="checkbox" checked={comparison.items.some(p => p.id === item.id)} onChange={() => comparison.toggle(toCompared(item))} /> 비교에 선택</label>
            <Link href="/compare">선택 항목 비교</Link>
          </div>
          <h2 style={{ fontSize: '1.1rem' }}>공식 출처</h2>
          {item.sources.filter(source => safeSource(source.source_url)).map((source, index) => <article key={index} style={{ border: '1px solid var(--ln)', padding: 16, borderRadius: 12, marginBottom: 12, overflowWrap: 'anywhere' }}>
            <a href={source.source_url} target="_blank" rel="noopener noreferrer">{source.title} ↗</a>
            {source.organization && <p>{source.organization}</p>}
            <p>출처 확인일: {source.verified_at || '미확인'}</p>
          </article>)}
          {item.sources.length === 0 && <p>표시할 원문 링크가 없습니다. 공식 기관 확인이 필요합니다.</p>}
        </>}
      </main>
    </div>
  </div>;
}
