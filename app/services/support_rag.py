"""지원제도 활성 근거 -> 구절 ID 생성 -> 검증 -> 원본 출처 연결."""

from copy import deepcopy
from datetime import date
import os

from psycopg.rows import dict_row
from pydantic import ValidationError

from app.models.rag import (
    DraftItem, RagConfigurationError, RagDraft, RagGeneration,
    RagResponseValidationError, RagSearchError, UnansweredPart,
    answer_status, schema_validation_issues,
)
from app.models.support_rag import SupportInfo, SupportRagResult
from app.retrieval.support_evidence import search_support_evidence
from app.services.database import get_connection
from app.services.answer_quality import guard_unsupported_absolutes
from app.retrieval.hybrid_search import has_source_url
from app.services.program_rag import (
    ANSWER_HEADERS, SHORTAGE_REASON, _bind_citations, _validate_evidence,
    ensure_source_policy, generation_kwargs, release_fields,
)
from app.services.rag_llm import (
    SYSTEM_PROMPT as PROGRAM_SYSTEM_PROMPT, _request_rag_draft,
    build_citation_spans, get_rag_settings, load_llm_environment, request_context,
    system_prompt_for, validate_mode,
)


EVIDENCE_PAGE_SIZE = 100


def guard_current_availability(draft, info, question, today=None, *, evidence):
    """A stored unknown/old status is not evidence of current application access."""
    current = any(word in question for word in ('현재', '지금', '오늘', '신청할 수 있', '접수 중', '모집 중'))
    day = today or date.today()
    unverified = info is None or info.availability in (None, 'UNKNOWN') or info.source_verified_at != day
    if not current or not unverified:
        return draft
    spans = build_citation_spans(evidence)
    items = []
    for item in draft.items:
        temporal = any(word in item.question_part for word in ('모집', '접수', '신청 가능', '신청가능', '신청 여부', '신청여부', '마감', '신청할 수'))
        if temporal and all(c in spans for c in item.citation_ids):
            item = item.model_copy(update={'answer': None, 'citation_ids': []})
        items.append(item)
    return RagDraft(items=items)


def guard_duplicate_benefit_claims(draft, evidence):
    """A separate review clause alone does not establish a blanket prohibition."""
    spans = build_citation_spans(evidence)
    items = []
    prohibitions = ('불가능', '불가', '금지', '중복 수혜할 수 없', '중복 지원할 수 없', '중복 지원이 안')
    for item in draft.items:
        text = item.answer or ''
        quotes = ' '.join(spans[c].quote for c in item.citation_ids if c in spans)
        if (item.citation_ids and all(c in spans for c in item.citation_ids) and '중복' in text and '별도 심사' in quotes and any(term in text for term in prohibitions)
                and not any(term in quotes for term in prohibitions)):
            item = item.model_copy(update={'answer': None, 'citation_ids': []})
        items.append(item)
    return RagDraft(items=items)
SYSTEM_PROMPT = PROGRAM_SYSTEM_PROMPT.replace(
    "선택된 한 프로그램", "선택된 한 지원제도", 1,
) + """
선택된 지원제도에 관한 질문만 답하라. 다른 제도의 조건을 적용하지 마라.
근거 부족 안내 자체를 answer에 쓰지 말고 answer=null, citation_ids=[]로 두어라.
접수·모집 여부는 저장된 근거의 회차·적용 범위에 한정해 설명하라.
UNKNOWN은 모집 중이라는 뜻이 아니며, 현재 모집 여부를 묻는 항목에는 직접
확인할 근거가 없으므로 answer=null, citation_ids=[]로 두어라.
OPEN/CLOSED/UPCOMING도 확인일 이후의 실시간 상태로 단정하지 마라.
저장된 모집 상태·확인일 안내는 코드가 별도로 붙인다. 날짜를 추측하지 마라.
근거가 '중복 지원·단계별 지급 요건은 별도 심사한다'이면 별도 심사라고만 설명한다.
그 문구만으로 '중복 지원 불가'를 추가하지 마라. 연도·취업 개시자 등 적용 범위도 생략하지 마라.
"""


