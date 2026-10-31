import { AVAILABILITY_NAMES } from './catalog';
import type { ComparedItem } from './useComparison';
export const comparisonRows: { label: string; value: (item: ComparedItem) => string }[] = [
  { label: '국가', value: p => p.country || '적용 국가 확인 필요' },
  { label: '자료 유형', value: p => p.kind === 'support' ? '지원제도' : '프로그램' },
  { label: '진출 목적·유형', value: p => p.type || '확인 필요' },
  { label: '운영 기관', value: p => p.provider || '공식 출처 확인' },
  { label: '설명', value: p => p.desc || '추가 확인 필요' },
  { label: '자격 검토', value: p => p.eligibility || '개인 조건 검토 필요' },
  { label: '저장된 모집 상태', value: p => p.availability ? AVAILABILITY_NAMES[p.availability] || '확인 필요' : '현재 접수 여부는 공식 기관 확인' },
  { label: '출처 확인일', value: p => p.verifiedAt || '미확인' },
];
