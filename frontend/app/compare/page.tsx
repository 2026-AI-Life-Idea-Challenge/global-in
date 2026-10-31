"use client";
import Header from "../../components/Header";
import Sidebar from "../../components/Sidebar";
import { useComparison } from '@/lib/useComparison';
import { comparisonRows } from '@/lib/comparisonRows';
import { safeSource } from '@/components/ConsultationDetails';


export default function ComparePage() {
  const { items: PROGRAMS } = useComparison();
  return (
    <div className="min-h-screen flex flex-col">
      <Header rightLabel="비교" />

      <div className="flex flex-1 max-w-[900px] mx-auto w-full">
        <div className="w-44 shrink-0 border-r border-gray-100 px-3 py-4">
          <Sidebar />
        </div>

        <main className="flex-1 px-6 py-6">
          <h2 className="text-lg font-bold mb-6">프로그램 비교</h2>
          <p>상담과 목록에서 선택한 실제 프로그램을 비교합니다. 비용·기간 등 확인되지 않은 정보는 채우지 않습니다.</p>
          {PROGRAMS.length < 2 && <p role="status">프로그램을 2개 이상 선택해 주세요. <a href="/chat">상담으로 이동 →</a></p>}

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
                {comparisonRows.map(({ label, value }) => (
                  <tr key={label} className="border-b border-gray-50">
                    <td className="text-xs text-gray-400 py-3 pr-4">{label}</td>
                    {PROGRAMS.map((p) => (
                      <td key={p.name} className="py-3 px-4 text-sm text-gray-700">
                        {value(p)}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr className="border-b border-gray-50"><td className="text-xs text-gray-400 py-3 pr-4">공식 출처</td>{PROGRAMS.map(p => <td key={p.id} className="py-3 px-4 text-sm text-gray-700">{p.sources?.filter(source => safeSource(source.source_url)).map((source,index) => <p key={index}><a href={source.source_url} target="_blank" rel="noopener noreferrer">{source.title}</a></p>) || '공식 출처 확인 필요'}</td>)}</tr>
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </div>
  );
}
