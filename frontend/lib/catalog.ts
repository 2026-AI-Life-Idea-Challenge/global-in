export type CatalogItem = {
  id: string; kind: 'program' | 'support'; name: string; country: string | null;
  category: string | null; provider: string | null; destination_countries: string[];
  availability: string; source_verified_at: string | null; release_id: string | null;
  sources: { title: string; source_url: string; organization?: string | null; verified_at?: string | null }[];
};
export const COUNTRY_NAMES: Record<string, string> = { japan: '일본', australia: '호주', usa: '미국', germany: '독일', canada: '캐나다', multi_country: '여러 국가', KR: '한국', JP: '일본', AU: '호주', US: '미국', DE: '독일', CA: '캐나다' };
export const CATEGORY_NAMES: Record<string, string> = { study: '유학', student: '유학', employment: '취업', working_holiday: '워킹홀리데이' };
export const AVAILABILITY_NAMES: Record<string, string> = { OPEN: '접수 중으로 기록됨', CLOSED: '접수 종료로 기록됨', UPCOMING: '접수 예정으로 기록됨', ROLLING: '상시 접수로 기록됨', UNKNOWN: '현재 접수 여부 미확인' };
export function catalogCountry(item: CatalogItem): string {
  return item.kind === 'support' ? item.destination_countries.map(code => COUNTRY_NAMES[code] || code).join(', ') || '적용 국가 확인 필요' : COUNTRY_NAMES[item.country || ''] || '여러 국가';
}
export function toCompared(item: CatalogItem) {
  return { id: item.id, name: item.name, country: catalogCountry(item), type: item.kind === 'support' ? '지원제도' : CATEGORY_NAMES[item.category || ''] || '프로그램',
    desc: '공식 원문과 개인별 적용 조건을 추가 확인하세요.', kind: item.kind,
    provider: item.provider || item.sources.find(source => source.organization)?.organization, availability: item.kind === 'support' ? item.availability : undefined,
    verifiedAt: item.source_verified_at, sources: item.sources, officialUrl: item.sources[0]?.source_url };
}
