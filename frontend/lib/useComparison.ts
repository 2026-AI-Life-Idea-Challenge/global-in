"use client";
import { useCallback, useMemo, useSyncExternalStore } from 'react';
import { COMPARE_KEY, readSaved, saveTab } from './consultation';

export type ComparedItem = { id: string | number; name: string; country?: string | null; type?: string; desc?: string; kind?: string;
  provider?: string | null; availability?: string; verifiedAt?: string | null; eligibility?: string;
  sources?: { title: string; source_url: string }[]; officialUrl?: string };
const eventName = 'global-in-comparison-updated';
function subscribe(callback: () => void) {
  window.addEventListener('storage', callback); window.addEventListener(eventName, callback);
  return () => { window.removeEventListener('storage', callback); window.removeEventListener(eventName, callback); };
}
function snapshot() { try { return sessionStorage.getItem(COMPARE_KEY) || '[]'; } catch { return '[]'; } }
function write(items: ComparedItem[]) { saveTab(COMPARE_KEY, items); window.dispatchEvent(new Event(eventName)); }
export function useComparison() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => '[]');
  const items = useMemo<ComparedItem[]>(() => {
    try { const parsed = JSON.parse(raw); return Array.isArray(parsed) ? parsed.filter(p => p && typeof p.name === 'string' && typeof p.id === 'string') : []; }
    catch { return []; }
  }, [raw]);
  const toggle = useCallback((item: ComparedItem) => { const old = readSaved<ComparedItem[]>(COMPARE_KEY, []); write(old.some(p => p.id === item.id) ? old.filter(p => p.id !== item.id) : [...old, item]); }, []);
  const clear = useCallback(() => write([]), []);
  const refresh = useCallback((current: ComparedItem[]) => {
      const byId = new Map(current.map(p => [p.id, p]));
      const old = readSaved<ComparedItem[]>(COMPARE_KEY, []);
      const updated = old.map(p => {
        const current = byId.get(p.id);
        return current ? { ...p, ...Object.fromEntries(Object.entries(current).filter(([, value]) => value !== undefined)) } : p;
      });
      if (JSON.stringify(old) !== JSON.stringify(updated)) write(updated);
    }, []);
  return { items, toggle, clear, refresh };
}
