"""Purpose matching for discovery; independent of personal eligibility and DB writes."""

from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field

from app.models.rag import RagResponseValidationError


class SupportRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    support_program_id: str
    reason: str = Field(min_length=1)
    fact_ids: list[str] = Field(min_length=1)


def support_facts(support):
    """Use actual profile fields, never infer purpose from an ID/name or broad topics."""
    profile = support.get("profile") or {}
    facts = {}
    for field in ("eligibility_summary", "benefits_summary", "applicability_conditions"):
        value = profile.get(field)
        values = value if isinstance(value, list) else [value]
        for index, text in enumerate(values):
            if isinstance(text, str) and text.strip():
                facts[f"{field}:{index}"] = text
    return facts


def support_catalog_entry(support):
    return {
        "support_program_id": support["support_program_id"],
        "name": support["name"],
        "destination_countries": support.get("destination_countries"),
        "facts": support_facts(support),
        "program_links": deepcopy(support.get("program_links") or []),
        "availability": support.get("availability"),
        "source_verified_at": support.get("source_verified_at"),
    }


def bind_support_recommendations(recommendations, supports):
    """Bind reason references to original metadata; semantic match remains model judgment."""
    by_id = {s["support_program_id"]: s for s in supports}
    selected, reasons, seen = [], {}, set()
    for item in recommendations:
        sid = item.support_program_id
        if sid not in by_id or sid in seen:
            raise RagResponseValidationError("추천 대상이 검색 범위를 벗어나거나 중복됩니다.",
                                             code="invalid_recommendation_target")
        facts = support_facts(by_id[sid])
        if not item.reason.strip() or not item.fact_ids or any(key not in facts for key in item.fact_ids):
            raise RagResponseValidationError("추천 이유의 원본 자료를 확인할 수 없습니다.",
                                             code="invalid_recommendation_fact")
        seen.add(sid)
        selected.append(deepcopy(by_id[sid]))
        reasons[sid] = {"reason": item.reason, "facts": {key: facts[key] for key in item.fact_ids}}
    return selected, reasons


PURPOSE_ANSWER_RULES = """
[사용자 목적과 추천]
known_user_profile의 purpose와 target_visa_type 및 현재 질문을 함께 읽어라.
최신 질문에서 바뀐 목적이 우선이다. 탐색·추천 요청에서는 근거의 실제 대상·지원 내용·
적용 조건이 그 목적과 연결되는 후보만 안내하고, 무엇을 지원하며 왜 관련 있는지 짧게 설명하라.
같은 국가, 높은 검색 순위, 비슷한 제목만으로 적합하다고 판단하지 마라.
취업 준비 목적에 대학원 진학을 전제로 한 장학금을 임의로 추천하지 마라.
현재 단계와 다른 지원을 설명해야 한다면 '취업 후' 같은 전제 조건을 같은 문장에 남겨라.
목적과의 관련성은 신청 자격·지급 확정과 다르다. 자격 미확인 후보는 확인해볼 후보로 표현하라.
목적 적합성을 판단할 근거가 없으면 임의 추천하지 마라. 근거 부족이 제도 부재를 뜻하지 않는다.
특정 제도의 설명·비교를 직접 요청했다면 추천 적합성으로 차단하지 말고 그 제도의 근거로 답하라.
정책은 연결된 프로그램/지원제도의 근거로 다루며 별도 지원 혜택으로 만들어 추천하지 마라.
"""
