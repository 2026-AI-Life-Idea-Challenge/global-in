"""
app/agent/official_information.py

공식 정보 안내 에이전트.

역할:
- pgvector RAG 를 통해 공식 문서를 검색하고 근거를 검증합니다.
- AI 해석과 공식 규정을 명확히 구분하여 사용자에게 전달합니다.
- 출처(official_agency, source_url)를 반드시 명시합니다.
- 정보가 없는 경우 추측하지 않고 공식 채널 확인을 권합니다.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.agent.state import AgentState, RetrievedDocument, ValidatedEvidence
from app.retrieval.retriever import retrieve
from app.retrieval.query import build_official_info_query, build_support_program_query
from app.services import llm

logger = logging.getLogger(__name__)

_SYSTEM = """
당신은 Global-In 의 공식 정보 안내 에이전트입니다.

핵심 원칙:
1. 공식 문서에서 검색된 내용만 근거로 사용합니다.
2. AI 의 해석과 공식 규정을 명확히 구분하세요.
3. 출처(기관명, 문서명, URL)를 반드시 인용하세요.
4. 검색된 문서가 없거나 불명확하면 "공식 확인 필요"라고 명시하세요.
5. 추측·일반적 지식으로 공식 정보를 대체하지 마세요.
6. 비자 자격 정보와 지원제도 정보를 분리하여 설명하세요.

응답 형식: 반드시 JSON 만 출력합니다.
{
  "answer": "사용자 질문에 대한 한국어 답변 (출처 인용 포함)",
  "official_sources": [
    {
      "official_agency": "발급 기관",
      "source_title": "문서 제목",
      "source_url": "URL (있는 경우)",
      "key_excerpt": "핵심 발췌문 (원문 그대로)"
    }
  ],
  "disclaimer": "AI 해석 면책 문구 (필요 시)",
  "needs_official_verification": true/false,
  "verification_guidance": "공식 채널 안내 (needs_official_verification=true 인 경우)"
}
""".strip()


def _docs_to_context(docs: list[dict]) -> str:
    """검색된 문서를 LLM 프롬프트 컨텍스트로 변환합니다."""
    if not docs:
        return "검색된 공식 문서가 없습니다."
    lines = []
    for i, doc in enumerate(docs, 1):
        agency = doc.get("official_agency") or "미상"
        title = doc.get("source_title") or "제목 없음"
        url = doc.get("source_url") or ""
        content = doc.get("content", "")
        is_valid = doc.get("is_valid", False)
        lines.append(
            f"[문서 {i}] 기관: {agency} | 제목: {title}"
            + (f" | URL: {url}" if url else "")
            + (f" | 검증: {'공식 확인됨' if is_valid else '미검증'}")
            + f"\n{content}\n"
        )
    return "\n".join(lines)


def _to_retrieved_document(doc: dict) -> RetrievedDocument:
    return RetrievedDocument(
        chunk_id=doc.get("chunk_id", ""),
        document_id=doc.get("document_id", ""),
        content=doc.get("content", ""),
        destination_country=doc.get("destination_country"),
        program_id=doc.get("program_id"),
    )


def _to_validated_evidence(doc: dict) -> ValidatedEvidence | None:
    if not doc.get("is_valid"):
        return None
    return ValidatedEvidence(
        chunk_id=doc.get("chunk_id", ""),
        content=doc.get("content", ""),
        official_agency=doc.get("official_agency"),
        source_title=doc.get("source_title"),
        source_url=doc.get("source_url"),
        is_valid=True,
        validity_reason=doc.get("validity_reason", ""),
    )


def run(state: AgentState) -> dict[str, Any]:
    """공식 정보 안내 에이전트 노드."""
    logger.info("[official_information] 실행")

    user_query = state["user_query"]
    profile = state.get("user_profile") or {}
    as_of = profile.get("application_date") or None

    # 1. 비자/프로그램 관련 공식 정보 검색
    query_text, filters = build_official_info_query(user_query, state)
    visa_docs = retrieve(
        query_text=query_text,
        filters=filters,
        top_k=5,
        similarity_threshold=0.45,
        as_of=as_of,
    )

    # 2. 지원제도 관련 공식 정보 검색 (intent 에 따라 추가)
    support_docs: list[dict] = []
    intent = state.get("intent", "")
    if intent in ("route_recommendation", "eligibility_review", "preparation_planning"):
        support_query, support_filters = build_support_program_query(user_query, state)
        support_docs = retrieve(
            query_text=support_query,
            filters=support_filters,
            top_k=3,
            similarity_threshold=0.45,
            as_of=as_of,
        )

    all_docs = visa_docs + support_docs

    # 3. RetrievedDocument 변환
    retrieved: list[RetrievedDocument] = [_to_retrieved_document(d) for d in all_docs]

    # 4. ValidatedEvidence 추출
    validated: list[ValidatedEvidence] = [
        ev for d in all_docs
        if (ev := _to_validated_evidence(d)) is not None
    ]

    # 5. LLM 으로 공식 정보 답변 생성
    context = _docs_to_context(all_docs)
    eligibility_summary = ""
    for er in (state.get("eligibility_results") or []):
        tid = er.get("target_id", "")
        status = er.get("status", "")
        eligibility_summary += f"- {tid}: {status}\n"

    prompt = f"""## 사용자 질문
{user_query}

## 자격 검토 요약 (이전 단계)
{eligibility_summary or '자격 검토 없음'}

## 검색된 공식 문서
{context}

사용자 질문에 대해 위 공식 문서를 근거로 답변하는 JSON 을 출력하세요.
공식 문서가 없는 경우 needs_official_verification=true 로 설정하세요.
"""
    try:
        raw = llm.extract_json(prompt, system=_SYSTEM, max_tokens=1536)
        llm_result = json.loads(raw)
    except Exception as e:
        logger.warning(f"[official_information] LLM 답변 생성 실패: {e}")
        llm_result = {
            "answer": "공식 정보를 불러오는 중 오류가 발생했습니다. 해당 국가의 공식 대사관 또는 이민국에 직접 확인하시기 바랍니다.",
            "official_sources": [],
            "disclaimer": "AI 답변 생성 중 오류 발생",
            "needs_official_verification": True,
            "verification_guidance": "공식 채널 직접 확인 권장",
        }

    # 6. final_answer 구성
    answer = llm_result.get("answer", "")
    if llm_result.get("needs_official_verification"):
        guidance = llm_result.get("verification_guidance", "")
        if guidance:
            answer += f"\n\n⚠️ {guidance}"

    return {
        "retrieved_documents": retrieved,
        "validated_evidence": validated,
        "final_answer": answer,
        "next_node": "preparation_planning",
        "current_agent": "official_information",
    }
