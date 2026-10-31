import presentation from './catalogPresentation.json';
const labels: Record<string, string[]> = presentation;
export function programName(id: string, fallback: string) { return labels[id]?.[0] || fallback; }
export function programDescription(id: string, fallback = '') { return labels[id]?.[1] || fallback; }

export type CatalogItem = {
  id: string; kind: 'program' | 'support'; name: string; country: string | null;
  category: string | null; provider: string | null; destination_countries: string[];
  availability: string; source_verified_at: string | null; release_id: string | null;
  sources: { title: string; source_url: string; organization?: string | null; verified_at?: string | null }[];
  description?: string; original_name?: string;
};
export const COUNTRY_NAMES: Record<string, string> = { japan: '일본', australia: '호주', usa: '미국', germany: '독일', canada: '캐나다', multi_country: '여러 국가', KR: '한국', JP: '일본', AU: '호주', US: '미국', DE: '독일', CA: '캐나다' };
export const CATEGORY_NAMES: Record<string, string> = { study: '유학', student: '유학', employment: '취업', working_holiday: '워킹홀리데이' };
export const AVAILABILITY_NAMES: Record<string, string> = { OPEN: '접수 중으로 기록됨', CLOSED: '접수 종료로 기록됨', UPCOMING: '접수 예정으로 기록됨', ROLLING: '상시 접수로 기록됨', UNKNOWN: '현재 접수 여부 미확인' };
export function catalogCountry(item: CatalogItem): string {
  return item.kind === 'support' ? item.destination_countries.map(code => COUNTRY_NAMES[code] || code).join(', ') || '적용 국가 확인 필요' : COUNTRY_NAMES[item.country || ''] || '여러 국가';
}
export function toCompared(item: CatalogItem) {
  return { id: item.id, name: /[가-힣]/.test(item.name) ? item.name : programName(item.id, item.name), country: catalogCountry(item), type: item.kind === 'support' ? '지원제도' : CATEGORY_NAMES[item.category || ''] || '프로그램',
    desc: programDescription(item.id, item.description || item.name), kind: item.kind,
    provider: item.provider || item.sources.find(source => source.organization)?.organization, availability: item.kind === 'support' ? item.availability : undefined,
    verifiedAt: item.source_verified_at, sources: item.sources, officialUrl: item.sources[0]?.source_url };
}


export function presentCatalog(items: CatalogItem[]): CatalogItem[] {
  return items.map(item => {
    const westSupport = item.id === 'US:US-WEST-01' ? items.find(row => row.id === 'KR_US_WEST') : undefined;
    const sources = westSupport ? [
      { title: '프로그램 소개', source_url: 'https://www.niied.go.kr/web/niied/contents/niied_iee_west', organization: '국립국제교육원' },
      ...westSupport.sources.map(source => ({ ...source, title: '모집·지원 안내' })),
    ] : item.sources;
    return { ...item, original_name: item.name, name: programName(item.id, item.name),
      description: programDescription(item.id, item.description || item.name), sources,
      source_verified_at: item.source_verified_at || westSupport?.source_verified_at || sources.find(source => source.verified_at)?.verified_at || null };
  });
}

let sharedCatalog: Promise<CatalogItem[]> | null = null;

/** 한 화면의 여러 카드가 카탈로그를 각자 받지 않도록 요청 하나를 공유한다. refresh는 다시 시도할 때만 쓴다. */
export function requestCatalog(refresh = false): Promise<CatalogItem[]> {
  if (sharedCatalog && !refresh) return sharedCatalog;
  const request = fetch('/api/catalog', { cache: 'no-store' }).then(async response => {
    const data = await response.json();
    if (!response.ok || !Array.isArray(data.items)) throw new Error(data.error || '자료 목록을 불러오지 못했습니다.');
    return presentCatalog(data.items);
  });
  sharedCatalog = request;
  request.catch(() => { if (sharedCatalog === request) sharedCatalog = null; });
  return request;
}

export function groupedCatalog(items: CatalogItem[]): CatalogItem[] {
  return items.filter(item => {
    const match = item.id.match(/^(AU:subclass_(?:417|462)_)(second|third)$/);
    if (match && items.some(row => row.id === match[1] + 'first')) return false;
    return item.id !== 'KR_US_WEST' || !items.some(row => row.id === 'US:US-WEST-01');
  }).map(item => {
    const family = item.id.match(/^AU:subclass_(417|462)_first$/)?.[1];
    return family ? { ...item, name: `호주 ${family === '417' ? '워킹홀리데이' : '워크앤홀리데이'} 비자 ${family}`,
      description: `호주 ${family}의 첫 신청·2차·3차 경로를 한곳에서 확인하고 단계별 요건을 비교할 수 있습니다.` } : item;
  });
}
