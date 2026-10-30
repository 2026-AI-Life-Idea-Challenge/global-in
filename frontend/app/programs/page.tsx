"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";

const FLAGS: Record<string, string> = {
  독일: '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  일본: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  호주: '<rect width="30" height="20" fill="#00247d"/><path d="M0 0l14 9M14 0L0 9" stroke="#fff" strokeWidth="1.6"/><path d="M7 0v9M0 4.5h14" stroke="#fff" strokeWidth="3"/><path d="M7 0v9M0 4.5h14" stroke="#cf142b" strokeWidth="1.6"/>',
  미국: '<rect width="30" height="20" fill="#fff"/><rect y="0" width="30" height="1.55" fill="#b22234"/><rect y="3.1" width="30" height="1.55" fill="#b22234"/><rect y="6.2" width="30" height="1.55" fill="#b22234"/><rect y="9.3" width="30" height="1.55" fill="#b22234"/><rect y="12.4" width="30" height="1.55" fill="#b22234"/><rect y="15.5" width="30" height="1.55" fill="#b22234"/><rect y="18.6" width="30" height="1.55" fill="#b22234"/><rect width="13" height="10.8" fill="#3c3b6e"/>',
  캐나다: '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/><path d="M15 4l1.3 3 2-1-.6 4 1.7-.4-.4 1.8 1.5 1-3.5 2.4.2 2.2h-4.4l.2-2.2-3.5-2.4 1.5-1-.4-1.8 1.7.4-.6-4 2 1z" fill="#d52b1e"/>',
};

function FlagSvg({ country, size = 22 }: { country: string; size?: number }) {
  if (!FLAGS[country]) return null;
  return (
    <svg
      viewBox="0 0 30 20"
      style={{ width: size, height: Math.round(size * 2 / 3), borderRadius: 2, flexShrink: 0 }}
      dangerouslySetInnerHTML={{ __html: FLAGS[country] }}
    />
  );
}

