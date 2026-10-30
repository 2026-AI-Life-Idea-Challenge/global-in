"use client";
import { useParams, useRouter } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";

const FLAGS: Record<string, string> = {
  독일: '<rect width="30" height="7" fill="#111"/><rect y="7" width="30" height="6.5" fill="#d00"/><rect y="13.5" width="30" height="6.5" fill="#ffce00"/>',
  일본: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="5" fill="#bc2a3a"/>',
  호주: '<rect width="30" height="20" fill="#00247d"/><path d="M0 0l14 9M14 0L0 9" stroke="#fff" strokeWidth="1.6"/><path d="M7 0v9M0 4.5h14" stroke="#fff" strokeWidth="3"/><path d="M7 0v9M0 4.5h14" stroke="#cf142b" strokeWidth="1.6"/>',
  미국: '<rect width="30" height="20" fill="#fff"/><rect y="0" width="30" height="1.55" fill="#b22234"/><rect y="3.1" width="30" height="1.55" fill="#b22234"/><rect y="6.2" width="30" height="1.55" fill="#b22234"/><rect y="9.3" width="30" height="1.55" fill="#b22234"/><rect y="12.4" width="30" height="1.55" fill="#b22234"/><rect y="15.5" width="30" height="1.55" fill="#b22234"/><rect y="18.6" width="30" height="1.55" fill="#b22234"/><rect width="13" height="10.8" fill="#3c3b6e"/>',
  캐나다: '<rect width="30" height="20" fill="#fff"/><rect width="7.5" height="20" fill="#d52b1e"/><rect x="22.5" width="7.5" height="20" fill="#d52b1e"/><path d="M15 4l1.3 3 2-1-.6 4 1.7-.4-.4 1.8 1.5 1-3.5 2.4.2 2.2h-4.4l.2-2.2-3.5-2.4 1.5-1-.4-1.8 1.7.4-.6-4 2 1z" fill="#d52b1e"/>',
};

