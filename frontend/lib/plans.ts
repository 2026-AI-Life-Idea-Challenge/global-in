import { useMemo, useSyncExternalStore } from 'react';
import { RESULT_KEY, PROFILE_KEY, readSaved } from './consultation';
import type { ComparedItem } from './useComparison';

export const PLAN_KEY = 'global-in-plans-v1';
const event = 'global-in-plans-updated';
export type PlanItem = { id: string; program_id: string; title: string; description: string; done: boolean;
  status: string; citations?: { title: string; source_url: string }[] };
export type Plan = { target: ComparedItem; items: PlanItem[] };

export async function personalizePlan(target: ComparedItem, supplied: PlanItem[] = [], existingOnly = false) {
  const saved = readSaved<{ profile?: Record<string, unknown> }>(PROFILE_KEY, {});
  const response = await fetch('/api/preparation', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_id: target.id, profile: saved.profile || {} }) });
  const data = await response.json();
  if (!response.ok || !Array.isArray(data.items) || !data.items.length) throw new Error(data.error || '개인별 준비 항목을 찾지 못했습니다.');
  const store = read();
  const old = store.plans.find(plan => plan.target.id === target.id);
  // A deleted plan must not reappear after a late response.
  if (existingOnly && !old) return;
  const generated: PlanItem[] = data.items;
  const next = [...generated, ...supplied.filter(item => item.program_id === target.id && !generated.some(row => row.id === item.id))];
  const items = next.map(item => ({ ...item, done: old?.items.some(previous => previous.id === item.id && previous.description === item.description && previous.done) || false }));
  if (old) {
    const custom = old.items.filter(item => !item.id.startsWith('personal:') && !item.id.startsWith('dataset:') && !item.id.startsWith('source:') && !items.some(row => row.id === item.id));
    old.target = { ...old.target, ...target }; old.items = [...items, ...custom];
  } else store.plans.push({ target, items });
  write(store);
}
type Store = { version: 1; plans: Plan[] };

function valid(value: unknown): value is Plan {
  const plan = value as Plan;
  return !!plan?.target && typeof plan.target.id === 'string' && typeof plan.target.name === 'string'
    && Array.isArray(plan.items) && plan.items.every(item => item && typeof item.id === 'string' && typeof item.title === 'string');
}
function read(): Store {
  try {
    const raw = localStorage.getItem(PLAN_KEY);
    if (raw !== null) {
      const data = JSON.parse(raw);
      return { version: 1, plans: Array.isArray(data.plans) ? data.plans.filter(valid) : [] };
    }
  } catch { return { version: 1, plans: [] }; }
  // Import the existing tab checklist once. A saved empty store is intentional.
  const legacy = readSaved<{ prep_items?: PlanItem[]; programs?: { program_id: string; name: string }[] }>(RESULT_KEY, {});
  const groups = new Map<string, Plan>();
  for (const item of legacy.prep_items || []) {
    if (!item || typeof item.program_id !== 'string' || typeof item.title !== 'string') continue;
    if (!groups.has(item.program_id)) groups.set(item.program_id, { target: { id: item.program_id,
      name: legacy.programs?.find(p => p.program_id === item.program_id)?.name || '상담 준비 항목' }, items: [] });
    groups.get(item.program_id)!.items.push({ ...item, done: item.done === true });
  }
  return { version: 1, plans: [...groups.values()] };
}
function write(store: Store) {
  try { localStorage.setItem(PLAN_KEY, JSON.stringify(store)); }
  catch { throw new Error('플랜을 저장하지 못했습니다. 브라우저 저장 공간을 확인해 주세요.'); }
  window.dispatchEvent(new Event(event));
}
function subscribe(callback: () => void) {
  window.addEventListener('storage', callback); window.addEventListener(event, callback);
  return () => { window.removeEventListener('storage', callback); window.removeEventListener(event, callback); };
}
function snapshot() {
  try { return localStorage.getItem(PLAN_KEY) ?? sessionStorage.getItem(RESULT_KEY) ?? '{}'; } catch { return '{}'; }
}
export function addToPlan(target: ComparedItem, items: PlanItem[] = []) {
  if (typeof target.id !== 'string') throw new Error('프로그램 ID를 확인해 주세요.');
  const store = read();
  const incoming = items.filter(item => item.program_id === target.id);
  const fallback: PlanItem = { id: `source:${target.id}`, program_id: target.id,
    title: '공식 요건·신청 절차 확인', description: '공식 출처에서 개인에게 적용되는 조건과 현재 신청 절차를 확인하세요.',
    done: false, status: 'check_needed', citations: target.sources };
  const old = store.plans.find(plan => plan.target.id === target.id);
  if (old) {
    old.target = { ...old.target, ...target };
    const existing = new Set(old.items.map(item => item.id));
    old.items.push(...incoming.filter(item => !existing.has(item.id)).map(item => ({ ...item, done: false })));
  } else store.plans.push({ target, items: (incoming.length ? incoming : [fallback]).map(item => ({ ...item, done: false })) });
  write(store);
}
export function usePlans() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => '__server__');
  const plans = useMemo(() => raw === '__server__' ? [] : read().plans, [raw]);
  function update(targetId: string, fn: (items: PlanItem[]) => PlanItem[]) {
    const store = read();
    store.plans = store.plans.map(plan => plan.target.id === targetId ? { ...plan, items: fn(plan.items) } : plan).filter(plan => plan.items.length);
    write(store);
  }
  return { plans,
    add: addToPlan,
    toggle: (target: string, id: string) => update(target, items => items.map(item => item.id === id ? { ...item, done: !item.done } : item)),
    remove: (target: string, id: string) => update(target, items => items.filter(item => item.id !== id)),
    edit: (target: string, id: string, title: string, description: string) => update(target, items => items.map(item => item.id === id ? { ...item, title: title.trim(), description: description.trim() } : item)),
    append: (target: string, title: string) => update(target, items => [...items, { id: crypto.randomUUID(), program_id: target, title: title.trim(), description: '', done: false, status: 'todo' }]),
    clear: () => write({ version: 1, plans: [] }),
  };
}
