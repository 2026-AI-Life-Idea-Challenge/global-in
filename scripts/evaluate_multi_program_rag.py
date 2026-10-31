"""Three development cases; one live request per case, no retry or judge LLM.

From the project root (local query model is always offline):
    env -u OPENAI_API_KEY RAG_MODEL=gpt-6-luna RAG_REASONING_EFFORT=low \
      /opt/miniconda3/envs/global-in/bin/python -B \
      -m scripts.evaluate_multi_program_rag --live

No flag: print the plan only. --retrieval-only: no external LLM call.
Logs contain answers and short exact quotes, never credentials or raw SDK errors.
"""

import argparse
import json
import os
import time
from unittest.mock import patch

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

from openai.resources.responses import Responses

from app.models.multi_program_rag import ProgramsRagResult
from app.models.rag import (
    RagConfigurationError, RagLLMError, RagResponseValidationError, RagSearchError,
)
from app.services import multi_program_rag as rag

CASES = (
    {"id": "funds", "question": "호주 워홀 프로그램들의 초기 자금 조건을 알려줘"},
    {"id": "funds_and_insurance", "question": "호주 워홀 프로그램들의 초기 자금 조건과 건강보험 가입 의무를 각각 알려줘"},
    {"id": "insurance", "question": "호주 워홀 프로그램들의 건강보험 가입이 의무인지 알려줘"},
)
COUNTRY, CATEGORY = "australia", "working_holiday"


def emit(event, **fields):
    print(json.dumps({"event": event, **fields}, ensure_ascii=False), flush=True)


def check_result(result):
    """Identity/provenance checks only; semantic entailment requires review."""
    ProgramsRagResult.model_validate(result)
    programs = {p["program_id"]: p for p in result["candidate_programs"]}
    rows = {row["chunk_id"]: row for row in result["evidence"]}
    checks = []
    for claim in result["claims"]:
        for citation in claim["citations"]:
            row = rows[citation["chunk_id"]]
            checks.append(
                claim["program_id"] == citation["program_id"]
                and claim["program_id"] in row["program_ids"]
                and citation["program_name"] == claim["program_name"]
                == programs[claim["program_id"]]["name"]
                and citation["quote"] in row["body"]
                and citation["source_missing"] == (not row["source_urls"])
                and all(citation[key] == row[key] for key in (
                    "document_id", "revision_id", "title", "source_urls",
                    "source_references", "answer_approved", "content_review_status",
                ))
            )
    return {
        "structure_valid": True,
        "citation_program_quote_source_and_approval_match": all(checks),
        "citation_count": len(checks),
        "development_flags_preserved": (
            result["development_only"] is True
            and result["eligibility_assessed"] is False
            and result["public_release_status"] == "not_assessed"
        ),
    }


def request_observer(parse, metrics):
    def observed(resource, **kwargs):
        if metrics["requests"]:
            raise RuntimeError("사례당 LLM 호출은 한 번만 허용합니다.")
        if (kwargs["model"] != rag.RAG_MODEL
                or kwargs.get("reasoning") != {"effort": rag.RAG_REASONING_EFFORT}):
            raise RuntimeError("실제 모델·reasoning 설정이 평가 조건과 다릅니다.")
        metrics["requests"] += 1
        started = time.perf_counter()
        try:
            response = parse(resource, **kwargs)
        finally:
            metrics["llm_seconds"] = round(time.perf_counter() - started, 3)
        metrics["actual_model"] = response.model
        metrics["reasoning_effort"] = getattr(getattr(response, "reasoning", None), "effort", None)
        usage = getattr(response, "usage", None)
        metrics["usage"] = {key: getattr(usage, key, None) for key in (
            "input_tokens", "output_tokens", "total_tokens",
        )}
        return response
    return observed


def evaluate_live_cases(cases=CASES):
    completed = failed = total_requests = 0
    stop = False
    for case in cases:
        if stop:
            emit("case_skipped", id=case["id"], reason="request_configuration_or_access_error")
            continue
        metrics = {"requests": 0}
        started = time.perf_counter()
        try:
            with patch.object(Responses, "parse", request_observer(Responses.parse, metrics)):
                result = rag.answer_programs_question(case["question"], COUNTRY, CATEGORY)
            checks = check_result(result)
        except (RagSearchError, RagLLMError, RagResponseValidationError) as exc:
            failed += 1
            cause = exc.__cause__
            status = getattr(cause, "status_code", None)
            status = status if type(status) is int else None
            emit("execution_error", id=case["id"], error_type=type(exc).__name__,
                 http_status=status, metrics=metrics,
                 validation_issues=exc.issues if isinstance(exc, RagResponseValidationError) else [])
            stop = isinstance(exc, RagConfigurationError) or status in {400, 401, 403, 404, 429}
        else:
            completed += 1
            # Limit printed quote lengths only; the function's citations retain
            # the full exact source spans and all original approval metadata.
            claims = [{**claim, "citations": [{
                key: citation[key] for key in (
                    "program_id", "program_name", "chunk_id", "source_urls", "answer_approved",
                )
            } | {"quote_excerpt": citation["quote"][:360]}
                for citation in claim["citations"]]} for claim in result["claims"]]
            emit("case", id=case["id"], question=case["question"],
                 elapsed_seconds=round(time.perf_counter() - started, 3), metrics=metrics,
                 requested_model=result["requested_model"], model=result["model"],
                 status=result["status"], answer=result["answer"], claims=claims,
                 question_parts=result["question_parts"], unanswered_parts=result["unanswered_parts"],
                 candidate_programs=result["candidate_programs"],
                 retrieved_programs=result["retrieved_programs"], answered_programs=result["answered_programs"],
                 programs_without_retrieved_evidence=result["programs_without_retrieved_evidence"],
                 checks=checks,
                 semantic_review="각 주장의 프로그램·의미·조건·수치와 전체 원문 인용을 별도 검토해야 함")
        total_requests += metrics["requests"]
    emit("summary", planned=len(cases), completed=completed, errors=failed,
         llm_requests=total_requests, max_requests=len(cases),
         semantic_quality_automatically_certified=False)
    return 0 if completed == len(cases) and not failed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--retrieval-only", action="store_true")
    args = parser.parse_args()
    if not args.live and not args.retrieval_only:
        emit("plan", cases=CASES, country=COUNTRY, category=CATEGORY,
             model=rag.RAG_MODEL, reasoning_effort=rag.RAG_REASONING_EFFORT,
             maximum_requests=len(CASES))
        return 0
    if args.retrieval_only:
        for case in CASES:
            rows = rag.search_programs_evidence_hybrid(
                case["question"], country=COUNTRY, category=CATEGORY, limit=rag.RETRIEVAL_LIMIT,
            )
            emit("retrieval", id=case["id"], external_llm_called=False, evidence=[{
                key: row[key] for key in (
                    "chunk_id", "program_ids", "programs", "title", "source_urls",
                    "answer_approved", "vector_rank", "keyword_rank", "rrf_score",
                )
            } | {"body_excerpt": row["body"][:360]} for row in rows])
        return 0
    rag.load_llm_environment()
    configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    emit("environment", api_key_configured=configured,
         requested_model=rag.RAG_MODEL, reasoning_effort=rag.RAG_REASONING_EFFORT)
    if not configured:
        emit("summary", completed=0, llm_requests=0, reason="OPENAI_API_KEY_not_configured")
        return 1
    return evaluate_live_cases()


if __name__ == "__main__":
    raise SystemExit(main())
