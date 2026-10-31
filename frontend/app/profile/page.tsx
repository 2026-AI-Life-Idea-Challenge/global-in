"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Header from "../../components/Header";
import {
  CHAT_KEY,
  RESULT_KEY,
  PROFILE_KEY,
  COMPARE_KEY,
  COUNTRY_CODES,
  VISA_CODES,
  readSaved,
  saveTab,
  expireConsultation,
  invalidateResults,
} from "@/lib/consultation";

const COUNTRIES = [
  { code: "jp", label: "일본" },
  { code: "au", label: "호주" },
  { code: "us", label: "미국" },
  { code: "de", label: "독일" },
  { code: "ca", label: "캐나다" },
];

const PURPOSES = [
  { icon: "🧳", label: "취업" },
  { icon: "🎓", label: "유학" },
  { icon: "✈️", label: "워킹홀리데이 / 교류" },
];

const EDUCATIONS = ["고등학교", "전문대학", "대학교", "대학원"];
const EDU_STATUS = ["재학", "휴학", "졸업", "중퇴"];

// 국가 이름과 국가 코드 매핑
const COUNTRY_ALIASES: Record<string, string> = {
  대한민국: "KR",
  한국: "KR",
  KR: "KR",
  미국: "US",
  US: "US",
  일본: "JP",
  JP: "JP",
  호주: "AU",
  AU: "AU",
  독일: "DE",
  DE: "DE",
  캐나다: "CA",
  CA: "CA",
  영국: "GB",
  GB: "GB",
  프랑스: "FR",
  FR: "FR",
  중국: "CN",
  CN: "CN",
  대만: "TW",
  TW: "TW",
  싱가포르: "SG",
  SG: "SG",
  뉴질랜드: "NZ",
  NZ: "NZ",
  베트남: "VN",
  VN: "VN",
  태국: "TH",
  TH: "TH",
  필리핀: "PH",
  PH: "PH",
  인도: "IN",
  IN: "IN",
  스페인: "ES",
  ES: "ES",
  이탈리아: "IT",
  IT: "IT",
  네덜란드: "NL",
  NL: "NL",
  스위스: "CH",
  CH: "CH",
  스웨덴: "SE",
  SE: "SE",
  노르웨이: "NO",
  NO: "NO",
  덴마크: "DK",
  DK: "DK",
  아일랜드: "IE",
  IE: "IE",
  말레이시아: "MY",
  MY: "MY",
  인도네시아: "ID",
  ID: "ID",
};

