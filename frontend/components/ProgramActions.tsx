"use client";
import Link from 'next/link';
import { useState } from 'react';
import { usePlans, personalizePlan, type PlanItem } from '@/lib/plans';
import type { ComparedItem } from '@/lib/useComparison';
import { useComparison } from '@/lib/useComparison';

export default function ProgramActions({ item, prepItems = [], showDetails = true, showCompare = false }: { item: ComparedItem; prepItems?: PlanItem[]; showDetails?: boolean; showCompare?: boolean }) {
  const { plans } = usePlans();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const comparison = useComparison();
  const included = plans.some(plan => plan.target.id === item.id);
  const buttonStyle = { border: '1px solid var(--ln)', background: '#fff', borderRadius: 10, padding: '8px 14px', fontSize: '0.82rem', color: 'var(--ink)', fontWeight: 500, cursor: 'pointer' };
  return <>
    {showCompare && <label><input type="checkbox" aria-label={`${item.name} 비교하기`} checked={comparison.items.some(p => p.id === item.id)} onChange={() => comparison.toggle(item)} /> 비교하기</label>}
    <button type="button" disabled={busy} aria-label={`${item.name} 플랜에 추가`} style={buttonStyle} onClick={async () => {
      setBusy(true);
      try { await personalizePlan(item, prepItems); setNotice('개인별 준비 항목을 플랜에 저장했습니다.'); } catch (error) { setNotice(error instanceof Error ? error.message : '저장 실패'); }
      finally { setBusy(false); }
    }}>{busy ? '준비 항목 생성 중…' : included ? '플랜 다시 검토' : '플랜에 넣기'}</button>
    {showDetails && <Link href={'/programs/' + encodeURIComponent(String(item.id))} style={buttonStyle}>자세히 보기</Link>}
    {notice && <span role="status">{notice}</span>}
  </>;
}
