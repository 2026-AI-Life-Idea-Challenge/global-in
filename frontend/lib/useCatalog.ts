"use client";
import { useEffect, useState } from 'react';
import { type CatalogItem, requestCatalog } from './catalog';

export function useCatalog() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    requestCatalog(revision > 0)
      .then(data => { if (active) { setItems(data); setError(''); setLoading(false); } })
      .catch(failure => { if (active) { setError(failure instanceof Error ? failure.message : '자료 조회 오류'); setLoading(false); } });
    return () => { active = false; };
  }, [revision]);
  return { items, loading, error, retry: () => { setLoading(true); setError(''); setRevision(value => value + 1); } };
}
