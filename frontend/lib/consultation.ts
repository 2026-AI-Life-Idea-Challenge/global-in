export const CHAT_KEY = 'global-in-chat-state';
export const RESULT_KEY = 'global-in-consult-result';
export const PROFILE_KEY = 'global-in-profile';
export const COMPARE_KEY = 'global-in-compare';

/** End consultation-derived state while keeping the explicitly saved profile. */
export function expireConsultation(): void {
  for (const key of [CHAT_KEY, RESULT_KEY, COMPARE_KEY]) {
    try { sessionStorage.removeItem(key); } catch { /* Storage may be disabled. */ }
  }
}

export function latestPrograms<T extends { id: string | number }>(messages: { programs?: T[] }[]): T[] {
  const byId = new Map<string | number, T>();
  for (const message of messages) for (const program of message.programs || []) byId.set(program.id, program);
  return [...byId.values()];
}

/** Keep conversation text, not results assessed against the previous profile. */
export function invalidateResults<T extends { programs?: unknown; details?: unknown }>(messages: T[]): T[] {
  return messages.map(message => ({ ...message, programs: undefined, details: undefined }));
}

export function readSaved<T>(key: string, fallback: T): T {
  try { return JSON.parse(sessionStorage.getItem(key) || 'null') ?? fallback; } catch { return fallback; }
}
export function saveTab(key: string, value: unknown): boolean {
  try { sessionStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
}
export const COUNTRY_CODES: Record<string, string> = { 일본: 'japan', 호주: 'australia', 미국: 'usa', 독일: 'germany', 캐나다: 'canada' };
export const VISA_CODES: Record<string, string> = { 취업: 'employment', 유학: 'student', '워킹홀리데이 / 교류': 'working_holiday' };
