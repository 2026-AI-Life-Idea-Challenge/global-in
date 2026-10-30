export const CHAT_KEY = 'global-in-chat-state';
export const RESULT_KEY = 'global-in-consult-result';
export const PROFILE_KEY = 'global-in-profile';
export const COMPARE_KEY = 'global-in-compare';

export function readSaved<T>(key: string, fallback: T): T {
  try { return JSON.parse(sessionStorage.getItem(key) || 'null') ?? fallback; } catch { return fallback; }
}
export function saveTab(key: string, value: unknown): boolean {
  try { sessionStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
}
export const COUNTRY_CODES: Record<string, string> = { 일본: 'japan', 호주: 'australia', 미국: 'usa', 독일: 'germany', 캐나다: 'canada' };
export const VISA_CODES: Record<string, string> = { 취업: 'employment', 유학: 'student', '워킹홀리데이 / 교류': 'working_holiday' };