export const PROGRAMS = [
  // ─── 일본 프로그램 ───
  { id: 1, type: "프로그램", country: "일본", tags: ["일본", "취업"], name: "기술·인문지식·국제업무", desc: "전문 지식과 기술을 활용해 일본에서 일하는 취업 경로.", sub: "담당 직무와 학력·경력 등 요건 확인", officialUrl: "https://www.moj.go.jp/isa/applications/status/gijinkoku.html" },
  { id: 8, type: "프로그램", country: "일본", tags: ["일본", "유학·교환학생"], name: "유학 비자 (留学)", desc: "일본의 대학, 전문학교 등 교육기관에서 학업을 위한 체류 경로.", sub: "입학허가서·재정 증빙 등 요건 확인", officialUrl: "https://www.moj.go.jp/isa/applications/status/ryugaku.html" },
  { id: 9, type: "프로그램", country: "일본", tags: ["일본", "워킹홀리데이"], name: "워킹홀리데이 (일본)", desc: "한국-일본 협정에 따라 일본에서 여행·체험 근로를 병행하는 경로.", sub: "연령·과거 참여 이력·이중국적 등 요건 확인", officialUrl: "https://www.mofa.go.jp/mofaj/toko/visa/working_h.html" },

  // ─── 독일 프로그램 ───
  { id: 3, type: "프로그램", country: "독일", tags: ["독일", "취업"], name: "기회카드 (Chancenkarte)", desc: "독일에서 일자리를 찾기 위한 체류 경로.", sub: "자격 인정 또는 점수 경로·언어·생계 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/opportunity-card" },
  { id: 10, type: "프로그램", country: "독일", tags: ["독일", "취업"], name: "EU 블루카드", desc: "고학력 전문직을 위한 독일 취업 및 장기 체류 경로.", sub: "학위 인정·고용계약·최소임금 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/eu-blue-card" },
  { id: 11, type: "프로그램", country: "독일", tags: ["독일", "취업"], name: "숙련노동자 비자 (Fachkräfte)", desc: "독일 내 직업훈련 또는 학위 기반으로 취업하는 경로.", sub: "자격 인정·고용계약 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/skilled-immigration" },
  { id: 12, type: "프로그램", country: "독일", tags: ["독일", "유학·교환학생"], name: "독일 유학 비자", desc: "독일의 대학 또는 동등 교육기관에서 학업을 위한 경로.", sub: "입학허가·재정 증빙·어학 능력 등 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/student-visa" },
  { id: 13, type: "프로그램", country: "독일", tags: ["독일", "유학·교환학생"], name: "대학입학 준비 비자", desc: "독일 대학 입학 전 어학연수·입학수속 준비를 위한 체류 경로.", sub: "입학 예정·어학 과정 등 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/language-course-higher-education" },
  { id: 14, type: "프로그램", country: "독일", tags: ["독일", "워킹홀리데이"], name: "워킹홀리데이 (독일-한국)", desc: "한국-독일 협정에 따라 독일에서 여행·체험 근로를 병행하는 경로.", sub: "연령·과거 참여 이력 등 요건 확인", officialUrl: "https://korea.diplo.de/kr-ko/visa-einreise/working-holiday/1598618" },

  // ─── 호주 프로그램 ───
  { id: 4, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워킹홀리데이 비자 (417) 1차", desc: "호주에서 여행하며 단기 근로를 병행하는 경로.", sub: "여권 국가·연령·이전 참여 이력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417" },
  { id: 15, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워킹홀리데이 비자 (417) 2차", desc: "1차 비자 후 지역사업장 근무 기간을 채워 연장하는 경로.", sub: "1차 비자 보유·지역사업장 근무 88일 이상 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417" },
  { id: 16, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워킹홀리데이 비자 (417) 3차", desc: "2차 비자 후 추가 지역사업장 근무로 한 번 더 연장하는 경로.", sub: "2차 비자 보유·지역사업장 근무 88일 이상 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417" },
  { id: 17, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워크앤홀리데이 비자 (462) 1차", desc: "지정 협정국 여권으로 신청하는 호주 워킹홀리데이 경로 (한국 포함).", sub: "협정국 여권·연령·학력·어학 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-and-holiday-462" },
  { id: 18, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워크앤홀리데이 비자 (462) 2차", desc: "1차 비자 후 지역사업장 근무로 연장하는 경로.", sub: "1차 비자 보유·지역사업장 근무 기간 충족 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-and-holiday-462" },
  { id: 19, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워크앤홀리데이 비자 (462) 3차", desc: "2차 비자 후 추가 근무로 한 번 더 연장하는 경로.", sub: "2차 비자 보유·추가 지역근무 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-and-holiday-462" },
  { id: 20, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "수요기술 취업 비자 (482) Core", desc: "수요직종에 해당하는 고용주 후원 임시취업 경로.", sub: "수요직종·고용주 후원·어학·경력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482" },
  { id: 21, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "수요기술 취업 비자 (482) 노동협약", desc: "노동협약을 통한 고용주 후원 임시취업 경로.", sub: "협약 고용주·해당 직종 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482" },
  { id: 22, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "수요기술 취업 비자 (482) 전문기술", desc: "고임금 전문직을 위한 고용주 후원 임시취업 경로.", sub: "고임금 요건·고용주 후원 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482" },
  { id: 23, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "지역기술임시 비자 (491)", desc: "지역 주정부 또는 가족의 추천을 받아 지역에서 취업하는 임시 경로.", sub: "주정부 추천·수요직종·어학·점수 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-work-regional-provisional-491" },
  { id: 24, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "지역고용후원 비자 (494) 고용주 후원", desc: "지역 고용주의 후원을 받아 지역에서 취업하는 임시 경로.", sub: "지역 고용주 후원·수요직종·어학·경력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494" },
  { id: 52, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "지역고용후원 비자 (494) 노동협약", desc: "노동협약을 통한 지역 고용주 후원 임시취업 경로.", sub: "협약 고용주·지역 근무·해당 직종 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494" },
  { id: 25, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "트레이닝 비자 (407)", desc: "직업 훈련 또는 업무 관련 연수를 위한 임시 체류 경로.", sub: "후원 기관·훈련 계획·재정 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407" },
  { id: 26, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "고용주 노미네이트 비자 (186) 직접입국", desc: "호주 고용주가 직접 추천하는 영주권 경로.", sub: "고용주 추천·수요직종·어학·경력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186" },
  { id: 27, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "고용주 노미네이트 비자 (186) 임시→영주", desc: "임시취업(482)에서 고용주 추천 영주권으로 전환하는 경로.", sub: "482 비자 3년·동일 고용주·수요직종 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186" },
  { id: 28, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "고용주 노미네이트 비자 (186) 노동협약", desc: "노동협약을 통한 고용주 추천 영주권 경로.", sub: "협약 고용주·해당 직종 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186" },
  { id: 29, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "독립기술 이민 비자 (189)", desc: "고용주나 가족 보증 없이 점수제로 신청하는 영주권 경로.", sub: "EOI 제출·초청·수요직종·점수·어학 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189" },
  { id: 30, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "주정부 노미네이트 비자 (190)", desc: "호주 주/테리토리 정부의 추천을 받아 신청하는 영주권 경로.", sub: "주정부 추천·수요직종·점수·어학 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-nominated-190" },
  { id: 31, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "지역영주 비자 (191)", desc: "지역 임시비자(491/494) 소지 후 3년 경력으로 신청하는 영주권 경로.", sub: "지역 임시비자 3년·소득 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/permanent-residence-regional-191" },
  { id: 32, type: "프로그램", country: "호주", tags: ["호주", "유학·교환학생"], name: "학생 비자 (500)", desc: "호주의 교육기관에 등록해 정규 과정을 이수하기 위한 경로.", sub: "입학허가(CoE)·재정·어학·GTE 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500" },

  // ─── 미국 프로그램 ───
  { id: 5, type: "프로그램", country: "미국", tags: ["미국", "유학·교환학생"], name: "학생 비자 (F-1)", desc: "미국의 대학 등 교육기관에서 학업을 위한 경로.", sub: "교육기관·학업 과정·I-20 등 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html" },
  { id: 33, type: "프로그램", country: "미국", tags: ["미국", "유학·교환학생"], name: "J-1 대학생 (Student)", desc: "미국 교육기관에서 학업을 위한 교환 방문자 경로.", sub: "교육기관·DS-2019·재정·어학 요건 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html" },
  { id: 34, type: "프로그램", country: "미국", tags: ["미국", "취업"], name: "H-1B 비자", desc: "미국 고용주가 후원하는 전문직 취업 비자.", sub: "학위·고용주 후원·추첨·LCA 등 요건 확인", officialUrl: "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations" },
  { id: 35, type: "프로그램", country: "미국", tags: ["미국", "취업"], name: "J-1 인턴십", desc: "인턴십 형태로 미국에서 실무 경험을 쌓는 교환 방문자 경로.", sub: "재학 중이거나 졸업 1년 이내·DS-2019·후원기관 요건 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html" },
  { id: 36, type: "프로그램", country: "미국", tags: ["미국", "취업"], name: "J-1 연수 (Trainee)", desc: "연수 형태로 미국에서 직업 훈련을 받는 교환 방문자 경로.", sub: "학위 또는 경력·DS-2019·후원기관 요건 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html" },
  { id: 37, type: "프로그램", country: "미국", tags: ["미국", "워킹홀리데이"], name: "J-1 Summer Work Travel", desc: "대학생이 미국에서 여름방학 동안 일하며 여행하는 교환 방문자 경로.", sub: "재학 중·고용계약·DS-2019·후원기관 요건 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html" },
  { id: 38, type: "프로그램", country: "미국", tags: ["미국", "장학·연수"], name: "WEST 프로그램", desc: "한국 대학생이 미국에서 인턴십·연수를 경험하는 한미 교육 교류 프로그램.", sub: "재학생·어학·선발 심사 등 요건 확인", officialUrl: "https://www.niied.go.kr/web/niied/nid/niied_board/5749" },

  // ─── 캐나다 프로그램 ───
  { id: 6, type: "프로그램", country: "캐나다", tags: ["캐나다", "취업"], name: "고용주 지정 취업허가 (ESWP)", desc: "특정 캐나다 고용주를 위해 발급되는 임시 취업 경로.", sub: "고용주 LMIA 또는 면제 요건·직종 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/temporary/apply.html" },
  { id: 39, type: "프로그램", country: "캐나다", tags: ["캐나다", "워킹홀리데이"], name: "국제경험 캐나다 워킹홀리데이 (IEC)", desc: "협정 국가 청년을 위한 캐나다 워킹홀리데이 경로.", sub: "연령·Pool 지원·고용 오퍼 등 요건 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/activities.html" },
  { id: 40, type: "프로그램", country: "캐나다", tags: ["캐나다", "취업"], name: "졸업 후 취업허가 (PGWP)", desc: "캐나다 공인 학교(DLI) 졸업자를 위한 취업허가 경로.", sub: "DLI 졸업·학업 기간 등 요건 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation.html" },
  { id: 41, type: "프로그램", country: "캐나다", tags: ["캐나다", "유학·교환학생"], name: "학생 비자 (Study Permit)", desc: "캐나다 지정학교(DLI)에서 6개월 이상 학업을 위한 경로.", sub: "DLI 입학허가·재정·어학·목적 설명 요건 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit.html" },

  // ─── 지원제도 (여러 국가) ───
  { id: 2, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "K-Move스쿨", desc: "해외취업에 필요한 어학·직무 연수와 취업 연계를 지원.", sub: "맞춤형 교육·연수비·일부 취업 지원", officialUrl: "https://www.worldjob.or.kr/ovsea/sdytrn.do" },
  { id: 7, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "해외취업정착지원금", desc: "해외취업 후 초기 정착과 경력 개발을 돕는 지원.", sub: "해외취업자의 초기 정착을 위한 지원금", officialUrl: "https://kmovefair.worldjob.or.kr/ovsea/sbsd.do?menuId=1000000041" },
  { id: 42, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "해외취업알선", desc: "해외 고용주와 구직자를 연결하는 취업 알선 서비스.", sub: "월드잡플러스 가입·이력서 등록 등 확인", officialUrl: "https://www.worldjob.or.kr/ovsea/empymn.do?menuId=1000000040" },
  { id: 43, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "K-MOVE 멘토링", desc: "해외취업 경험자(멘토)와 구직자(멘티)를 연결하는 지원.", sub: "멘티 신청·매칭 후 온·오프라인 멘토링 진행", officialUrl: "https://kmovefair.worldjob.or.kr/kmove/intro.do" },
  { id: 44, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "해외일경험지원사업 WELL", desc: "단기 해외 일경험을 통한 청년 글로벌 역량 강화 지원.", sub: "재학·졸업 청년 대상·파견 기업 등 요건 확인", officialUrl: "https://www.worldjob.or.kr/ovsea/well.do" },

  // ─── 지원제도 (국가별) ───
  { id: 45, type: "지원제도", country: "미국", tags: ["미국", "장학·연수"], name: "한·미 대학생 연수 WEST", desc: "미국에서 인턴십·연수를 경험하는 한미 교육 교류 프로그램 참가 지원.", sub: "참가비·체재비·어학연수비 일부 지원", officialUrl: "https://www.niied.go.kr/web/niied/nid/niied_board/5749" },
  { id: 46, type: "지원제도", country: "미국", tags: ["미국", "장학·연수"], name: "WEST 어학연수비 대출", desc: "WEST 프로그램 참가자를 위한 어학연수비 대출 지원.", sub: "WEST 합격자·대출 한도·상환 조건 확인", officialUrl: "https://www.kosaf.go.kr/ko/tuition.do?pg=PTHDWestAply_01M&ttab1=2" },
  { id: 47, type: "지원제도", country: "일본", tags: ["일본", "장학·연수"], name: "2027 MEXT 연구유학생 장학", desc: "일본 문부과학성이 지원하는 연구유학생 장학 프로그램.", sub: "대학 추천·연령·학업 성적 등 요건 확인", officialUrl: "https://www.kr.emb-japan.go.jp/itpr_ko/news_20260512.html" },
  { id: 48, type: "지원제도", country: "호주", tags: ["호주", "장학·연수"], name: "Research Training Program (RTP)", desc: "호주 정부가 지원하는 대학원 연구과정 장학 프로그램.", sub: "호주 대학 입학·연구 계획 등 요건 확인", officialUrl: "https://www.education.gov.au/research-block-grants/research-training-program" },
  { id: 49, type: "지원제도", country: "미국", tags: ["미국", "장학·연수"], name: "2027 풀브라이트 대학원 장학", desc: "미한교육위원회가 운영하는 미국 대학원 장학 프로그램.", sub: "한국 국적·학업 성적·어학·연구계획 등 요건 확인", officialUrl: "https://www.fulbright.or.kr/grant/graduate/" },
  { id: 50, type: "지원제도", country: "독일", tags: ["독일", "장학·연수"], name: "베를린자유대 독일장학 (Deutschlandstipendium)", desc: "베를린자유대학교의 독일장학금 프로그램.", sub: "재학생·성적·사회 참여 등 요건 확인", officialUrl: "https://www.fu-berlin.de/en/sites/deutschlandstipendium" },
  { id: 51, type: "지원제도", country: "캐나다", tags: ["캐나다", "장학·연수"], name: "워털루 국제석사 우수장학 (IMAE)", desc: "워털루대학교의 국제 석사과정 우수 장학금.", sub: "입학 예정 국제 석사생·성적 요건 확인", officialUrl: "https://uwaterloo.ca/current-graduate-students/awards-and-funding/international-student-funding" },
];

const COUNTRIES = ["전체", "독일", "일본", "호주", "미국", "캐나다"];
const PURPOSES = ["전체", "취업", "유학·교환학생", "워킹홀리데이", "장학·연수"];
const TYPES = ["전체", "프로그램", "지원제도"];

type Program = typeof PROGRAMS[number];

const COMPARE_ROWS: { label: string; render: (p: Program) => string }[] = [
  { label: "국가", render: (p) => p.country ?? "여러 국가" },
  { label: "유형", render: (p) => p.type },
  { label: "목적", render: (p) => p.tags.filter(t => t !== p.country && t !== "여러 국가" && t !== "과정별 상이").join(", ") },
  { label: "대상·조건", render: (p) => p.sub },
];

export default function ProgramsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("전체");
  const [countryFilter, setCountryFilter] = useState("전체");
  const [purposeFilter, setPurposeFilter] = useState("전체");
  const [compareIds, setCompareIds] = useState<number[]>([]);

  const filtered = PROGRAMS.filter(p => {
    if (search && !p.name.includes(search) && !p.desc.includes(search)) return false;
    if (typeFilter !== "전체" && p.type !== typeFilter) return false;
    if (countryFilter !== "전체" && p.country !== countryFilter) return false;
    if (purposeFilter !== "전체" && !p.tags.includes(purposeFilter)) return false;
    return true;
  });

  const comparePrograms = PROGRAMS.filter(p => compareIds.includes(p.id));

  function toggleCompare(id: number) {
    setCompareIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  }

  const chipStyle = (active: boolean) => ({
    display: "flex", alignItems: "center", gap: 5,
    padding: "6px 14px", borderRadius: 20, fontSize: "0.82rem",
    border: `1px solid ${active ? "var(--ink)" : "var(--ln)"}`,
    background: active ? "var(--ink)" : "#fff",
    color: active ? "#fff" : "var(--ink)",
    cursor: "pointer", fontWeight: active ? 600 : 400,
  } as React.CSSProperties);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      <Header rightLabel="해외 활동 탐색" />

      <div style={{ display: "flex", flex: 1, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px" }}>
        <Sidebar />

        <main style={{ flex: 1, padding: "24px 32px", minWidth: 0 }}>
          {/* 헤더 */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: "0.72rem", letterSpacing: "0.14em", color: "var(--ac)", fontWeight: 600, marginBottom: 10 }}>
              ● EXPLORE YOUR POSSIBILITIES
            </div>
            <h2 style={{ margin: "0 0 6px", fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.04em" }}>
              프로그램·지원제도 찾기
            </h2>
            <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--mu)" }}>
              관심 있는 국가와 목적에 맞는 해외 활동 경로와 지원을 찾아보세요.
            </p>
          </div>

          {/* 필터 카드 */}
          <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "20px 24px", marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, border: "1px solid var(--ln)", borderRadius: 10, padding: "10px 14px", marginBottom: 16 }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.8">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="이름이나 키워드로 검색"
                style={{ flex: 1, border: "none", outline: "none", fontSize: "0.88rem", background: "transparent" }} />
            </div>

            <div style={{ display: "flex", gap: 8, marginBottom: 14, alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", gap: 6 }}>
                {TYPES.map(t => <button key={t} onClick={() => setTypeFilter(t)} style={chipStyle(typeFilter === t)}>{t}</button>)}
              </div>
              <button onClick={() => { setTypeFilter("전체"); setCountryFilter("전체"); setPurposeFilter("전체"); setSearch(""); setCompareIds([]); }}
                style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", fontSize: "0.8rem", color: "var(--mu)", cursor: "pointer" }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
                </svg>
                필터 초기화
              </button>
            </div>

            <div style={{ fontSize: "0.78rem", color: "var(--mu)", marginBottom: 14 }}>
              <strong>프로그램</strong>은 해외 활동을 위한 경로, <strong>지원제도</strong>는 교육·비용·취업 연계 지원이에요.
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: "0.78rem", color: "var(--mu)", width: 24, flexShrink: 0 }}>국가</span>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {COUNTRIES.map(c => (
                  <button key={c} onClick={() => setCountryFilter(c)} style={chipStyle(countryFilter === c)}>
                    {c !== "전체" && <FlagSvg country={c} size={18} />}{c}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: "0.78rem", color: "var(--mu)", width: 24, flexShrink: 0 }}>목적</span>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {PURPOSES.map(p => <button key={p} onClick={() => setPurposeFilter(p)} style={chipStyle(purposeFilter === p)}>{p}</button>)}
              </div>
            </div>
          </div>

          {/* 결과 카운트 */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <span style={{ fontSize: "0.85rem", color: "var(--ink)" }}>
              총 <strong>{filtered.length}개</strong>{" "}
              <span style={{ color: "var(--mu)", fontSize: "0.8rem" }}>
                프로그램 {filtered.filter(p => p.type === "프로그램").length} · 지원제도 {filtered.filter(p => p.type === "지원제도").length}
              </span>
            </span>
            {compareIds.length > 0 && (
              <span style={{ fontSize: "0.8rem", color: "var(--ac)", fontWeight: 600 }}>
                {compareIds.length}개 선택됨 {compareIds.length >= 2 ? "· 아래에서 비교 중" : "· 1개 더 선택하면 비교"}
              </span>
            )}
          </div>

          {/* 비교표 — 필터 아래, 리스트 위 */}
          {comparePrograms.length >= 2 && (
            <div style={{ marginBottom: 20, background: "#fff", border: "1.5px solid var(--ac)", borderRadius: 16, overflow: "hidden" }}>
              <div style={{ padding: "14px 24px", borderBottom: "1px solid var(--ln)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#f7f9ff" }}>
                <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--ink)", display: "flex", alignItems: "center", gap: 8 }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--ac)" strokeWidth="2">
                    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
                  </svg>
                  비교표
                  <span style={{ fontSize: "0.8rem", fontWeight: 400, color: "var(--mu)" }}>{comparePrograms.length}개 선택됨</span>
                </div>
                <button onClick={() => setCompareIds([])} style={{ background: "none", border: "none", fontSize: "0.8rem", color: "var(--mu)", cursor: "pointer" }}>전체 해제</button>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                  <thead>
                    <tr style={{ background: "#f7f8fa" }}>
                      <th style={{ padding: "12px 20px", textAlign: "left", fontWeight: 600, color: "var(--mu)", fontSize: "0.78rem", width: 100 }}>항목</th>
                      {comparePrograms.map(p => (
                        <th key={p.id} style={{ padding: "12px 20px", textAlign: "left", fontWeight: 700, color: "var(--ink)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            {p.country && <FlagSvg country={p.country} size={18} />}{p.name}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {COMPARE_ROWS.map((row, ri) => (
                      <tr key={ri} style={{ borderTop: "1px solid var(--ln)", background: ri % 2 === 0 ? "#fff" : "#fafbfc" }}>
                        <td style={{ padding: "12px 20px", fontWeight: 600, color: "var(--mu)", fontSize: "0.78rem", whiteSpace: "nowrap" }}>{row.label}</td>
                        {comparePrograms.map(p => <td key={p.id} style={{ padding: "12px 20px", color: "var(--ink)", lineHeight: 1.5 }}>{row.render(p)}</td>)}
                      </tr>
                    ))}
                    <tr style={{ borderTop: "1px solid var(--ln)" }}>
                      <td style={{ padding: "12px 20px", fontWeight: 600, color: "var(--mu)", fontSize: "0.78rem" }}>공식 사이트</td>
                      {comparePrograms.map(p => (
                        <td key={p.id} style={{ padding: "12px 20px" }}>
                          <a href={p.officialUrl} target="_blank" rel="noopener noreferrer"
                            style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "0.82rem", color: "var(--ac)", textDecoration: "none", fontWeight: 500 }}>
                            바로가기 <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 7h10v10M7 17L17 7"/></svg>
                          </a>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 프로그램 목록 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filtered.map(p => {
              const isChecked = compareIds.includes(p.id);
              return (
                <div key={p.id} style={{
                  background: "#fff",
                  border: `1px solid ${isChecked ? "var(--ac)" : "var(--ln)"}`,
                  borderRadius: 14, padding: "18px 20px",
                  display: "flex", alignItems: "center", gap: 16,
                  transition: "border-color 0.15s",
                }}>
                  {/* 국기 */}
                  <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--tn)", display: "grid", placeItems: "center", flexShrink: 0, overflow: "hidden" }}>
                    {p.country ? <FlagSvg country={p.country} size={26} /> : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.6">
                        <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>
                      </svg>
                    )}
                  </div>

                  {/* 내용 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", gap: 6, marginBottom: 6, flexWrap: "wrap" }}>
                      <span style={{ fontSize: "0.72rem", fontWeight: 600, padding: "2px 8px", borderRadius: 6, background: "var(--tn)", color: "var(--ac)" }}>{p.type}</span>
                      {p.tags.map(t => <span key={t} style={{ fontSize: "0.72rem", color: "var(--mu)", padding: "2px 8px", borderRadius: 6, background: "#f0f1f5" }}>{t}</span>)}
                    </div>
                    <div style={{ fontWeight: 700, fontSize: "0.95rem", marginBottom: 4 }}>{p.name}</div>
                    <div style={{ fontSize: "0.82rem", color: "#555", marginBottom: 4 }}>{p.desc}</div>
                    <div style={{ fontSize: "0.78rem", color: "var(--mu)" }}>{p.sub}</div>
                  </div>

                  {/* 버튼 영역 */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0, alignItems: "flex-end" }}>
                    {/* 비교하기 체크박스 */}
                    <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", userSelect: "none" }}>
                      <div onClick={() => toggleCompare(p.id)} style={{
                        width: 18, height: 18, borderRadius: 5,
                        border: `1.5px solid ${isChecked ? "var(--ac)" : "#d0d3de"}`,
                        background: isChecked ? "var(--ac)" : "#fff",
                        display: "grid", placeItems: "center", cursor: "pointer", flexShrink: 0, transition: "all 0.15s",
                      }}>
                        {isChecked && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>}
                      </div>
                      <span style={{ fontSize: "0.8rem", color: isChecked ? "var(--ac)" : "var(--mu)", fontWeight: isChecked ? 600 : 400 }}>비교하기</span>
                    </label>

                    {/* 자세히 보기 버튼 */}
                    <button
                      onClick={() => router.push(`/programs/${p.id}`)}
                      style={{
                        border: "1px solid var(--ln)", background: "#fff", borderRadius: 10, padding: "8px 14px",
                        fontSize: "0.82rem", display: "flex", alignItems: "center", gap: 4,
                        color: "var(--ink)", fontWeight: 500, cursor: "pointer",
                      }}
                    >
                      자세히 보기
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M5 12h14M12 5l7 7-7 7"/>
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ fontSize: "0.78rem", color: "#ccc", textAlign: "center", marginTop: 24, paddingBottom: 32 }}>
            화면 시안을 위한 예시 목록이에요. 개인별 자격과 현재 신청 정보는 별도 확인이 필요해요.
          </div>
        </main>
      </div>

      <footer style={{ display: "flex", justifyContent: "space-between", maxWidth: 1040, margin: "0 auto", width: "100%", padding: "20px 20px", fontSize: "0.78rem", color: "#ccc" }}>
        <span>Global-In.</span>
        <span>해외에서의 다음 시작을 함께.</span>
      </footer>
    </div>
  );
}