const PROGRAMS = [
  // ─── 일본 프로그램 ───
  { id: 1, type: "프로그램", country: "일본", tags: ["일본", "취업"], name: "기술·인문지식·국제업무", desc: "전문 지식과 기술을 활용해 일본에서 일하는 취업 경로.", sub: "담당 직무와 학력·경력 등 요건 확인", officialUrl: "https://www.moj.go.jp/isa/applications/status/gijinkoku.html",
    details: "일본 법무성이 지정하는 재류자격 중 하나로, 전문직 종사자를 대상으로 합니다. 법률·회계·IT·외국어 교육 등 넓은 분야에서 활용되며, 대학 졸업 또는 10년 이상 실무 경험이 필요합니다." },
  { id: 8, type: "프로그램", country: "일본", tags: ["일본", "유학·교환학생"], name: "유학 비자 (留学)", desc: "일본의 대학, 전문학교 등 교육기관에서 학업을 위한 체류 경로.", sub: "입학허가서·재정 증빙 등 요건 확인", officialUrl: "https://www.moj.go.jp/isa/applications/status/ryugaku.html",
    details: "일본의 대학, 대학원, 단기대학, 전문학교 등 교육기관에 입학하여 공부하기 위한 재류자격입니다. 입학허가서(합격통지)와 재정 능력 증빙을 갖춰 재외 일본 공관에서 신청하며, 유학생 아르바이트(자격외 활동)는 주 28시간까지 허용됩니다." },
  { id: 9, type: "프로그램", country: "일본", tags: ["일본", "워킹홀리데이"], name: "워킹홀리데이 (일본)", desc: "한국-일본 협정에 따라 일본에서 여행·체험 근로를 병행하는 경로.", sub: "연령·과거 참여 이력·이중국적 등 요건 확인", officialUrl: "https://www.mofa.go.jp/mofaj/toko/visa/working_h.html",
    details: "한·일 워킹홀리데이 협정에 따라 만 18~30세 한국 청년이 최대 1년간 일본에 체류하며 취업·여행을 병행할 수 있는 비자입니다. 취업 종류와 기간에 제한이 있으며, 동일 고용주 아래 3개월 초과 취업은 제한됩니다. 재외 일본 공관에서 신청 가능합니다." },

  // ─── 독일 프로그램 ───
  { id: 3, type: "프로그램", country: "독일", tags: ["독일", "취업"], name: "기회카드 (Chancenkarte)", desc: "독일에서 일자리를 찾기 위한 체류 경로.", sub: "자격 인정 또는 점수 경로·언어·생계 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/opportunity-card",
    details: "2024년 도입된 독일의 새로운 이민 제도로, 숙련 인력이 독일 현지에서 직접 구직 활동을 할 수 있도록 최대 1년간 체류를 허가합니다. 점수 기반 평가(독일어, 경력, 연령, 학력 등)를 통해 선발합니다." },
  { id: 10, type: "프로그램", country: "독일", tags: ["독일", "취업"], name: "EU 블루카드", desc: "고학력 전문직을 위한 독일 취업 및 장기 체류 경로.", sub: "학위 인정·고용계약·최소임금 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/eu-blue-card",
    details: "EU 블루카드는 EU 외 고학력 전문 인력을 위한 특별 거주 제도로, 독일 내 취업 및 장기 체류를 허가합니다. 독일 또는 외국 대학 학위 인정, 최소 임금 기준을 충족하는 고용계약이 필요하며, IT 직종 등 일부 분야는 학위 없이도 신청 가능합니다. 영주권 신청 기간도 단축됩니다." },
  { id: 11, type: "프로그램", country: "독일", tags: ["독일", "취업"], name: "숙련노동자 비자 (Fachkräfte)", desc: "독일 내 직업훈련 또는 학위 기반으로 취업하는 경로.", sub: "자격 인정·고용계약 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/skilled-immigration",
    details: "독일의 숙련노동자 이민법(Fachkräfteeinwanderungsgesetz)에 따라 직업 훈련 수료자 또는 대학 학위 소지자가 독일에서 취업할 수 있는 경로입니다. 독일 당국의 자격 인정 절차(Anerkennung)가 필요하며, 관련 분야의 고용계약이 있어야 합니다." },
  { id: 12, type: "프로그램", country: "독일", tags: ["독일", "유학·교환학생"], name: "독일 유학 비자", desc: "독일의 대학 또는 동등 교육기관에서 학업을 위한 경로.", sub: "입학허가·재정 증빙·어학 능력 등 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/student-visa",
    details: "독일 국립·사립 대학교 또는 동등 교육기관의 정규 과정 입학을 위한 비자입니다. 입학허가서, 독일어 또는 영어 어학 능력 증빙, 재정 증빙(차단 계좌 등)이 필요합니다. 독일은 대부분의 국립대학에서 학비가 없어 유학 비용이 낮은 편입니다." },
  { id: 13, type: "프로그램", country: "독일", tags: ["독일", "유학·교환학생"], name: "대학입학 준비 비자", desc: "독일 대학 입학 전 어학연수·입학수속 준비를 위한 체류 경로.", sub: "입학 예정·어학 과정 등 요건 확인", officialUrl: "https://www.make-it-in-germany.com/en/visa-residence/types/language-course-higher-education",
    details: "독일 대학 진학 전 어학 능력 향상 또는 입학 수속 준비를 위해 최대 2년간 체류할 수 있는 비자입니다. 어학 과정 등록 확인서나 대학 입학 조건부 허가서가 필요하며, 어학 목표 달성 후 학생 비자로 전환이 가능합니다." },
  { id: 14, type: "프로그램", country: "독일", tags: ["독일", "워킹홀리데이"], name: "워킹홀리데이 (독일-한국)", desc: "한국-독일 협정에 따라 독일에서 여행·체험 근로를 병행하는 경로.", sub: "연령·과거 참여 이력 등 요건 확인", officialUrl: "https://korea.diplo.de/kr-ko/visa-einreise/working-holiday/1598618",
    details: "한·독 문화 교류 협정에 따라 만 18~30세 한국 청년이 최대 1년간 독일에서 취업과 여행을 병행할 수 있는 비자입니다. 1인 1회 한정이며, 주된 목적은 휴가로 취업은 부수적이어야 합니다. 주한 독일 대사관에서 신청합니다." },

  // ─── 호주 프로그램 ───
  { id: 4, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워킹홀리데이 비자 (417) 1차", desc: "호주에서 여행하며 단기 근로를 병행하는 경로.", sub: "여권 국가·연령·이전 참여 이력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417",
    details: "만 18~30세(일부 국가 35세)의 청년을 대상으로 호주 체류와 취업을 동시에 허용하는 비자입니다. 한국 국적자는 최대 3년까지 연장이 가능하며, 지역 근무 조건 충족 시 2·3차 비자를 받을 수 있습니다." },
  { id: 15, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워킹홀리데이 비자 (417) 2차", desc: "1차 비자 후 지역사업장 근무 기간을 채워 연장하는 경로.", sub: "1차 비자 보유·지역사업장 근무 88일 이상 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417",
    details: "417 비자 1차 기간 중 지정 지역(농업·건설·광업 등)에서 88일 이상 근무한 경우 신청할 수 있는 2차 워킹홀리데이 비자입니다. 1차와 동일하게 1년 기간이 부여되며, 지역 근무 요건을 충족하면 3차까지 연장 가능합니다." },
  { id: 16, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워킹홀리데이 비자 (417) 3차", desc: "2차 비자 후 추가 지역사업장 근무로 한 번 더 연장하는 경로.", sub: "2차 비자 보유·지역사업장 근무 88일 이상 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417",
    details: "417 비자 2차 기간 중 지정 지역에서 추가로 88일 이상 근무한 경우 신청할 수 있는 3차 워킹홀리데이 비자입니다. 3차까지 최대 3년 호주 체류가 가능하며, 농업·어업·광업 등 특정 지역 근무 기록이 필요합니다." },
  { id: 17, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워크앤홀리데이 비자 (462) 1차", desc: "지정 협정국 여권으로 신청하는 호주 워킹홀리데이 경로 (한국 포함).", sub: "협정국 여권·연령·학력·어학 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-and-holiday-462",
    details: "462 비자는 한국 포함 44개 협정국 청년을 위한 워킹홀리데이 비자입니다. 만 18~30세, 2년 이상 대학 교육 이수, 기능성 영어 능력 증빙이 필요하며, 연간 쿼터 제한이 있습니다. 지역 근무 조건 충족 시 2·3차 비자 신청이 가능합니다." },
  { id: 18, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워크앤홀리데이 비자 (462) 2차", desc: "1차 비자 후 지역사업장 근무로 연장하는 경로.", sub: "1차 비자 보유·지역사업장 근무 기간 충족 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-and-holiday-462",
    details: "462 비자 1차 기간 중 지정 지역에서 88일(또는 3개월) 이상 근무한 경우 2차 비자를 신청할 수 있습니다. 지역 근무 인정 직종과 지역 범위는 정부 웹사이트에서 확인이 필요하며, 비자 기간은 추가 1년입니다." },
  { id: 19, type: "프로그램", country: "호주", tags: ["호주", "워킹홀리데이"], name: "워크앤홀리데이 비자 (462) 3차", desc: "2차 비자 후 추가 근무로 한 번 더 연장하는 경로.", sub: "2차 비자 보유·추가 지역근무 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-and-holiday-462",
    details: "462 비자 2차 기간 중 지역 지정 직종에서 추가 근무 요건을 충족한 경우 3차 비자를 신청할 수 있습니다. 최대 3년간 호주 체류가 가능하며, 지역별 근무 조건은 임시 기술 이민 부족 직종 목록을 기준으로 합니다." },
  { id: 20, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "수요기술 취업 비자 (482) Core", desc: "수요직종에 해당하는 고용주 후원 임시취업 경로.", sub: "수요직종·고용주 후원·어학·경력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
    details: "호주 고용주의 후원을 받아 수요 직종(MLTSSL)에 취업하는 임시 비자입니다. 최대 4년까지 체류 가능하며, 조건 충족 시 영주권(186 비자) 전환이 가능합니다. 영어 능력 증빙과 2년 이상 관련 직종 경력이 필요합니다." },
  { id: 21, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "수요기술 취업 비자 (482) 노동협약", desc: "노동협약을 통한 고용주 후원 임시취업 경로.", sub: "협약 고용주·해당 직종 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
    details: "호주 정부와 체결한 노동협약(Labour Agreement)을 보유한 고용주가 후원하는 482 비자 경로입니다. 표준 직종 목록에 없는 직종도 협약을 통해 후원이 가능하며, 협약 조건에 따라 요건이 달라집니다." },
  { id: 22, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "수요기술 취업 비자 (482) 전문기술", desc: "고임금 전문직을 위한 고용주 후원 임시취업 경로.", sub: "고임금 요건·고용주 후원 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-skill-shortage-482",
    details: "연봉이 일정 기준 이상(고임금 임계치)인 고임금 전문직 종사자를 위한 482 비자 경로입니다. 직종 목록 제한이 없고 영어 면제 혜택이 있는 경우도 있어 고학력·고연봉 직군에 유리합니다." },
  { id: 23, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "지역기술임시 비자 (491)", desc: "지역 주정부 또는 가족의 추천을 받아 지역에서 취업하는 임시 경로.", sub: "주정부 추천·수요직종·어학·점수 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-work-regional-provisional-491",
    details: "호주 지방·지역에서 거주·취업하는 조건으로 주정부 또는 지역 내 가족의 추천을 받아 신청하는 5년 임시 비자입니다. 3년 거주 및 소득 요건 충족 시 영주권(191 비자)으로 전환이 가능합니다." },
  { id: 24, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "지역고용후원 비자 (494) 고용주 후원", desc: "지역 고용주의 후원을 받아 지역에서 취업하는 임시 경로.", sub: "지역 고용주 후원·수요직종·어학·경력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494",
    details: "호주 지방·지역에 소재한 고용주가 후원하는 5년 임시 취업 비자입니다. 지역 수요 직종(RSMS 리스트)에 해당해야 하며, 3년 거주 및 소득 요건 충족 후 영주권(191 비자)으로 전환이 가능합니다." },
  { id: 52, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "지역고용후원 비자 (494) 노동협약", desc: "노동협약을 통한 지역 고용주 후원 임시취업 경로.", sub: "협약 고용주·지역 근무·해당 직종 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494",
    details: "노동협약(Labour Agreement)을 보유한 지방·지역 고용주가 후원하는 494 비자 경로입니다. 협약에 따라 표준 직종 목록 외 직종도 포함될 수 있으며, 3년 거주·소득 요건 충족 시 영주권으로 전환 가능합니다." },
  { id: 25, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "트레이닝 비자 (407)", desc: "직업 훈련 또는 업무 관련 연수를 위한 임시 체류 경로.", sub: "후원 기관·훈련 계획·재정 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407",
    details: "호주에서 직업 기술 향상 또는 업무 관련 훈련을 받기 위한 임시 비자입니다. 호주 내 후원 기관(조직)이 필요하며, 최대 2년까지 체류가 가능합니다. 직업 훈련, 산업 연수, 직업 개발 연수 세 가지 활동 유형 중 하나를 선택합니다." },
  { id: 26, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "고용주 노미네이트 비자 (186) 직접입국", desc: "호주 고용주가 직접 추천하는 영주권 경로.", sub: "고용주 추천·수요직종·어학·경력 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186",
    details: "호주 고용주의 추천을 받아 직접 영주권을 신청하는 경로입니다. MLTSSL 직종에 해당해야 하며, 3년 이상 관련 경력과 영어 능력 증빙이 필요합니다. 고용주는 승인된 후원자여야 합니다." },
  { id: 27, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "고용주 노미네이트 비자 (186) 임시→영주", desc: "임시취업(482)에서 고용주 추천 영주권으로 전환하는 경로.", sub: "482 비자 3년·동일 고용주·수요직종 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186",
    details: "482 비자 소지자가 동일 고용주 아래 3년 이상 근무한 후 영주권으로 전환하는 경로입니다. 직종이 영주 취업 리스트에 있어야 하며, 나이 제한(45세 미만), 영어 능력 기준을 충족해야 합니다." },
  { id: 28, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "고용주 노미네이트 비자 (186) 노동협약", desc: "노동협약을 통한 고용주 추천 영주권 경로.", sub: "협약 고용주·해당 직종 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186",
    details: "노동협약(Labour Agreement)을 체결한 고용주가 추천하는 영주권 경로입니다. 협약에 따라 표준 요건이 일부 완화되거나 직종 범위가 확대될 수 있으며, 개별 협약 조건을 반드시 확인해야 합니다." },
  { id: 29, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "독립기술 이민 비자 (189)", desc: "고용주나 가족 보증 없이 점수제로 신청하는 영주권 경로.", sub: "EOI 제출·초청·수요직종·점수·어학 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189",
    details: "호주 정부의 SkillSelect 시스템에 관심 표명서(EOI)를 제출한 후 초청(ITA)을 받아 영주권을 신청하는 경로입니다. 점수(65점 이상)와 직종(MLTSSL)이 핵심이며, 나이·학력·영어·경력·호주 내 자격 인정 등이 점수에 반영됩니다." },
  { id: 30, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "주정부 노미네이트 비자 (190)", desc: "호주 주/테리토리 정부의 추천을 받아 신청하는 영주권 경로.", sub: "주정부 추천·수요직종·점수·어학 등 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-nominated-190",
    details: "호주 각 주·테리토리 정부의 추천을 받아 영주권을 신청하는 경로입니다. 주정부 추천 시 5점이 추가되며, 각 주마다 요건과 수요 직종이 다릅니다. EOI 제출 후 주정부 추천 → 연방 정부 초청 순서로 진행됩니다." },
  { id: 31, type: "프로그램", country: "호주", tags: ["호주", "취업"], name: "지역영주 비자 (191)", desc: "지역 임시비자(491/494) 소지 후 3년 경력으로 신청하는 영주권 경로.", sub: "지역 임시비자 3년·소득 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/permanent-residence-regional-191",
    details: "491 또는 494 비자로 호주 지방·지역에서 최소 3년 거주 및 소득 기준 충족 시 신청할 수 있는 영주권입니다. 지역 거주 의무와 최소 연소득 기준을 반드시 충족해야 하며, 신청자와 동반 가족 모두 조건을 갖춰야 합니다." },
  { id: 32, type: "프로그램", country: "호주", tags: ["호주", "유학·교환학생"], name: "학생 비자 (500)", desc: "호주의 교육기관에 등록해 정규 과정을 이수하기 위한 경로.", sub: "입학허가(CoE)·재정·어학·GTE 요건 확인", officialUrl: "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500",
    details: "CRICOS 등록 교육기관에서 정규 과정을 공부하기 위한 호주 학생 비자입니다. 입학확인서(CoE), 재정 능력 증빙, 영어 능력 증빙, 진정한 임시 입국자(GTE) 요건을 충족해야 합니다. 주당 40시간 이내 아르바이트가 허용됩니다." },

  // ─── 미국 프로그램 ───
  { id: 5, type: "프로그램", country: "미국", tags: ["미국", "유학·교환학생"], name: "학생 비자 (F-1)", desc: "미국의 대학 등 교육기관에서 학업을 위한 경로.", sub: "교육기관·학업 과정·I-20 등 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
    details: "미국 SEVP 승인 학교에서 정규 과정 수학을 위한 비자로, 학교로부터 I-20 양식을 받은 뒤 미국 대사관에서 인터뷰를 통해 발급받습니다. 졸업 후 OPT를 통해 최대 3년간 미국 내 취업이 가능합니다." },
  { id: 33, type: "프로그램", country: "미국", tags: ["미국", "유학·교환학생"], name: "J-1 대학생 (Student)", desc: "미국 교육기관에서 학업을 위한 교환 방문자 경로.", sub: "교육기관·DS-2019·재정·어학 요건 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html",
    details: "J-1 교환 방문자 비자 중 대학생 카테고리로, 미국 대학·대학원에서 정규 학업을 위한 경로입니다. 후원 기관으로부터 DS-2019 양식을 받아야 하며, F-1과 달리 교환 학생 프로그램 협약을 통해 진행됩니다. 귀국 의무(2년 체류) 조건이 있을 수 있습니다." },
  { id: 34, type: "프로그램", country: "미국", tags: ["미국", "취업"], name: "H-1B 비자", desc: "미국 고용주가 후원하는 전문직 취업 비자.", sub: "학위·고용주 후원·추첨·LCA 등 요건 확인", officialUrl: "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
    details: "미국 고용주가 후원하는 전문직 취업 비자로, 학사 이상 학위와 관련 직종 고용 오퍼가 필요합니다. 매년 4월 추첨(Lottery)을 통해 쿼터가 배분되며, 초기 3년 후 3년 연장이 가능합니다. 영주권(그린카드) 스폰서 경로와 연계됩니다." },
  { id: 35, type: "프로그램", country: "미국", tags: ["미국", "취업"], name: "J-1 인턴십", desc: "인턴십 형태로 미국에서 실무 경험을 쌓는 교환 방문자 경로.", sub: "재학 중이거나 졸업 1년 이내·DS-2019·후원기관 요건 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html",
    details: "J-1 교환 방문자 비자 중 인턴십 카테고리로, 재학생이나 졸업 1년 이내 청년이 미국 기업에서 인턴십을 경험하는 경로입니다. 최대 12개월이며, 후원 기관을 통해 DS-2019를 발급받아야 합니다." },
  { id: 36, type: "프로그램", country: "미국", tags: ["미국", "취업"], name: "J-1 연수 (Trainee)", desc: "연수 형태로 미국에서 직업 훈련을 받는 교환 방문자 경로.", sub: "학위 또는 경력·DS-2019·후원기관 요건 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html",
    details: "J-1 교환 방문자 비자 중 연수(Trainee) 카테고리로, 학위 소지자 또는 일정 경력을 가진 전문인이 미국에서 직업 훈련을 받는 경로입니다. 최대 18개월이며, 후원 기관의 승인된 훈련 계획서가 필요합니다." },
  { id: 37, type: "프로그램", country: "미국", tags: ["미국", "워킹홀리데이"], name: "J-1 Summer Work Travel", desc: "대학생이 미국에서 여름방학 동안 일하며 여행하는 교환 방문자 경로.", sub: "재학 중·고용계약·DS-2019·후원기관 요건 확인", officialUrl: "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html",
    details: "외국 대학의 재학생이 미국에서 여름방학 기간(최대 4개월) 동안 취업하며 여행을 경험하는 J-1 비자 카테고리입니다. 미국 내 취업 오퍼를 먼저 받거나 후원 기관의 알선을 통해 고용 후 DS-2019를 발급받아 신청합니다." },
  { id: 38, type: "프로그램", country: "미국", tags: ["미국", "장학·연수"], name: "WEST 프로그램", desc: "한국 대학생이 미국에서 인턴십·연수를 경험하는 한미 교육 교류 프로그램.", sub: "재학생·어학·선발 심사 등 요건 확인", officialUrl: "https://www.niied.go.kr/web/niied/nid/niied_board/5749",
    details: "Work, English Study and Travel의 약자로, 한·미 교육 교류 협정에 따라 한국 대학(원)생이 미국에서 어학연수와 인턴십을 동시에 경험하는 프로그램입니다. 국립국제교육원(NIIED)이 주관하며 서류·면접 전형을 통해 선발합니다." },

  // ─── 캐나다 프로그램 ───
  { id: 6, type: "프로그램", country: "캐나다", tags: ["캐나다", "취업"], name: "고용주 지정 취업허가 (ESWP)", desc: "특정 캐나다 고용주를 위해 발급되는 임시 취업 경로.", sub: "고용주 LMIA 또는 면제 요건·직종 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/permit/temporary/apply.html",
    details: "특정 고용주와 직종에 한해 취업을 허용하는 캐나다 임시 취업허가입니다. 고용주가 LMIA(노동시장영향평가)를 받거나 LMIA 면제 조건(국제 협정, 이민자 이익 등)에 해당하는 경우 신청 가능합니다. 허가 기간은 고용 계약 기간에 따라 다릅니다." },
  { id: 39, type: "프로그램", country: "캐나다", tags: ["캐나다", "워킹홀리데이"], name: "국제경험 캐나다 워킹홀리데이 (IEC)", desc: "협정 국가 청년을 위한 캐나다 워킹홀리데이 경로.", sub: "연령·Pool 지원·고용 오퍼 등 요건 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/activities.html",
    details: "IEC(International Experience Canada) 워킹홀리데이는 한국 포함 협정국 만 18~35세 청년이 최대 2년간 캐나다에서 체류·취업할 수 있는 프로그램입니다. 매년 풀(Pool)에 프로필을 등록하면 무작위 초청 후 취업허가를 신청합니다." },
  { id: 40, type: "프로그램", country: "캐나다", tags: ["캐나다", "취업"], name: "졸업 후 취업허가 (PGWP)", desc: "캐나다 공인 학교(DLI) 졸업자를 위한 취업허가 경로.", sub: "DLI 졸업·학업 기간 등 요건 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation.html",
    details: "캐나다 지정학교(DLI)를 졸업한 후 취업허가를 받아 캐나다에서 일할 수 있는 경로입니다. 학업 기간에 따라 최대 3년 허가가 주어지며, 캐나다 내 취업 경력을 쌓아 영주권(Express Entry 등) 신청의 발판이 됩니다." },
  { id: 41, type: "프로그램", country: "캐나다", tags: ["캐나다", "유학·교환학생"], name: "학생 비자 (Study Permit)", desc: "캐나다 지정학교(DLI)에서 6개월 이상 학업을 위한 경로.", sub: "DLI 입학허가·재정·어학·목적 설명 요건 확인", officialUrl: "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit.html",
    details: "캐나다 이민부가 지정한 DLI(Designated Learning Institution)에서 6개월 이상 학업을 하기 위한 허가증입니다. 입학허가서, 재정 증빙, 어학 능력 증빙, 귀국 의지 입증이 필요하며, 풀타임 학생은 캠퍼스 내 근로와 일부 조건의 캠퍼스 외 근로도 허용됩니다." },

  // ─── 지원제도 (여러 국가) ───
  { id: 2, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "K-Move스쿨", desc: "해외취업에 필요한 어학·직무 연수와 취업 연계를 지원.", sub: "맞춤형 교육·연수비·일부 취업 지원", officialUrl: "https://www.worldjob.or.kr/ovsea/sdytrn.do",
    details: "한국산업인력공단이 운영하는 해외취업 지원 사업으로, 국가·직종별 맞춤형 교육과 함께 취업 연계까지 지원합니다. 훈련비 및 체재비 일부 지원이 가능하며, 매년 모집 공고를 통해 선발합니다." },
  { id: 7, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "해외취업정착지원금", desc: "해외취업 후 초기 정착과 경력 개발을 돕는 지원.", sub: "해외취업자의 초기 정착을 위한 지원금", officialUrl: "https://kmovefair.worldjob.or.kr/ovsea/sbsd.do?menuId=1000000041",
    details: "고용노동부와 한국산업인력공단이 지원하는 사업으로, 해외에 취업한 청년에게 초기 정착금을 지급합니다. 지원 요건(연령·소득 등)과 지원금액은 매년 변경될 수 있으므로 월드잡플러스 공식 사이트에서 최신 공고를 확인하세요." },
  { id: 42, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "해외취업알선", desc: "해외 고용주와 구직자를 연결하는 취업 알선 서비스.", sub: "월드잡플러스 가입·이력서 등록 등 확인", officialUrl: "https://www.worldjob.or.kr/ovsea/empymn.do?menuId=1000000040",
    details: "한국산업인력공단 월드잡플러스를 통해 해외 고용주와 구직자를 직접 연결하는 서비스입니다. 구직자는 영문 이력서를 등록하고, 정기적으로 개최되는 해외 취업 박람회 및 기업 채용 행사에 참여해 취업 기회를 얻을 수 있습니다." },
  { id: 43, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "K-MOVE 멘토링", desc: "해외취업 경험자(멘토)와 구직자(멘티)를 연결하는 지원.", sub: "멘티 신청·매칭 후 온·오프라인 멘토링 진행", officialUrl: "https://kmovefair.worldjob.or.kr/kmove/intro.do",
    details: "해외취업에 성공한 선배(멘토)와 준비 중인 청년(멘티)을 연결하여 실질적인 취업 노하우와 현지 경험을 공유하는 프로그램입니다. 온·오프라인 방식으로 진행되며, 국가별·직종별 맞춤 멘토 매칭을 지원합니다." },
  { id: 44, type: "지원제도", country: null, tags: ["여러 국가", "취업"], name: "해외일경험지원사업 WELL", desc: "단기 해외 일경험을 통한 청년 글로벌 역량 강화 지원.", sub: "재학·졸업 청년 대상·파견 기업 등 요건 확인", officialUrl: "https://www.worldjob.or.kr/ovsea/well.do",
    details: "Work Experience for Language and Leadership의 약자로, 청년들이 해외 기업에서 단기 일경험을 통해 글로벌 역량을 키울 수 있도록 지원하는 사업입니다. 항공료·체재비 일부를 지원하며, 현지 기업 파견을 통해 실무 경험을 제공합니다." },

  // ─── 지원제도 (국가별) ───
  { id: 45, type: "지원제도", country: "미국", tags: ["미국", "장학·연수"], name: "한·미 대학생 연수 WEST", desc: "미국에서 인턴십·연수를 경험하는 한미 교육 교류 프로그램 참가 지원.", sub: "참가비·체재비·어학연수비 일부 지원", officialUrl: "https://www.niied.go.kr/web/niied/nid/niied_board/5749",
    details: "국립국제교육원(NIIED)이 주관하는 WEST 프로그램 참가자를 위한 지원 사업입니다. 합격자에게 어학연수비 대출 및 일부 참가 비용 지원이 제공됩니다. 매년 상반기에 모집 공고가 나오며, 서류·면접 전형을 거쳐 선발합니다." },
  { id: 46, type: "지원제도", country: "미국", tags: ["미국", "장학·연수"], name: "WEST 어학연수비 대출", desc: "WEST 프로그램 참가자를 위한 어학연수비 대출 지원.", sub: "WEST 합격자·대출 한도·상환 조건 확인", officialUrl: "https://www.kosaf.go.kr/ko/tuition.do?pg=PTHDWestAply_01M&ttab1=2",
    details: "한국장학재단에서 WEST 프로그램 합격자를 대상으로 미국 현지 어학연수 비용을 저금리로 대출해주는 지원 사업입니다. 대출 한도와 상환 조건은 매년 변경될 수 있으며, 한국장학재단 홈페이지에서 최신 내용을 확인하세요." },
  { id: 47, type: "지원제도", country: "일본", tags: ["일본", "장학·연수"], name: "2027 MEXT 연구유학생 장학", desc: "일본 문부과학성이 지원하는 연구유학생 장학 프로그램.", sub: "대학 추천·연령·학업 성적 등 요건 확인", officialUrl: "https://www.kr.emb-japan.go.jp/itpr_ko/news_20260512.html",
    details: "일본 문부과학성(MEXT)이 외국인 유학생에게 수업료·생활비·왕복 항공료를 지원하는 장학 프로그램입니다. 한국 내 대학 추천(학교 추천)과 일본 대사관 접수(대사관 추천) 두 가지 경로가 있으며, 연구유학생으로 일본 대학원에서 연구를 진행합니다." },
  { id: 48, type: "지원제도", country: "호주", tags: ["호주", "장학·연수"], name: "Research Training Program (RTP)", desc: "호주 정부가 지원하는 대학원 연구과정 장학 프로그램.", sub: "호주 대학 입학·연구 계획 등 요건 확인", officialUrl: "https://www.education.gov.au/research-block-grants/research-training-program",
    details: "호주 정부가 대학을 통해 석·박사 연구과정 학생에게 학비와 일부 생활비를 지원하는 장학 프로그램입니다. 국제 학생도 지원 대상이 될 수 있으며, 각 대학별로 선발 기준과 지원 규모가 다릅니다. 입학 지원 시 RTP 장학금 신청을 함께 진행합니다." },
  { id: 49, type: "지원제도", country: "미국", tags: ["미국", "장학·연수"], name: "2027 풀브라이트 대학원 장학", desc: "미한교육위원회가 운영하는 미국 대학원 장학 프로그램.", sub: "한국 국적·학업 성적·어학·연구계획 등 요건 확인", officialUrl: "https://www.fulbright.or.kr/grant/graduate/",
    details: "한·미 교육 교류재단인 미한교육위원회가 운영하는 풀브라이트 장학금은 한국 학생이 미국 대학원에서 학위 과정을 이수할 수 있도록 수업료, 생활비, 항공비를 지원합니다. 매년 상반기 서류 접수 후 인터뷰를 통해 최종 선발합니다." },
  { id: 50, type: "지원제도", country: "독일", tags: ["독일", "장학·연수"], name: "베를린자유대 독일장학 (Deutschlandstipendium)", desc: "베를린자유대학교의 독일장학금 프로그램.", sub: "재학생·성적·사회 참여 등 요건 확인", officialUrl: "https://www.fu-berlin.de/en/sites/deutschlandstipendium",
    details: "독일 연방정부와 민간 기부자가 공동 재원을 마련하는 독일장학금(Deutschlandstipendium) 제도로, 베를린자유대학교 재학생을 대상으로 합니다. 학업 성적과 사회적 참여를 기준으로 선발하며, 매달 일정 금액이 지급됩니다." },
  { id: 51, type: "지원제도", country: "캐나다", tags: ["캐나다", "장학·연수"], name: "워털루 국제석사 우수장학 (IMAE)", desc: "워털루대학교의 국제 석사과정 우수 장학금.", sub: "입학 예정 국제 석사생·성적 요건 확인", officialUrl: "https://uwaterloo.ca/current-graduate-students/awards-and-funding/international-student-funding",
    details: "캐나다 워털루대학교가 우수한 국제 신입 석사과정 학생에게 제공하는 장학금입니다. 별도 신청 없이 입학 지원 시 자동으로 심사되며, 학업 성적 및 연구 역량을 기준으로 선발합니다. 수혜 조건은 해마다 달라질 수 있으니 공식 사이트에서 확인하세요." },
];

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

