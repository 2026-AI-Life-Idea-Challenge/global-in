"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Header from "../../components/Header";
import { CHAT_KEY, RESULT_KEY, PROFILE_KEY, COUNTRY_CODES, VISA_CODES, readSaved, saveTab } from '@/lib/consultation';

const COUNTRIES = [
  { flag: "🇯🇵", label: "일본" },
  { flag: "🇦🇺", label: "호주" },
  { flag: "🇺🇸", label: "미국" },
  { flag: "🇩🇪", label: "독일" },
  { flag: "🇨🇦", label: "캐나다" },
];

const PURPOSES = [
  { icon: "🧳", label: "취업" },
  { icon: "🎓", label: "유학" },
  { icon: "✈️", label: "워킹홀리데이 / 교류" },
];

const EDUCATIONS = ["고등학교", "전문대학", "대학교", "대학원 이상"];
const EDU_STATUS = ["재학", "휴학", "졸업", "중퇴"];

export default function ProfilePage() {
  const router = useRouter();
  const [nationality, setNationality] = useState("");
  const [age, setAge] = useState(""); // Stores an explicit date of birth; never derived from age.
  const [residence, setResidence] = useState("");
  const [education, setEducation] = useState("");
  const [eduStatus, setEduStatus] = useState("");
  const [major, setMajor] = useState("");
  const [career, setCareer] = useState("");
  const [careerDuration, setCareerDuration] = useState("");
  const [languages, setLanguages] = useState("");
  const [certs, setCerts] = useState("");
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [undecidedCountry, setUndecidedCountry] = useState(true);
  const [selectedPurposes, setSelectedPurposes] = useState<string[]>([]);
  const [undecidedPurpose, setUndecidedPurpose] = useState(true);
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const saved = readSaved<{ form?: Record<string, unknown> }>(PROFILE_KEY, {}).form;
      if (!saved) return;
      const fields = { nationality: setNationality, age: setAge, residence: setResidence, education: setEducation,
        eduStatus: setEduStatus, major: setMajor, career: setCareer, careerDuration: setCareerDuration, languages: setLanguages, certs: setCerts };
      Object.entries(fields).forEach(([key, setter]) => { if (typeof saved[key] === 'string') setter(saved[key] as string); });
      if (Array.isArray(saved.selectedCountries)) setSelectedCountries(saved.selectedCountries as string[]);
      if (Array.isArray(saved.selectedPurposes)) setSelectedPurposes(saved.selectedPurposes as string[]);
      setUndecidedCountry(saved.undecidedCountry !== false);
      setUndecidedPurpose(saved.undecidedPurpose !== false);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function saveProfile(goToChat = false) {
    if (saving) return;
    const aliases: Record<string, string> = { 대한민국: 'KR', 한국: 'KR', 미국: 'US', 일본: 'JP', 호주: 'AU', 독일: 'DE', 캐나다: 'CA' };
    const nationalities = nationality.split(/[,/]+/).map(value => aliases[value.trim()] || value.trim().toUpperCase()).filter(Boolean);
    if (!nationalities.length || nationalities.some(value => !/^[A-Z]{2}$/.test(value))) {
      setNotice('국적은 한국 또는 KR처럼 입력하세요. 복수 국적은 쉼표로 구분하세요.'); return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(age) || age > new Date().toLocaleDateString('sv-SE') || Number(age.slice(0, 4)) < new Date().getFullYear() - 80) {
      setNotice('만 나이 대신 정확한 생년월일을 입력해 주세요.'); return;
    }
    const countries = undecidedCountry ? [] : selectedCountries;
    const purposes = undecidedPurpose ? [] : selectedPurposes;
    const context = [residence && `현재 거주: ${residence}`, education && `학력: ${education} ${eduStatus}`, major && `전공: ${major}`,
      career && `경력: ${career} ${careerDuration}`, languages && `언어: ${languages}`, certs && `자격: ${certs}`,
      countries.length && `희망 국가: ${countries.join(', ')}`, purposes.length && `목적: ${purposes.join(', ')}`].filter(Boolean).join('; ');
    if (context.length > 500) { setNotice('학력·경력 등 부가 정보를 합계 500자 이내로 줄여 주세요.'); return; }
    const profile = { date_of_birth: age, nationalities, target_country: countries.length === 1 ? COUNTRY_CODES[countries[0]] : null,
      target_visa_type: purposes.length === 1 ? VISA_CODES[purposes[0]] : null, purpose: context || null };
    const form = { nationality, age, residence, education, eduStatus, major, career, careerDuration, languages, certs,
      selectedCountries, selectedPurposes, undecidedCountry, undecidedPurpose };
    setSaving(true); setNotice('');
    try {
      const chat = readSaved<{ session_id?: string; messages?: unknown[] }>(CHAT_KEY, {});
      if (chat.session_id) {
        const response = await fetch('/api/chat', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: chat.session_id, profile }) });
        const result = await response.json();
        if (!response.ok) {
          if (response.status === 404) sessionStorage.removeItem(CHAT_KEY);
          throw new Error(result.error || '재검토에 실패했습니다.');
        }
        saveTab(RESULT_KEY, result);
        saveTab(CHAT_KEY, { ...chat, messages: [...(chat.messages || []), { role: 'assistant', content: result.content, details: result,
          programs: (result.programs || []).map((p: { program_id: string; name: string; country: string; visa_type: string; summary: string }) => ({ id: p.program_id, name: p.name, country: p.country, type: p.visa_type, desc: p.summary })) }], compareIds: [] });
      }
      if (!saveTab(PROFILE_KEY, { form, profile })) throw new Error('브라우저 저장소를 사용할 수 없습니다. 저장 설정을 확인해 주세요.');
      sessionStorage.removeItem('global-in-compare');
      setNotice(chat.session_id ? '프로필을 저장하고 재검토 결과를 갱신했습니다.' : '이 탭에 프로필을 저장했습니다. 다음 상담에 반영됩니다.');
      if (goToChat) router.push('/chat');
    } catch (error) { setNotice(error instanceof Error ? error.message : '프로필을 저장하지 못했습니다.'); }
    finally { setSaving(false); }
  }

  const toggleCountry = (label: string) => {
    setUndecidedCountry(false);
    setSelectedCountries((prev) =>
      prev.includes(label) ? prev.filter((c) => c !== label) : [...prev, label]
    );
  };

  const togglePurpose = (label: string) => {
    setUndecidedPurpose(false);
    setSelectedPurposes((prev) =>
      prev.includes(label) ? prev.filter((p) => p !== label) : [...prev, label]
    );
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      <Header rightLabel="내 프로필" />

      <main style={{ maxWidth: 860, margin: "0 auto", width: "100%", padding: "24px 16px", flex: 1 }}>
        <button
          onClick={() => router.back()}
          style={{
            display: "flex", alignItems: "center", gap: 6, fontSize: "0.78rem",
            color: "var(--mu)", background: "none", border: "none", cursor: "pointer",
            padding: "4px 0", marginBottom: 20,
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
          처음으로 돌아가기
        </button>

        <p style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.16em", color: "#ccc", marginBottom: 4 }}>● MY PROFILE</p>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 800, margin: "0 0 4px", color: "var(--ink)" }}>내 프로필</h2>
        <p style={{ fontSize: "0.78rem", color: "var(--mu)", marginBottom: 24 }}>상담에 사용할 기본 정보와 학력·경력·언어 정보를 관리합니다.</p>

        {/* 기본 정보 */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <h3 style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--ink)", margin: 0 }}>기본 정보</h3>
            <span style={{ fontSize: "0.65rem", color: "#ccc" }}>* 필수 입력</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            {[
              { label: "국적 *", value: nationality, onChange: setNationality, placeholder: "선택 또는 입력" },
              { label: "생년월일 *", value: age, onChange: setAge, placeholder: "YYYY-MM-DD" },
              { label: "현재 거주 국가 *", value: residence, onChange: setResidence, placeholder: "선택 또는 입력" },
            ].map(({ label, value, onChange, placeholder }) => (
              <div key={label}>
                <label style={{ fontSize: "0.75rem", color: "var(--mu)", display: "block", marginBottom: 6 }}>{label}</label>
                <input
                  type={label === '생년월일 *' ? 'date' : 'text'} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
                  style={{ width: "100%", border: "1px solid var(--ln)", borderRadius: 12, padding: "10px 12px", fontSize: "0.88rem", outline: "none", boxSizing: "border-box" }}
                />
              </div>
            ))}
          </div>
        </section>

        {/* 학력 */}
        <section style={{ marginBottom: 32, borderTop: "1px solid var(--ln)", paddingTop: 24 }}>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--ink)", marginBottom: 16 }}>
            학력 <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "#ccc" }}>선택 입력</span>
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--mu)", display: "block", marginBottom: 6 }}>최종 학력</label>
              <select value={education} onChange={e => setEducation(e.target.value)}
                style={{ width: "100%", border: "1px solid var(--ln)", borderRadius: 12, padding: "10px 12px", fontSize: "0.88rem", outline: "none", background: "#fff", boxSizing: "border-box" }}>
                <option value="">선택</option>
                {EDUCATIONS.map(e => <option key={e}>{e}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--mu)", display: "block", marginBottom: 6 }}>학적 상태</label>
              <select value={eduStatus} onChange={e => setEduStatus(e.target.value)}
                style={{ width: "100%", border: "1px solid var(--ln)", borderRadius: 12, padding: "10px 12px", fontSize: "0.88rem", outline: "none", background: "#fff", boxSizing: "border-box" }}>
                <option value="">선택</option>
                {EDU_STATUS.map(e => <option key={e}>{e}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--mu)", display: "block", marginBottom: 6 }}>전공</label>
              <input value={major} onChange={e => setMajor(e.target.value)} placeholder="예: 컴퓨터공학"
                style={{ width: "100%", border: "1px solid var(--ln)", borderRadius: 12, padding: "10px 12px", fontSize: "0.88rem", outline: "none", boxSizing: "border-box" }} />
            </div>
          </div>
        </section>

        {/* 경력 */}
        <section style={{ marginBottom: 32, borderTop: "1px solid var(--ln)", paddingTop: 24 }}>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--ink)", marginBottom: 16 }}>
            경력 <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "#ccc" }}>선택 입력</span>
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--mu)", display: "block", marginBottom: 6 }}>직무·경력 분야</label>
              <input value={career} onChange={e => setCareer(e.target.value)} placeholder="예: 웹 개발"
                style={{ width: "100%", border: "1px solid var(--ln)", borderRadius: 12, padding: "10px 12px", fontSize: "0.88rem", outline: "none", boxSizing: "border-box" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--mu)", display: "block", marginBottom: 6 }}>경력 기간</label>
              <input value={careerDuration} onChange={e => setCareerDuration(e.target.value)} placeholder="예: 2년 6개월 / 경력 없음"
                style={{ width: "100%", border: "1px solid var(--ln)", borderRadius: 12, padding: "10px 12px", fontSize: "0.88rem", outline: "none", boxSizing: "border-box" }} />
            </div>
          </div>
        </section>

        {/* 언어 */}
        <section style={{ marginBottom: 32, borderTop: "1px solid var(--ln)", paddingTop: 24 }}>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--ink)", marginBottom: 16 }}>
            언어 <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "#ccc" }}>선택 입력</span>
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--mu)", display: "block", marginBottom: 6 }}>사용 언어</label>
              <input value={languages} onChange={e => setLanguages(e.target.value)} placeholder="예: 한국어, 영어, 일본어"
                style={{ width: "100%", border: "1px solid var(--ln)", borderRadius: 12, padding: "10px 12px", fontSize: "0.88rem", outline: "none", boxSizing: "border-box" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--mu)", display: "block", marginBottom: 6 }}>어학 시험·자격</label>
              <input value={certs} onChange={e => setCerts(e.target.value)} placeholder="예: IELTS 6.5, JLPT N2"
                style={{ width: "100%", border: "1px solid var(--ln)", borderRadius: 12, padding: "10px 12px", fontSize: "0.88rem", outline: "none", boxSizing: "border-box" }} />
            </div>
          </div>
        </section>

        {/* 관심 국가 */}
        <section style={{ marginBottom: 32, borderTop: "1px solid var(--ln)", paddingTop: 24 }}>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--ink)", marginBottom: 16 }}>
            관심 국가 <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "#ccc" }}>선택 입력 · 복수 선택 가능</span>
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
            {COUNTRIES.map(({ flag, label }) => (
              <button key={label} onClick={() => toggleCountry(label)}
                style={{
                  position: "relative", border: `1px solid ${selectedCountries.includes(label) ? "#6b7080" : "var(--ln)"}`,
                  borderRadius: 16, padding: "16px 8px", display: "flex", flexDirection: "column",
                  alignItems: "center", gap: 8, background: selectedCountries.includes(label) ? "#f5f5f7" : "#fff", cursor: "pointer",
                }}>
                <div style={{
                  position: "absolute", top: 8, right: 8, width: 14, height: 14, borderRadius: 4,
                  border: `1px solid ${selectedCountries.includes(label) ? "var(--ink)" : "var(--ln)"}`,
                  background: selectedCountries.includes(label) ? "var(--ink)" : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {selectedCountries.includes(label) && <span style={{ color: "#fff", fontSize: 8 }}>✓</span>}
                </div>
                <span style={{ fontSize: "1.5rem" }}>{flag}</span>
                <span style={{ fontSize: "0.75rem", color: "var(--ink)" }}>{label}</span>
              </button>
            ))}
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, cursor: "pointer" }}>
            <input type="checkbox" checked={undecidedCountry} onChange={e => setUndecidedCountry(e.target.checked)} />
            <span style={{ fontSize: "0.78rem", color: "var(--mu)" }}>미정</span>
          </label>
        </section>

        {/* 진출 목적 */}
        <section style={{ marginBottom: 32, borderTop: "1px solid var(--ln)", paddingTop: 24 }}>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--ink)", marginBottom: 16 }}>
            진출 목적 <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "#ccc" }}>선택 입력 · 복수 선택 가능</span>
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
            {PURPOSES.map(({ icon, label }) => (
              <button key={label} onClick={() => togglePurpose(label)}
                style={{
                  position: "relative", border: `1px solid ${selectedPurposes.includes(label) ? "#6b7080" : "var(--ln)"}`,
                  borderRadius: 16, padding: "20px 8px", display: "flex", flexDirection: "column",
                  alignItems: "center", gap: 8, background: selectedPurposes.includes(label) ? "#f5f5f7" : "#fff", cursor: "pointer",
                }}>
                <div style={{
                  position: "absolute", top: 8, right: 8, width: 14, height: 14, borderRadius: 4,
                  border: `1px solid ${selectedPurposes.includes(label) ? "var(--ink)" : "var(--ln)"}`,
                  background: selectedPurposes.includes(label) ? "var(--ink)" : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {selectedPurposes.includes(label) && <span style={{ color: "#fff", fontSize: 8 }}>✓</span>}
                </div>
                <span style={{ fontSize: "1.25rem" }}>{icon}</span>
                <span style={{ fontSize: "0.78rem", color: "var(--ink)" }}>{label}</span>
              </button>
            ))}
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, cursor: "pointer" }}>
            <input type="checkbox" checked={undecidedPurpose} onChange={e => setUndecidedPurpose(e.target.checked)} />
            <span style={{ fontSize: "0.78rem", color: "var(--mu)" }}>미정</span>
          </label>
        </section>

        <p style={{ fontSize: "0.75rem", color: "#ccc", marginBottom: 24 }}>선택 항목은 나중에 추가하거나 수정할 수 있습니다.</p>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, paddingBottom: 32 }}>
          <button disabled={saving} onClick={() => saveProfile()} style={{ border: "1px solid var(--ln)", color: "var(--ink)", padding: "12px 24px", borderRadius: 12, fontSize: "0.88rem", fontWeight: 500, background: "#fff", cursor: "pointer" }}>
            프로필 저장하기
          </button>
          <button disabled={saving} onClick={() => saveProfile(true)}
            style={{ background: "var(--ink)", color: "#fff", padding: "12px 24px", borderRadius: 12, fontSize: "0.88rem", fontWeight: 600, border: "none", cursor: "pointer" }}>
            이 정보로 상담하기 →
          </button>
        </div>
        <p role="status" aria-live="polite">{saving ? '프로필 반영·재검토 중…' : notice}</p>
      </main>
    </div>
  );
}
