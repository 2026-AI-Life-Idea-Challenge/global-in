"use client";
import { useSyncExternalStore } from 'react';
import Link from 'next/link';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { useCatalog } from '@/lib/useCatalog';
import { useComparison } from '@/lib/useComparison';
import { AVAILABILITY_NAMES, CATEGORY_NAMES, catalogCountry, toCompared } from '@/lib/catalog';

const filterKey = 'global-in-catalog-filters';
const filterEvent = 'global-in-catalog-filters-updated';
const defaults = { search: '', kind: 'all', country: 'all', category: 'all' };
function subscribe(callback: () => void) {
  window.addEventListener(filterEvent, callback);
  return () => window.removeEventListener(filterEvent, callback);
}
function snapshot() { try { return sessionStorage.getItem(filterKey) || '{}'; } catch { return '{}'; } }

export default function ProgramsPage() {
  const { items, loading, error, retry } = useCatalog();
  const comparison = useComparison();
  const raw = useSyncExternalStore(subscribe, snapshot, () => '{}');
  let filters = defaults;
  try { const parsed = JSON.parse(raw); filters = Object.fromEntries(Object.entries(defaults).map(([key, value]) => [key, typeof parsed?.[key] === 'string' ? parsed[key] : value])) as typeof defaults; } catch { /* Use defaults for old or corrupt state. */ }
  const { search, kind, country, category } = filters;
  const update = (patch: Partial<typeof defaults>) => {
    try { sessionStorage.setItem(filterKey, JSON.stringify({ ...filters, ...patch })); } catch { /* Storage may be disabled. */ }
    window.dispatchEvent(new Event(filterEvent));
  };
  const countries = [...new Set(items.map(catalogCountry))].sort();
  const categories = [...new Set(items.map(item => item.category).filter((value): value is string => !!value))].sort();
  const filtered = items.filter(item => (kind === 'all' || item.kind === kind) && (country === 'all' || catalogCountry(item) === country) && (category === 'all' || item.category === category)
    && (item.name + ' ' + catalogCountry(item) + ' ' + (CATEGORY_NAMES[item.category || ''] || '')).toLowerCase().includes(search.toLowerCase()));
  return <div style={{ minHeight: '100dvh', background: 'var(--bg)' }}>
    <Header rightLabel="프로그램·지원제도" />
    <div style={{ display: 'flex', maxWidth: 1040, margin: '20px auto', padding: '0 20px' }}>
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0, padding: 24 }}>
        <h1 style={{ fontSize: '1.5rem' }}>프로그램·지원제도 찾기</h1>
        <p>현재 DB에 등록된 프로그램과 공식 출처입니다. 목록 등록은 개인 자격 충족이나 접수 가능을 뜻하지 않습니다.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 18 }}>
          <input aria-label="프로그램 검색" placeholder="국가·제도·목적 검색" value={search} onChange={e => update({ search: e.target.value })} style={{ flex: 1, minWidth: 140, padding: 10 }} />
          <select aria-label="자료 유형" value={kind} onChange={e => update({ kind: e.target.value })}><option value="all">전체 유형</option><option value="program">프로그램</option><option value="support">지원제도</option></select>
          <select aria-label="목적지 국가" value={country} onChange={e => update({ country: e.target.value })}><option value="all">전체 국가</option>{countries.map(name => <option key={name}>{name}</option>)}</select>
          <select aria-label="진출 목적" value={category} onChange={e => update({ category: e.target.value })}><option value="all">전체 목적</option>{categories.map(value => <option key={value} value={value}>{CATEGORY_NAMES[value] || value}</option>)}</select>
        </div>
        {loading && <p role="status">공식 자료 목록을 불러오는 중…</p>}
        {error && <div role="alert">{error} <button onClick={retry}>다시 불러오기</button></div>}
        {!loading && !error && <p role="status">프로그램 {items.filter(p => p.kind === 'program').length}개 · 지원제도 {items.filter(p => p.kind === 'support').length}개 · 검색 결과 {filtered.length}개</p>}
        {!loading && !error && filtered.length === 0 && <p>검색 결과가 없습니다. 국가나 검색어를 바꿔 주세요.</p>}
        {filtered.map(item => <article key={item.id} style={{ border: '1px solid var(--ln)', borderRadius: 14, background: '#fff', padding: 18, marginBottom: 12 }}>
          <small>{catalogCountry(item)} · {item.kind === 'support' ? '지원제도' : CATEGORY_NAMES[item.category || ''] || '프로그램'}</small>
          <h2 style={{ fontSize: '1rem', margin: '8px 0' }}>{item.name}</h2>
          <p>원문 확인일: {item.source_verified_at || '자료별 출처 확인 필요'}{item.kind === 'support' ? ' · 저장된 모집 상태: ' + (AVAILABILITY_NAMES[item.availability] || '현재 접수 여부 미확인') : ''}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18 }}>
            <Link href={'/programs/' + encodeURIComponent(item.id)}>공식 자료 자세히 보기 →</Link>
            <label><input type="checkbox" checked={comparison.items.some(p => p.id === item.id)} onChange={() => comparison.toggle(toCompared(item))} /> {item.name} 비교</label>
          </div>
        </article>)}
        <p><Link href="/compare">선택한 {comparison.items.length}개 항목 비교 →</Link></p>
      </main>
    </div>
  </div>;
}