export default function ProgramDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params?.id);
  const program = PROGRAMS.find(p => p.id === id);

  if (!program) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
        <Header rightLabel="프로그램 상세" />
        <div style={{ display: "flex", flex: 1, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px" }}>
          <Sidebar />
          <main style={{ flex: 1, padding: "24px 32px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ textAlign: "center" }}>
              <p style={{ color: "var(--mu)", marginBottom: 16 }}>프로그램을 찾을 수 없어요.</p>
              <button onClick={() => router.push("/programs")} style={{ background: "var(--ink)", color: "#fff", border: "none", borderRadius: 10, padding: "10px 20px", cursor: "pointer" }}>
                목록으로
              </button>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
      <Header rightLabel="프로그램 상세" />

      <div style={{ display: "flex", flex: 1, maxWidth: 1040, margin: "20px auto 0", width: "100%", padding: "0 20px" }}>
        <Sidebar />

        <main style={{ flex: 1, padding: "24px 32px", minWidth: 0 }}>
          {/* 뒤로가기 */}
          <button
            onClick={() => router.back()}
            style={{
              display: "flex", alignItems: "center", gap: 6, fontSize: "0.82rem",
              color: "var(--mu)", background: "none", border: "none", cursor: "pointer",
              padding: "4px 0", marginBottom: 24,
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 5l-7 7 7 7"/>
            </svg>
            목록으로 돌아가기
          </button>

          {/* 헤더 카드 */}
          <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "28px 32px", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 20, flexWrap: "wrap" }}>
              {/* 국기 아이콘 */}
              <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--tn)", display: "grid", placeItems: "center", flexShrink: 0, overflow: "hidden" }}>
                {program.country ? (
                  <FlagSvg country={program.country} size={36} />
                ) : (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>
                  </svg>
                )}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                {/* 배지 */}
                <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: "0.72rem", fontWeight: 600, padding: "3px 10px", borderRadius: 6, background: "var(--tn)", color: "var(--ac)" }}>
                    {program.type}
                  </span>
                  {program.tags.map(t => (
                    <span key={t} style={{ fontSize: "0.72rem", color: "var(--mu)", padding: "3px 10px", borderRadius: 6, background: "#f0f1f5" }}>{t}</span>
                  ))}
                </div>

                <h1 style={{ margin: "0 0 8px", fontSize: "1.4rem", fontWeight: 800, letterSpacing: "-0.03em", color: "var(--ink)" }}>
                  {program.name}
                </h1>
                <p style={{ margin: 0, fontSize: "0.92rem", color: "#555", lineHeight: 1.6 }}>
                  {program.desc}
                </p>
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 16, alignItems: "start" }}>
            {/* 왼쪽: 상세 설명 + 대상 조건 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* 개요 */}
              <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "24px 28px" }}>
                <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 개요</div>
                <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--ink)", lineHeight: 1.8 }}>
                  {program.details}
                </p>
              </div>

              {/* 대상·조건 */}
              <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "24px 28px" }}>
                <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 대상·조건</div>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ac)", flexShrink: 0, marginTop: 7 }} />
                  <span style={{ fontSize: "0.88rem", color: "var(--ink)", lineHeight: 1.7 }}>{program.sub}</span>
                </div>
                <p style={{ margin: "12px 0 0", fontSize: "0.8rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  자격 조건과 신청 요건은 변경될 수 있으니, 공식 사이트에서 최신 정보를 꼭 확인하세요.
                </p>
              </div>
            </div>

            {/* 오른쪽: 액션 카드 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* 공식 사이트 */}
              <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 16, padding: "20px 22px" }}>
                <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 12 }}>● 공식 사이트</div>
                <p style={{ margin: "0 0 14px", fontSize: "0.82rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  신청 방법, 자격 요건, 최신 공지를 공식 사이트에서 확인하세요.
                </p>
                <a
                  href={program.officialUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                    width: "100%", padding: "11px 0", borderRadius: 10,
                    border: "1.5px solid var(--ink)", background: "#fff",
                    fontSize: "0.88rem", fontWeight: 600, color: "var(--ink)",
                    textDecoration: "none", boxSizing: "border-box",
                  }}
                >
                  공식 사이트 방문
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M7 7h10v10M7 17L17 7"/>
                  </svg>
                </a>
              </div>

              {/* AI 상담하기 */}
              <div style={{ background: "#fff", border: "1.5px solid var(--ac)", borderRadius: 16, padding: "20px 22px" }}>
                <div style={{ fontSize: "0.72rem", letterSpacing: "0.12em", color: "var(--ac)", fontWeight: 600, marginBottom: 10 }}>● AI 상담</div>
                <p style={{ margin: "0 0 14px", fontSize: "0.82rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  이 프로그램에 대해 궁금한 점을 AI와 함께 알아보세요.
                </p>
                <button
                  onClick={() => router.push(`/chat?program=${encodeURIComponent(program.name)}&country=${encodeURIComponent(program.country ?? "")}`)}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                    width: "100%", padding: "11px 0", borderRadius: 10,
                    border: "1.5px solid var(--ac)", background: "var(--ac)",
                    fontSize: "0.88rem", fontWeight: 700, color: "#fff",
                    cursor: "pointer", boxSizing: "border-box",
                  }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  AI와 상담하기
                </button>
              </div>

              {/* 안내 */}
              <div style={{ background: "#fff", border: "1px solid var(--ln)", borderRadius: 12, padding: "14px 16px" }}>
                <p style={{ margin: 0, fontSize: "0.76rem", color: "var(--mu)", lineHeight: 1.6 }}>
                  화면 시안을 위한 예시 정보예요. 실제 자격 요건과 신청 절차는 공식 사이트에서 확인해 주세요.
                </p>
              </div>
            </div>
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