export default function ProfilePage() {
  const router = useRouter();

  const [nationality, setNationality] = useState("");
  const [age, setAge] = useState("");
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

  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const saved = readSaved<{ form?: Record<string, unknown> }>(
        PROFILE_KEY,
        {}
      ).form;

      if (!saved) return;

      const fields = {
        nationality: setNationality,
        age: setAge,
        residence: setResidence,
        education: setEducation,
        eduStatus: setEduStatus,
        major: setMajor,
        career: setCareer,
        careerDuration: setCareerDuration,
        languages: setLanguages,
        certs: setCerts,
      };

      Object.entries(fields).forEach(([key, setter]) => {
        if (typeof saved[key] === "string") {
          setter(saved[key] as string);
        }
      });

      if (Array.isArray(saved.selectedCountries)) {
        setSelectedCountries(saved.selectedCountries as string[]);
      }

      if (Array.isArray(saved.selectedPurposes)) {
        setSelectedPurposes(saved.selectedPurposes as string[]);
      }

      setUndecidedCountry(saved.undecidedCountry !== false);
      setUndecidedPurpose(saved.undecidedPurpose !== false);
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  async function saveProfile(goToChat = false) {
    if (saving) return;

    // 국적 검증
    const nationalities = nationality
      .split(/[,/]+/)
      .map((value) => {
        const trimmed = value.trim();
        return (
          COUNTRY_ALIASES[trimmed] ||
          trimmed.toUpperCase()
        );
      })
      .filter(Boolean);

    if (
      !nationalities.length ||
      nationalities.some((value) => !/^[A-Z]{2}$/.test(value))
    ) {
      setNotice(
        "국적은 한국 또는 KR처럼 입력하세요. 복수 국적은 쉼표로 구분하세요."
      );
      return;
    }

    // 현재 거주 국가 검증
    const residenceCode =
      COUNTRY_ALIASES[residence.trim()] ||
      residence.trim().toUpperCase();

    if (!residence.trim()) {
      setNotice("현재 거주 국가를 입력해 주세요.");
      return;
    }

    if (!/^[A-Z]{2}$/.test(residenceCode)) {
      setNotice(
        "현재 거주 국가는 대한민국 또는 KR처럼 입력해 주세요."
      );
      return;
    }

    // 생년월일 검증
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(age) ||
      age > new Date().toLocaleDateString("sv-SE") ||
      Number(age.slice(0, 4)) < new Date().getFullYear() - 80
    ) {
      setNotice("정확한 생년월일을 입력해 주세요.");
      return;
    }

    const countries = undecidedCountry ? [] : selectedCountries;
    const purposes = undecidedPurpose ? [] : selectedPurposes;

    const context = [
      residence && `현재 거주: ${residence}`,
      education && `학력: ${education} ${eduStatus}`,
      major && `전공: ${major}`,
      career && `경력: ${career} ${careerDuration}`,
      languages && `언어: ${languages}`,
      certs && `자격: ${certs}`,
      countries.length && `희망 국가: ${countries.join(", ")}`,
      purposes.length && `목적: ${purposes.join(", ")}`,
    ]
      .filter(Boolean)
      .join("; ");

    if (context.length > 500) {
      setNotice("학력·경력 등 부가 정보를 합계 500자 이내로 줄여 주세요.");
      return;
    }

    const profile = {
      date_of_birth: age,
      nationalities,
      residence_country: residenceCode,
      education: education || null, education_status: eduStatus || null, major: major || null,
      career: career || null, career_duration: careerDuration || null, languages: languages || null, certifications: certs || null,
      target_country:
        countries.length === 1 ? COUNTRY_CODES[countries[0]] : null,
      target_visa_type:
        purposes.length === 1 ? VISA_CODES[purposes[0]] : null,
      purpose: context || null,
    };

    const form = {
      nationality,
      age,
      residence,
      education,
      eduStatus,
      major,
      career,
      careerDuration,
      languages,
      certs,
      selectedCountries,
      selectedPurposes,
      undecidedCountry,
      undecidedPurpose,
    };

    if (!saveTab(PROFILE_KEY, { form, profile, explicitProfile: profile })) {
      setNotice(
        "프로필을 저장하지 못했습니다. 브라우저 저장 설정을 확인해 주세요."
      );
      return;
    }

    setSaving(true);
    setNotice("프로필을 저장했습니다.");

    try {
      if (goToChat) {
        expireConsultation();
        router.push('/chat');
        return;
      }
      const chat = readSaved<{
        session_id?: string;
        messages?: {
          role: string;
          content: string;
          programs?: unknown;
          details?: unknown;
        }[];
      }>(CHAT_KEY, {});

      sessionStorage.removeItem(RESULT_KEY);
      saveTab(COMPARE_KEY, []);

      const pendingChat = {
        ...chat,
        messages: invalidateResults(chat.messages || []),
        compareIds: [],
        profile_pending: true,
      };

      if (chat.session_id) {
        if (!saveTab(CHAT_KEY, pendingChat)) {
          throw new Error("프로필은 저장됐지만 상담 상태 저장에 실패했습니다.");
        }

        const response = await fetch("/api/chat", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: chat.session_id,
            profile,
          }),
        });

        const result = await response.json();

        if (!response.ok) {
          if (response.status === 404) {
            expireConsultation();
            setNotice(
              "프로필은 저장했습니다. 상담이 만료되어 이전 결과를 정리했습니다. 이 정보로 상담하기를 눌러 새 상담을 시작하세요."
            );
            return;
          }

          throw new Error(
            `프로필은 저장했습니다. ${result.error || "재검토에 실패했습니다."} 저장 버튼으로 재시도하거나 상담에서 다시 질문해 주세요.`
          );
        }

        saveTab(RESULT_KEY, result);

        saveTab(CHAT_KEY, {
          ...pendingChat,
          profile_pending: false,
          messages: [
            ...pendingChat.messages,
            {
              role: "assistant",
              content: result.content,
              details: result,
              programs: (result.programs || []).map(
                (p: {
                  program_id: string;
                  name: string;
                  country: string;
                  visa_type: string;
                  summary: string;
                }) => ({
                  id: p.program_id,
                  name: p.name,
                  country: p.country,
                  type: p.visa_type,
                  desc: p.summary,
                })
              ),
            },
          ],
          compareIds: [],
        });
      }

      sessionStorage.removeItem("global-in-compare");

      setNotice(
        chat.session_id
          ? "프로필을 저장하고 재검토 결과를 갱신했습니다."
          : "이 탭에 프로필을 저장했습니다. 다음 상담에 반영됩니다."
      );

      if (goToChat) router.push("/chat");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "재검토에 실패했습니다.";

      setNotice(
        message.startsWith("프로필은 저장")
          ? message
          : `프로필은 저장했습니다. ${message} 저장 버튼으로 재검토를 다시 시도해 주세요.`
      );
    } finally {
      setSaving(false);
    }
  }

  const toggleCountry = (label: string) => {
    setUndecidedCountry(false);

    setSelectedCountries((prev) =>
      prev.includes(label)
        ? prev.filter((c) => c !== label)
        : [...prev, label]
    );
  };

  const togglePurpose = (label: string) => {
    setUndecidedPurpose(false);

    setSelectedPurposes((prev) =>
      prev.includes(label)
        ? prev.filter((p) => p !== label)
        : [...prev, label]
    );
  };

  const inputStyle = {
    width: "100%",
    border: "1px solid #e5e8f0",
    borderRadius: 11,
    padding: "12px 14px",
    fontSize: "0.86rem",
    background: "#fafbfe",
    color: "#252a40",
    boxSizing: "border-box" as const,
    minHeight: 48,
    transition: "all 0.2s ease",
  };

  const sectionTitleStyle = {
    fontSize: "0.95rem",
    fontWeight: 700,
    color: "#252a40",
    margin: "0 0 20px",
    letterSpacing: "-0.025em",
  };

  const sectionStyle = {
    marginBottom: 18,
    background: "#fff",
    border: "1px solid #eaecf3",
    borderRadius: 18,
    padding: 26,
    boxShadow: "0 3px 14px rgba(35,45,90,0.025)",
  };

  return (
    <div className="profile-page">
      <Header rightLabel="내 프로필" />

      <main className="profile-main">
        <button className="back-button" onClick={() => router.back()}>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M19 12H5M12 5l-7 7 7 7" />
          </svg>
          돌아가기
        </button>

        <div className="profile-heading">
          <p className="eyebrow">● MY PROFILE</p>
          <h2>내 프로필</h2>
          <p className="profile-description">
            상담에 사용할 기본 정보와 학력·경력·언어 정보를 관리합니다.
          </p>
        </div>

        {/* 기본 정보 */}
        <section style={sectionStyle}>
          <div className="section-heading">
            <h3 style={sectionTitleStyle}>기본 정보</h3>
            <span className="required-note">* 필수 입력</span>
          </div>

          <div className="form-grid three-columns">
            {[
              {
                label: "국적 *",
                value: nationality,
                onChange: setNationality,
                placeholder: "예: 대한민국",
              },
              {
                label: "생년월일 *",
                value: age,
                onChange: setAge,
                placeholder: "YYYY-MM-DD",
                type: "date",
              },
              {
                label: "현재 거주 국가 *",
                value: residence,
                onChange: setResidence,
                placeholder: "예: 대한민국",
              },
            ].map(({ label, value, onChange, placeholder, type }) => (
              <div key={label}>
                <label className="field-label">{label}</label>
                <input
                  type={type || "text"}
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  placeholder={placeholder}
                  style={inputStyle}
                />
              </div>
            ))}
          </div>
        </section>

        {/* 학력 */}
        <section style={sectionStyle}>
          <h3 style={sectionTitleStyle}>
            학력 <span className="optional-label">선택 입력</span>
          </h3>

          <div className="form-grid three-columns">
            <div>
              <label className="field-label">최종 학력</label>
              <select
                value={education}
                onChange={(e) => setEducation(e.target.value)}
                style={inputStyle}
              >
                <option value="">선택</option>
                {EDUCATIONS.map((e) => (
                  <option key={e}>{e}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="field-label">학적 상태</label>
              <select
                value={eduStatus}
                onChange={(e) => setEduStatus(e.target.value)}
                style={inputStyle}
              >
                <option value="">선택</option>
                {EDU_STATUS.map((e) => (
                  <option key={e}>{e}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="field-label">전공</label>
              <input
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                placeholder="예: 컴퓨터공학"
                style={inputStyle}
              />
            </div>
          </div>
        </section>

        {/* 경력 */}
        <section style={sectionStyle}>
          <h3 style={sectionTitleStyle}>
            경력 <span className="optional-label">선택 입력</span>
          </h3>

          <div className="form-grid two-columns">
            <div>
              <label className="field-label">직무·경력 분야</label>
              <input
                value={career}
                onChange={(e) => setCareer(e.target.value)}
                placeholder="예: 웹 개발"
                style={inputStyle}
              />
            </div>

            <div>
              <label className="field-label">경력 기간</label>
              <input
                value={careerDuration}
                onChange={(e) => setCareerDuration(e.target.value)}
                placeholder="예: 2년 6개월 / 경력 없음"
                style={inputStyle}
              />
            </div>
          </div>
        </section>

        {/* 언어 */}
        <section style={sectionStyle}>
          <h3 style={sectionTitleStyle}>
            언어 <span className="optional-label">선택 입력</span>
          </h3>

          <div className="form-grid two-columns">
            <div>
              <label className="field-label">사용 언어</label>
              <input
                value={languages}
                onChange={(e) => setLanguages(e.target.value)}
                placeholder="예: 한국어, 영어, 일본어"
                style={inputStyle}
              />
            </div>

            <div>
              <label className="field-label">어학 시험·자격</label>
              <input
                value={certs}
                onChange={(e) => setCerts(e.target.value)}
                placeholder="예: IELTS 6.5, JLPT N2"
                style={inputStyle}
              />
            </div>
          </div>
        </section>

        {/* 관심 국가 */}
        <section style={sectionStyle}>
          <h3 style={sectionTitleStyle}>
            관심 국가{" "}
            <span className="optional-label">선택 입력 · 복수 선택 가능</span>
          </h3>

          <div className="country-grid">
            {COUNTRIES.map(({ code, label }) => {
              const selected = selectedCountries.includes(label);

              return (
                <button
                  type="button"
                  key={label}
                  onClick={() => toggleCountry(label)}
                  className={`choice-card ${selected ? "selected" : ""}`}
                >
                  <span className="choice-check">
                    {selected ? "✓" : ""}
                  </span>

                  <img
                    src={`https://flagcdn.com/w80/${code}.png`}
                    alt={`${label} 국기`}
                    className="country-flag"
                  />

                  <span className="choice-label">{label}</span>
                </button>
              );
            })}
          </div>

          <label className="undecided-option">
            <input
              type="checkbox"
              checked={undecidedCountry}
              onChange={(e) => setUndecidedCountry(e.target.checked)}
            />
            <span>아직 정하지 않았어요</span>
          </label>
        </section>

        {/* 진출 목적 */}
        <section style={sectionStyle}>
          <h3 style={sectionTitleStyle}>
            진출 목적{" "}
            <span className="optional-label">선택 입력 · 복수 선택 가능</span>
          </h3>

          <div className="purpose-grid">
            {PURPOSES.map(({ icon, label }) => {
              const selected = selectedPurposes.includes(label);

              return (
                <button
                  type="button"
                  key={label}
                  onClick={() => togglePurpose(label)}
                  className={`choice-card purpose-card ${
                    selected ? "selected" : ""
                  }`}
                >
                  <span className="choice-check">
                    {selected ? "✓" : ""}
                  </span>

                  <span className="purpose-icon">{icon}</span>
                  <span className="choice-label">{label}</span>
                </button>
              );
            })}
          </div>

          <label className="undecided-option">
            <input
              type="checkbox"
              checked={undecidedPurpose}
              onChange={(e) => setUndecidedPurpose(e.target.checked)}
            />
            <span>아직 정하지 않았어요</span>
          </label>
        </section>

        <p className="bottom-guide">
          선택 항목은 나중에 추가하거나 수정할 수 있습니다.
        </p>

        {/* 저장 안내 및 버튼 */}
        <div className="save-area">
          <p className="status-message" role="status" aria-live="polite">
            {saving ? "프로필 반영·재검토 중…" : notice}
          </p>

          <div className="action-buttons">
            <button
              disabled={saving}
              onClick={() => saveProfile()}
              className="save-button"
            >
              프로필 저장하기
            </button>

            <button
              disabled={saving}
              onClick={() => saveProfile(true)}
              className="consult-button"
            >
              이 정보로 상담하기 <span>→</span>
            </button>
          </div>
        </div>
      </main>

      <style jsx global>{`
        .profile-page {
          min-height: 100vh;
          background: #f7f8fc;
          color: #252a40;
          display: flex;
          flex-direction: column;
        }

        .profile-main {
          width: 100%;
          max-width: 960px;
          margin: 0 auto;
          padding: 38px 28px 60px;
          flex: 1;
          box-sizing: border-box;
        }

        .back-button {
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 5px 0;
          margin-bottom: 28px;
          border: none;
          background: transparent;
          color: #788097;
          font-size: 0.8rem;
          cursor: pointer;
          transition: color 0.2s;
        }

        .back-button:hover {
          color: #6975c9;
        }

        .profile-heading {
          margin-bottom: 28px;
        }

        .eyebrow {
          color: #8189d6;
          font-size: 0.67rem;
          font-weight: 800;
          letter-spacing: 0.16em;
          margin: 0 0 9px;
        }

        .profile-heading h2 {
          color: #20243a;
          font-size: 1.75rem;
          font-weight: 800;
          letter-spacing: -0.05em;
          margin: 0 0 9px;
        }

        .profile-description {
          color: #858ca0;
          font-size: 0.84rem;
          line-height: 1.7;
          margin: 0;
        }

        .section-heading {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .required-note {
          color: #a3a9b8;
          font-size: 0.7rem;
        }

        .optional-label {
          color: #a3a9b8;
          font-size: 0.74rem;
          font-weight: 400;
          margin-left: 4px;
        }

        .field-label {
          display: block;
          color: #626a80;
          font-size: 0.78rem;
          font-weight: 500;
          margin-bottom: 8px;
        }

        .form-grid {
          display: grid;
          gap: 16px;
        }

        .three-columns {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .two-columns {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .profile-main input:not([type="checkbox"]),
        .profile-main select {
          width: 100%;
          min-width: 0;
          box-sizing: border-box;
          min-height: 48px;
          padding: 12px 14px;
          border: 1px solid #e5e8f0;
          border-radius: 11px;
          background: #fafbfe;
          color: #252a40;
          font-size: 0.86rem;
          outline: none;
          transition: border-color 0.2s, box-shadow 0.2s,
            background 0.2s;
        }

        .profile-main input:not([type="checkbox"]):focus,
        .profile-main select:focus {
          border-color: #858de0;
          background: #fff;
          box-shadow: 0 0 0 3px rgba(133, 141, 224, 0.12);
        }

        .profile-main input::placeholder {
          color: #a7adbd;
        }

        .country-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 12px;
        }

        .purpose-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }

        .choice-card {
          position: relative;
          min-width: 0;
          min-height: 116px;
          padding: 20px 10px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          gap: 10px;
          border: 1px solid #e7e9f1;
          border-radius: 15px;
          background: #fafbfe;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .choice-card:hover {
          border-color: #a0a7e9;
          background: #f5f6ff;
          transform: translateY(-2px);
        }

        .choice-card.selected {
          border-color: #8189d6;
          background: #f1f2ff;
          box-shadow: 0 0 0 2px rgba(129, 137, 214, 0.08);
        }

        .choice-check {
          position: absolute;
          top: 10px;
          right: 10px;
          width: 19px;
          height: 19px;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid #dfe2eb;
          border-radius: 6px;
          color: #fff;
          background: #fff;
          font-size: 0.7rem;
          font-weight: 700;
        }

        .choice-card.selected .choice-check {
          border-color: #777fd0;
          background: #777fd0;
        }

        .country-flag {
          display: block;
          width: 48px;
          height: 34px;
          object-fit: cover;
          border-radius: 5px;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
        }

        .purpose-icon {
          font-size: 1.55rem;
          line-height: 1.2;
        }

        .choice-label {
          color: #41475e;
          font-size: 0.82rem;
          font-weight: 600;
          text-align: center;
          line-height: 1.4;
          word-break: keep-all;
        }

        .choice-card.selected .choice-label {
          color: #5e68b7;
        }

        .undecided-option {
          display: flex;
          align-items: center;
          gap: 9px;
          margin-top: 16px;
          color: #737b90;
          font-size: 0.8rem;
          cursor: pointer;
        }

        .undecided-option input {
          width: 16px;
          height: 16px;
          accent-color: #777fd0;
          cursor: pointer;
        }

        .bottom-guide {
          color: #9ba1b1;
          font-size: 0.77rem;
          margin: 4px 0 22px;
        }

        .save-area {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          width: 100%;
        }

        .status-message {
          width: 100%;
          min-height: 20px;
          margin: 0 0 12px;
          color: #6975c9;
          font-size: 0.8rem;
          line-height: 1.6;
          text-align: right;
        }

        .action-buttons {
          display: flex;
          justify-content: flex-end;
          align-items: center;
          gap: 12px;
          width: 100%;
          padding-bottom: 12px;
        }

        .action-buttons button {
          min-height: 49px;
          padding: 0 24px;
          border-radius: 12px;
          font-size: 0.86rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .save-button {
          border: 1px solid #e1e4ed;
          color: #50566b;
          background: #fff;
          font-weight: 600;
        }

        .save-button:hover {
          border-color: #b9bee8;
          background: #f7f8ff;
        }

        .consult-button {
          border: none;
          color: #fff;
          background: #6975c9;
          font-weight: 700;
          box-shadow: 0 5px 14px rgba(105, 117, 201, 0.2);
        }

        .consult-button:hover {
          background: #5865ba;
          transform: translateY(-2px);
          box-shadow: 0 7px 17px rgba(105, 117, 201, 0.25);
        }

        .action-buttons button:disabled {
          opacity: 0.55;
          cursor: not-allowed;
          transform: none;
        }

        @media (max-width: 768px) {
          .profile-main {
            padding: 28px 20px 44px;
          }

          .three-columns {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .country-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
          }
        }

        @media (max-width: 520px) {
          .profile-main {
            padding: 22px 14px 36px;
          }

          .profile-heading h2 {
            font-size: 1.5rem;
          }

          .profile-description {
            font-size: 0.78rem;
          }

          .profile-main section {
            padding: 18px !important;
            border-radius: 15px;
          }

          .three-columns,
          .two-columns {
            grid-template-columns: 1fr;
          }

          .country-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .purpose-grid {
            grid-template-columns: 1fr;
          }

          .purpose-card {
            min-height: 82px;
          }

          .action-buttons {
            flex-direction: column;
          }

          .action-buttons button {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
