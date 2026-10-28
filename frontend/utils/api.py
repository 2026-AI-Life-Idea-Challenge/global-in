"""
frontend/utils/api.py
FastAPI 백엔드 통신 유틸리티
"""
import os
import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def chat_stream(session_id: str, message: str, profile: dict) -> str:
    """
    AI 에이전트에 메시지를 전송하고 응답 텍스트를 반환.
    실제 연결 전이면 더미 응답을 반환.
    """
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            json={
                "session_id": session_id,
                "message": message,
                "profile": profile,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("reply", "")
    except Exception:
        # 백엔드 미연결 시 더미 응답
        return (
            "안녕하세요! 현재 AI 상담 서버와 연결 중이에요. "
            "연결이 완료되면 맞춤 답변을 드릴게요. 😊"
        )


def search_programs(filters: dict) -> list[dict]:
    """
    프로그램·지원제도 검색.
    백엔드 미연결 시 샘플 데이터 반환.
    """
    try:
        resp = requests.get(
            f"{API_BASE}/programs",
            params=filters,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception:
        return _sample_programs(filters)


def _sample_programs(filters: dict) -> list[dict]:
    """백엔드 없을 때 보여줄 샘플 프로그램 목록."""
    samples = [
        {
            "id": "jp_employment_skilled",
            "type": "프로그램",
            "country": "일본",
            "country_emoji": "🇯🇵",
            "purpose": "취업",
            "name": "기술·인문지식·국제업무",
            "description": "전문 지식과 기술을 활용해 일본에서 일하는 취업 경로.",
            "condition_summary": "담당 직무와 학력·경력 등 요건 확인",
            "url": "https://www.naver.com/",
        },
        {
            "id": "kmove_support",
            "type": "지원제도",
            "country": "여러 국가",
            "country_emoji": "🌐",
            "purpose": "취업",
            "name": "K-Move스쿨",
            "description": "해외취업에 필요한 어학·직무 연수와 취업 연계를 지원.",
            "condition_summary": "지원 내용: 맞춤형 교육·연수비·일부 취업 지원",
            "url": "",
        },
        {
            "id": "de_chancenkarte",
            "type": "프로그램",
            "country": "독일",
            "country_emoji": "🇩🇪",
            "purpose": "취업",
            "name": "기회카드 (Chancenkarte)",
            "description": "독일에서 일자리를 찾기 위한 체류 경로.",
            "condition_summary": "자격 인정 또는 점수 경로·언어·생계 요건 확인",
            "url": "",
        },
        {
            "id": "au_wh_417",
            "type": "프로그램",
            "country": "호주",
            "country_emoji": "🇦🇺",
            "purpose": "워킹홀리데이",
            "name": "워킹홀리데이 비자 (417)",
            "description": "호주에서 여행하며 단기 근로를 병행하는 경로.",
            "condition_summary": "나이·국가·연령 이전 참여 이력 등 요건 확인",
            "url": "",
        },
        {
            "id": "us_f1_student",
            "type": "프로그램",
            "country": "미국",
            "country_emoji": "🇺🇸",
            "purpose": "유학·교환학생",
            "name": "학생 비자 (F-1)",
            "description": "미국의 대학 등 교육기관에서 학업을 위한 경로.",
            "condition_summary": "교육기관 학업 과정·I-20 등 확인",
            "url": "",
        },
        {
            "id": "ca_fsw",
            "type": "프로그램",
            "country": "캐나다",
            "country_emoji": "🇨🇦",
            "purpose": "취업",
            "name": "연방 전문인력 프로그램 (FSW)",
            "description": "해외 숙련 경력을 바탕으로 검토하는 캐나다 영주권 경로.",
            "condition_summary": "숙련 경력·공인어·학력 등 조건 확인",
            "url": "",
        },
        {
            "id": "koreit_support",
            "type": "지원제도",
            "country": "여러 국가",
            "country_emoji": "🌐",
            "purpose": "취업",
            "name": "해외취업정착지원금",
            "description": "해외취업 후 초기 정착과 경력 개발을 돕는 지원.",
            "condition_summary": "지원 내용: 해외취업자의 초기 정착을 위한 지원금",
            "url": "",
        },
    ]

    result = samples
    country = filters.get("country") or "전체"
    purpose = filters.get("purpose") or "전체"
    keyword = (filters.get("keyword") or "").strip()
    tab = filters.get("tab") or "전체"

    if tab == "프로그램":
        result = [p for p in result if p["type"] == "프로그램"]
    elif tab == "지원제도":
        result = [p for p in result if p["type"] == "지원제도"]

    if country != "전체":
        result = [p for p in result if country in p["country"]]

    if purpose != "전체":
        purpose_map = {
            "취업": "취업",
            "유학·교환학생": "유학",
            "워킹홀리데이": "워킹홀리데이",
        }
        key = purpose_map.get(purpose, purpose)
        result = [p for p in result if key in p["purpose"]]

    if keyword:
        result = [
            p for p in result
            if keyword in p["name"] or keyword in p["description"]
        ]

    return result
