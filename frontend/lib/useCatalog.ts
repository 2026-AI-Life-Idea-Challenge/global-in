"use client";
import { useEffect, useState } from 'react';
import { type CatalogItem, presentCatalog } from './catalog';

export function useCatalog() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/catalog', { signal: controller.signal, cache: 'no-store' })
      .then(async response => { const data = await response.json(); if (!response.ok || !Array.isArray(data.items)) throw new Error(data.error || '자료 목록을 불러오지 못했습니다.'); return data.items; })
      .then(data => { if (!controller.signal.aborted) { setItems(presentCatalog(data)); setError(''); setLoading(false); } })
      .catch(failure => { if (!controller.signal.aborted) { setError(failure instanceof Error ? failure.message : '자료 조회 오류'); setLoading(false); } });
    return () => controller.abort();
  }, [revision]);
  return { items, loading, error, retry: () => { setLoading(true); setError(''); setRevision(value => value + 1); } };
}
