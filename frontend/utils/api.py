"""
frontend/utils/api.py
FastAPI 백엔드 통신 유틸리티
"""
import os
import re
import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
_API_KEY = os.getenv("INTERNAL_API_KEY", "")

# ── 국가/카테고리 매핑 ──────────────────────────────────────────────────────
_COUNTRY_MAP = {
    "japan":         ("일본",     "🇯🇵"),
    "australia":     ("호주",     "🇦🇺"),
    "usa":           ("미국",     "🇺🇸"),
    "germany":       ("독일",     "🇩🇪"),
    "canada":        ("캐나다",   "🇨🇦"),
    "uk":            ("영국",     "🇬🇧"),
    "france":        ("프랑스",   "🇫🇷"),
    "multi_country": ("여러 국가","🌐"),
}

_CATEGORY_MAP = {
    "employment":      "취업",
    "study":           "유학·교환학생",
    "working_holiday": "워킹홀리데이",
}

_NATIONALITY_ISO = {
    "KR": "한국", "JP": "일본", "US": "미국",
    "DE": "독일", "AU": "호주", "CA": "캐나다", "GB": "영국",
}

_COUNTRY_NAME_KO = {
    "japan": "일본", "australia": "호주", "usa": "미국",
    "germany": "독일", "canada": "캐나다", "uk": "영국",
}

_VISA_PURPOSE = {
    "study": "유학·교환학생",
    "student": "유학·교환학생",
    "employment": "취업",
    "working_holiday": "워킹홀리데이",
}


def _add_paragraph_breaks(text: str) -> str:
    """한국어 응답 텍스트에 문단 줄바꿈을 추가합니다."""
    if not text:
        return text
    if "\n" in text:
        return text
    text = re.sub(r"([다요죠네까습])([.!?]) +(?=[가-힣①②③\-⚠️✅])", r"\1\2\n\n", text)
    return text.strip()


def _to_program_cards(
    candidate_programs: list | None,
    candidate_support_programs: list | None,
) -> list[dict]:
    """백엔드 candidate_programs → program_card 포맷으로 변환."""
    cards = []
    for p in (candidate_programs or []):
        ckey = (p.get("country") or "").lower()
        country_name, emoji = _COUNTRY_MAP.get(ckey, (ckey or "기타", "🌐"))
        category = (p.get("category") or "").lower()
        purpose = _CATEGORY_MAP.get(category, category)
        cards.append({
            "id":                p.get("program_id") or p.get("id") or "",
            "type":              "프로그램",
            "country":           country_name,
            "country_emoji":     emoji,
            "purpose":           purpose,
            "name":              p.get("name") or "",
            "description":       p.get("recommendation_reason") or p.get("description") or "",
            "condition_summary": "",
            "url":               p.get("url") or "",
        })
    for sp in (candidate_support_programs or []):
        ckey = (sp.get("country") or "").lower()
        country_name, emoji = _COUNTRY_MAP.get(ckey, (ckey or "여러 국가", "🌐"))
        cards.append({
            "id":                sp.get("support_program_id") or sp.get("id") or "",
            "type":              "지원제도",
            "country":           country_name,
            "country_emoji":     emoji,
            "purpose":           "취업",
            "name":              sp.get("name") or "",
            "description":       sp.get("note") or sp.get("description") or "",
            "condition_summary": sp.get("applicability_status") or "",
            "url":               sp.get("url") or "",
        })
    return cards


def _map_profile(backend_profile: dict) -> dict:
    """백엔드 UserProfile → 프론트 session_state.profile 필드 매핑."""
    from datetime import date as _date
    updates = {}

    # 국적: ["KR"] → ["한국"]
    if "nationalities" in backend_profile:
        nats = backend_profile["nationalities"]
        if isinstance(nats, list):
            updates["nationalities"] = [_NATIONALITY_ISO.get(n, n) for n in nats]
        elif isinstance(nats, str):
            updates["nationalities"] = [_NATIONALITY_ISO.get(nats, nats)]

    # 생년월일 → 나이
    if "date_of_birth" in backend_profile:
        try:
            dob = _date.fromisoformat(backend_profile["date_of_birth"])
            today = _date.today()
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
            updates["age"] = age
        except Exception:
            pass

    # 목표 국가
    if "target_country" in backend_profile:
        tc = (backend_profile["target_country"] or "").lower()
        ko = _COUNTRY_NAME_KO.get(tc, tc)
        if ko:
            updates["target_countries"] = [ko]
            updates["undecided_country"] = False

    # 비자 유형 → 목적
    if "target_visa_type" in backend_profile:
        vt = (backend_profile["target_visa_type"] or "").lower()
        purpose = _VISA_PURPOSE.get(vt)
        if purpose:
            updates["purposes"] = [purpose]
            updates["undecided_purpose"] = False

    # 프론트 필드와 동일한 것은 그대로
    direct_fields = [
        "age", "major", "languages", "language_certs",
        "education_level", "career_duration", "job_field",
        "residence_country", "education_status",
    ]
    for k in direct_fields:
        if backend_profile.get(k) is not None:
            updates[k] = backend_profile[k]

    # extra 딕셔너리 내부도 병합 (단, age는 직접 넣지 않음)
    if isinstance(backend_profile.get("extra"), dict):
        extra = {k: v for k, v in backend_profile["extra"].items() if k != "age"}
        updates.update(extra)

    # DOB 기반 만 나이가 있으면 항상 최종 override (stale age 방지)
    if "age" in updates and "date_of_birth" in backend_profile:
        pass  # already computed from DOB above; extra age already stripped

    return updates


