"use client";
import Header from "../../components/Header";
import Sidebar from "../../components/Sidebar";

const PROGRAMS = [
  {
    name: "일본 워킹홀리데이",
    country: "일본 🇯🇵",
    type: "워킹홀리데이",
    age: "만 18~30세",
    duration: "최대 1년",
    cost: "약 30~50만원",
    language: "일본어 우대",
    point: "가깝고 생활비 저렴",
  },
  {
    name: "호주 워킹홀리데이",
    country: "호주 🇦🇺",
    type: "워킹홀리데이",
    age: "만 18~30세",
    duration: "최대 1년 (연장 가능)",
    cost: "약 40~60만원",
    language: "영어",
    point: "영어 실력 향상, 높은 최저임금",
  },
];

const ROWS: { label: string; key: keyof typeof PROGRAMS[0] }[] = [
  { label: "국가", key: "country" },
  { label: "유형", key: "type" },
  { label: "나이 조건", key: "age" },
  { label: "체류 기간", key: "duration" },
  { label: "비용", key: "cost" },
  { label: "언어", key: "language" },
  { label: "특징", key: "point" },
];

export default function ComparePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header rightLabel="비교" />

      <div className="flex flex-1 max-w-[900px] mx-auto w-full">
        <div className="w-44 shrink-0 border-r border-gray-100 px-3 py-4">
          <Sidebar />
        </div>

        <main className="flex-1 px-6 py-6">
          <h2 className="text-lg font-bold mb-6">프로그램 비교</h2>

          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr>
                  <th className="text-left text-xs text-gray-400 font-medium py-2 pr-4 w-28">
                    항목
                  </th>
                  {PROGRAMS.map((p) => (
                    <th
                      key={p.name}
                      className="text-left font-bold py-2 px-4 border-b border-gray-100"
                    >
                      {p.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map(({ label, key }) => (
                  <tr key={key} className="border-b border-gray-50">
                    <td className="text-xs text-gray-400 py-3 pr-4">{label}</td>
                    {PROGRAMS.map((p) => (
                      <td key={p.name} className="py-3 px-4 text-sm text-gray-700">
                        {p[key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </div>
  );
}