def _load_support_info(support_program_id: str) -> SupportInfo | None:
    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                SELECT s.support_program_id, s.name, p.availability,
                       p.source_verified_at, p.profile,
                       p.release_id AS profile_release_id
                FROM public.support_programs AS s
                LEFT JOIN public.support_program_profiles AS p
                  ON p.support_program_id = s.support_program_id
                WHERE s.support_program_id = %s
            """, (support_program_id,))
            row = cursor.fetchone()
    if row is None:
        return None
    try:
        return SupportInfo.model_validate(row)
    except ValidationError as exc:
        raise RagSearchError("지원제도 기본 정보 형식이 잘못되었습니다.") from exc


def _validate_support_evidence(support_program_id, rows):
    if not isinstance(rows, list):
        raise RagSearchError("지원제도 근거가 목록 형식이 아닙니다.")
    adapted = []
    for row in rows:
        if (not isinstance(row, dict) or "program_id" in row
                or row.get("support_program_id") != support_program_id):
            raise RagSearchError("근거가 요청한 지원제도의 범위를 벗어났습니다.")
        # Reuse the single-program field/scope checks without changing public IDs.
        adapted.append({**row, "program_id": support_program_id})
    _validate_evidence(support_program_id, adapted)


def _load_all_evidence(support_program_id):
    rows = []
    offset = 0
    while True:
        page = search_support_evidence(support_program_id, limit=EVIDENCE_PAGE_SIZE, offset=offset)
        _validate_support_evidence(support_program_id, page)
        if len(page) > EVIDENCE_PAGE_SIZE:
            raise RagSearchError("조회한 근거가 요청한 페이지 크기를 초과했습니다.")
        rows.extend(page)
        if len(page) < EVIDENCE_PAGE_SIZE:
            break
        offset += EVIDENCE_PAGE_SIZE
    # Reject cross-page duplicates instead of silently dropping provenance.
    _validate_support_evidence(support_program_id, rows)
    return rows


def _availability_notice(info: SupportInfo | None) -> str:
    if info is None:
        return "저장된 지원제도 정보가 없어 모집 여부를 확인할 수 없습니다."
    labels = {"OPEN": "접수 중으로 저장됨", "CLOSED": "마감으로 저장됨",
              "UPCOMING": "접수 예정으로 저장됨", "UNKNOWN": "모집 여부 확인 불가"}
    state = info.availability
    label = labels.get(state, "상태 미기록")
    verified = info.source_verified_at.isoformat() if info.source_verified_at else "미기록"
    notice = f"저장된 모집 상태: {label}, 확인일: {verified}."
    scope = (info.profile or {}).get("availability_scope")
    if isinstance(scope, str) and scope.strip():
        notice += f" 적용 범위: {scope}."
    return notice + " 확인일 이후의 현재 모집 여부는 재확인이 필요합니다."


def _messages_payload(support_program_id, question, evidence, profile=None,
                      mode="development", today=None):
    spans = build_citation_spans(evidence)
    return {
        "support_program_id": support_program_id,
        "question": question,
        "retrieved_passages": [{
            **{key: row[key] for key in ("chunk_id", "title", "body")},
            "citation_spans": [{"id": span_id, "text": span.quote}
                               for span_id, span in spans.items() if span.chunk_id == row["chunk_id"]],
        } for row in evidence],
        **request_context(profile, mode, "default", today),
    }


def generate_support_draft(support_program_id, question, evidence, profile=None,
                           *, mode="development", today=None):
    validate_mode(mode)
    load_llm_environment()
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RagConfigurationError("OPENAI_API_KEY가 설정되어 있지 않습니다.")
    model, effort = get_rag_settings()
    return _request_rag_draft(
        _messages_payload(support_program_id, question, evidence, profile, mode, today),
        system_prompt=system_prompt_for(SYSTEM_PROMPT, mode), draft_type=RagDraft,
        model=model, effort=effort,
    )


def answer_support_question(
    support_program_id: str, question: str, profile: dict | None = None,
    *, mode: str = "development", today=None,
) -> dict:
    """선택한 제도의 활성 근거 전체를 읽고 최대 한 번 생성한다.

    구절·출처 검증은 인용의 의미적 타당성을 보장하지 않는다.
    상태는 반환된 질문 항목 기준이며, 근거 부족과 실행 오류를 구분한다.
    목록/프로필과 근거 페이지는 기존 함수의 별도 읽기 전용 트랜잭션을 쓴다.
    mode="production"은 순위 없이 전체를 읽은 뒤 출처 URL 없는 근거를 제외한다.
    """
    validate_mode(mode)
    if not isinstance(support_program_id, str) or not support_program_id.strip():
        raise ValueError("support_program_id는 비어 있지 않은 문자열이어야 합니다.")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question은 공백이 아닌 문자를 포함한 문자열이어야 합니다.")
    support_program_id = support_program_id.strip()
    try:
        info = _load_support_info(support_program_id)
        rows = _load_all_evidence(support_program_id)
        if mode == "production":
            rows = [row for row in rows if has_source_url(row["source_urls"])]
        if rows and info is None:
            raise RagSearchError("근거의 대상인 지원제도 기본 정보가 없습니다.")
    except RagSearchError:
        raise
    except Exception as exc:
        raise RagSearchError("지원제도 정보 또는 활성 근거 조회에 실패했습니다.") from exc
    ensure_source_policy(rows, mode)
    evidence = deepcopy(rows)
    requested_model = model = None
    if not evidence:
        draft = RagDraft(items=[DraftItem(question_part=question, answer=None, citation_ids=[])])
    else:
        generation = generate_support_draft(
            support_program_id, question, deepcopy(evidence),
            **generation_kwargs(profile, mode, "default", today),
        )
        if not isinstance(generation, RagGeneration):
            raise RagResponseValidationError("LLM 생성 결과 형식이 잘못되었습니다.", code="invalid_generation_type")
        try:
            draft = RagDraft.model_validate(generation.draft.model_dump())
        except ValidationError as exc:
            raise RagResponseValidationError("답변 항목 구조가 올바르지 않습니다.", issues=schema_validation_issues(exc)) from exc
        except AttributeError as exc:
            raise RagResponseValidationError("LLM 답변 항목 형식이 잘못되었습니다.", code="invalid_draft_type") from exc
        requested_model, model = generation.requested_model, generation.model
    try:
        draft = guard_current_availability(draft, info, question, today, evidence=evidence)
        draft = guard_duplicate_benefit_claims(draft, evidence)
        draft = guard_unsupported_absolutes(draft, evidence)
        claims = _bind_citations(draft, evidence)
        unanswered = [UnansweredPart(part_index=i, question_part=item.question_part, reason=SHORTAGE_REASON)
                      for i, item in enumerate(draft.items) if item.answer is None]
        notice = _availability_notice(info)
        lines = [ANSWER_HEADERS[mode]]
        lines.extend(f"{claim.text} [{i}]" for i, claim in enumerate(claims, 1))
        if unanswered:
            lines.append(SHORTAGE_REASON)
            lines.extend(f"- {part.question_part}" for part in unanswered)
        lines.append(notice)
        result = SupportRagResult(
            support_program_id=support_program_id, question=question,
            status=answer_status(len(claims), len(unanswered)), answer="\n".join(lines),
            question_parts=[item.question_part for item in draft.items], claims=claims,
            unanswered_parts=unanswered, evidence=evidence, support_info=info,
            availability_notice=notice, requested_model=requested_model, model=model,
            **release_fields(mode, "default", draft),
        )
    except ValidationError as exc:
        raise RagResponseValidationError("최종 답변 구조 검증에 실패했습니다.", issues=schema_validation_issues(exc)) from exc
    return result.model_dump(mode="json")