def chat_send(
    user_query: str,
    session_id: str | None = None,
    history: list[dict] | None = None,
    profile: dict | None = None,
) -> dict:
    """
    AI 에이전트에 메시지를 전송하고 응답 딕셔너리를 반환.
    반환값: {"text": str, "programs": list[dict], "profile": dict}
    """
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            json={
                "session_id": session_id,
                "user_query": user_query,
                "history": history or [],
                "user_profile": profile or {},
            },
            headers={"X-API-Key": _API_KEY},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        raw_text = data.get("final_answer") or data.get("follow_up_question") or ""
        text = _add_paragraph_breaks(raw_text)

        programs = _to_program_cards(
            data.get("candidate_programs"),
            data.get("candidate_support_programs"),
        )

        backend_profile = data.get("user_profile") or {}
        mapped_profile = _map_profile(backend_profile)

        return {"text": text, "programs": programs, "profile": mapped_profile}

    except Exception:
        return {
            "text": (
                "안녕하세요! 현재 AI 상담 서버와 연결 중이에요. "
                "연결이 완료되면 맞춤 답변을 드릴게요. 😊"
            ),
            "programs": [],
            "profile": {},
        }


# 하위 호환용 alias
chat_stream = chat_send


def search_programs(filters: dict) -> list[dict]:
    """프로그램·지원제도 검색. 백엔드 미연결 시 샘플 데이터 반환."""
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
        {"id": "jp_employment_skilled", "type": "프로그램", "country": "일본",
         "country_emoji": "🇯🇵", "purpose": "취업", "name": "기술·인문지식·국제업무",
         "description": "전문 지식과 기술을 활용해 일본에서 일하는 취업 경로.",
         "condition_summary": "담당 직무와 학력·경력 등 요건 확인", "url": ""},
        {"id": "kmove_support", "type": "지원제도", "country": "여러 국가",
         "country_emoji": "🌐", "purpose": "취업", "name": "K-Move스쿨",
         "description": "해외취업에 필요한 어학·직무 연수와 취업 연계를 지원.",
         "condition_summary": "지원 내용: 맞춤형 교육·연수비·일부 취업 지원", "url": ""},
        {"id": "de_chancenkarte", "type": "프로그램", "country": "독일",
         "country_emoji": "🇩🇪", "purpose": "취업", "name": "기회카드 (Chancenkarte)",
         "description": "독일에서 일자리를 찾기 위한 체류 경로.",
         "condition_summary": "자격 인정 또는 점수 경로·언어·생계 요건 확인", "url": ""},
        {"id": "au_wh_417", "type": "프로그램", "country": "호주",
         "country_emoji": "🇦🇺", "purpose": "워킹홀리데이", "name": "워킹홀리데이 비자 (417)",
         "description": "호주에서 여행하며 단기 근로를 병행하는 경로.",
         "condition_summary": "나이·국가·연령 이전 참여 이력 등 요건 확인", "url": ""},
        {"id": "us_f1_student", "type": "프로그램", "country": "미국",
         "country_emoji": "🇺🇸", "purpose": "유학·교환학생", "name": "학생 비자 (F-1)",
         "description": "미국의 대학 등 교육기관에서 학업을 위한 경로.",
         "condition_summary": "교육기관 학업 과정·I-20 등 확인", "url": ""},
        {"id": "ca_fsw", "type": "프로그램", "country": "캐나다",
         "country_emoji": "🇨🇦", "purpose": "취업", "name": "연방 전문인력 프로그램 (FSW)",
         "description": "해외 숙련 경력을 바탕으로 검토하는 캐나다 영주권 경로.",
         "condition_summary": "숙련 경력·공인어·학력 등 조건 확인", "url": ""},
        {"id": "koreit_support", "type": "지원제도", "country": "여러 국가",
         "country_emoji": "🌐", "purpose": "취업", "name": "해외취업정착지원금",
         "description": "해외취업 후 초기 정착과 경력 개발을 돕는 지원.",
         "condition_summary": "지원 내용: 해외취업자의 초기 정착을 위한 지원금", "url": ""},
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
        purpose_map = {"취업": "취업", "유학·교환학생": "유학", "워킹홀리데이": "워킹홀리데이"}
        key = purpose_map.get(purpose, purpose)
        result = [p for p in result if key in p["purpose"]]
    if keyword:
        result = [p for p in result if keyword in p["name"] or keyword in p["description"]]

    return result
