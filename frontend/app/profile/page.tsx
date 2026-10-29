"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Header from "../../components/Header";

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
    <div className="min-h-screen bg-white flex flex-col">
      <Header rightLabel="내 프로필" />

      <main className="max-w-[860px] mx-auto w-full px-4 py-4 flex-1">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 mb-5"
        >
          <ArrowLeft size={12} /> 처음으로 돌아가기
        </button>

        <p className="text-[0.6rem] font-bold tracking-widest text-gray-300 mb-1">● MY PROFILE</p>
        <h2 className="text-xl font-extrabold text-gray-900 mb-1">내 프로필</h2>
        <p className="text-xs text-gray-400 mb-6">상담에 사용할 기본 정보와 학력·경력·언어 정보를 관리합니다.</p>

        {/* 기본 정보 */}
        <section className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-900">기본 정보</h3>
            <span className="text-[0.65rem] text-gray-300">* 필수 입력</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">국적 <span className="text-gray-400">*</span></label>
              <input value={nationality} onChange={e => setNationality(e.target.value)} placeholder="선택 또는 입력" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-gray-300 placeholder-gray-300" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">만 나이 <span className="text-gray-400">*</span></label>
              <div className="flex items-center border border-gray-200 rounded-xl px-3 py-2.5 gap-1">
                <input value={age} onChange={e => setAge(e.target.value)} placeholder="예: 27" className="flex-1 text-sm outline-none placeholder-gray-300" />
                <span className="text-xs text-gray-300">세</span>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">현재 거주 국가 <span className="text-gray-400">*</span></label>
              <input value={residence} onChange={e => setResidence(e.target.value)} placeholder="선택 또는 입력" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-gray-300 placeholder-gray-300" />
            </div>
          </div>
        </section>

        {/* 학력 */}
        <section className="mb-8 border-t border-gray-50 pt-6">
          <h3 className="text-sm font-bold text-gray-900 mb-1">학력 <span className="text-xs font-normal text-gray-300 ml-1">선택 입력</span></h3>
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">최종 학력</label>
              <select value={education} onChange={e => setEducation(e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none text-gray-700 bg-white">
                <option value="">선택</option>
                {EDUCATIONS.map(e => <option key={e}>{e}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">학적 상태</label>
              <select value={eduStatus} onChange={e => setEduStatus(e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none text-gray-700 bg-white">
                <option value="">선택</option>
                {EDU_STATUS.map(e => <option key={e}>{e}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">전공</label>
              <input value={major} onChange={e => setMajor(e.target.value)} placeholder="예: 컴퓨터공학" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-gray-300 placeholder-gray-300" />
            </div>
          </div>
        </section>

        {/* 경력 */}
        <section className="mb-8 border-t border-gray-50 pt-6">
          <h3 className="text-sm font-bold text-gray-900 mb-1">경력 <span className="text-xs font-normal text-gray-300 ml-1">선택 입력</span></h3>
          <div className="grid grid-cols-2 gap-3 mt-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">직무·경력 분야</label>
              <input value={career} onChange={e => setCareer(e.target.value)} placeholder="예: 웹 개발" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-gray-300 placeholder-gray-300" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">경력 기간</label>
              <input value={careerDuration} onChange={e => setCareerDuration(e.target.value)} placeholder="예: 2년 6개월 / 경력 없음" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-gray-300 placeholder-gray-300" />
            </div>
          </div>
        </section>

        {/* 언어 */}
        <section className="mb-8 border-t border-gray-50 pt-6">
          <h3 className="text-sm font-bold text-gray-900 mb-1">언어 <span className="text-xs font-normal text-gray-300 ml-1">선택 입력</span></h3>
          <div className="grid grid-cols-2 gap-3 mt-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">사용 언어</label>
              <input value={languages} onChange={e => setLanguages(e.target.value)} placeholder="예: 한국어, 영어, 일본어" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-gray-300 placeholder-gray-300" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1.5">어학 시험·자격</label>
              <input value={certs} onChange={e => setCerts(e.target.value)} placeholder="예: IELTS 6.5, JLPT N2" className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-gray-300 placeholder-gray-300" />
            </div>
          </div>
        </section>

        {/* 관심 국가 */}
        <section className="mb-8 border-t border-gray-50 pt-6">
          <h3 className="text-sm font-bold text-gray-900 mb-1">관심 국가 <span className="text-xs font-normal text-gray-300 ml-1">선택 입력 · 복수 선택 가능</span></h3>
          <div className="grid grid-cols-5 gap-2 mt-4">
            {COUNTRIES.map(({ flag, label }) => (
              <button
                key={label}
                onClick={() => toggleCountry(label)}
                className={`relative border rounded-2xl p-4 flex flex-col items-center gap-2 transition-colors ${
                  selectedCountries.includes(label) ? "border-gray-400 bg-gray-50" : "border-gray-100 hover:border-gray-200"
                }`}
              >
                <div className={`absolute top-2 right-2 w-3.5 h-3.5 rounded border ${selectedCountries.includes(label) ? "border-gray-700 bg-gray-700" : "border-gray-200"} flex items-center justify-center`}>
                  {selectedCountries.includes(label) && <span className="text-white text-[8px]">✓</span>}
                </div>
                <span className="text-2xl">{flag}</span>
                <span className="text-xs text-gray-600">{label}</span>
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 mt-2 cursor-pointer">
            <input type="checkbox" checked={undecidedCountry} onChange={e => setUndecidedCountry(e.target.checked)} className="accent-gray-700" />
            <span className="text-xs text-gray-500">미정</span>
          </label>
        </section>

        {/* 진출 목적 */}
        <section className="mb-8 border-t border-gray-50 pt-6">
          <h3 className="text-sm font-bold text-gray-900 mb-1">진출 목적 <span className="text-xs font-normal text-gray-300 ml-1">선택 입력 · 복수 선택 가능</span></h3>
          <div className="grid grid-cols-3 gap-2 mt-4">
            {PURPOSES.map(({ icon, label }) => (
              <button
                key={label}
                onClick={() => togglePurpose(label)}
                className={`relative border rounded-2xl p-5 flex flex-col items-center gap-2 transition-colors ${
                  selectedPurposes.includes(label) ? "border-gray-400 bg-gray-50" : "border-gray-100 hover:border-gray-200"
                }`}
              >
                <div className={`absolute top-2 right-2 w-3.5 h-3.5 rounded border ${selectedPurposes.includes(label) ? "border-gray-700 bg-gray-700" : "border-gray-200"} flex items-center justify-center`}>
                  {selectedPurposes.includes(label) && <span className="text-white text-[8px]">✓</span>}
                </div>
                <span className="text-xl">{icon}</span>
                <span className="text-xs text-gray-600">{label}</span>
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 mt-2 cursor-pointer">
            <input type="checkbox" checked={undecidedPurpose} onChange={e => setUndecidedPurpose(e.target.checked)} className="accent-gray-700" />
            <span className="text-xs text-gray-500">미정</span>
          </label>
        </section>

        <p className="text-xs text-gray-300 mb-6">선택 항목은 나중에 추가하거나 수정할 수 있습니다.</p>

        {/* 버튼 */}
        <div className="flex justify-end gap-3 pb-8">
          <button className="border border-gray-200 text-gray-600 px-6 py-3 rounded-xl text-sm font-medium hover:bg-gray-50">
            프로필 저장하기
          </button>
          <button
            onClick={() => router.push("/chat")}
            className="bg-gray-900 text-white px-6 py-3 rounded-xl text-sm font-semibold hover:bg-gray-700 transition-colors"
          >
            이 정보로 상담하기 →
          </button>
        </div>
      </main>
    </div>
  );
}