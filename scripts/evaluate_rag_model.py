"""One-pass RAG model evaluation with frozen evidence, not a semantic judge.

Prepare once (read-only retrieval, no external LLM call):
    python -B -m scripts.evaluate_rag_model --prepare --snapshot /tmp/rag-inputs.json
Evaluate once (no retrieval/DB calls):
    env -u OPENAI_API_KEY RAG_MODEL=gpt-6-luna RAG_REASONING_EFFORT=low \
        python -B -m scripts.evaluate_rag_model --live --snapshot /tmp/rag-inputs.json

The snapshot contains source bodies and metadata for local reproducibility.
Only the existing RAG payload is sent to the LLM. Neither mode overwrites files.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time
from unittest.mock import patch

from openai.resources.responses import Responses

from app.models.rag import (
    RagConfigurationError, RagDraft, RagLLMError, RagResponseValidationError, RagSearchError,
)
from app.services import program_rag as rag
from app.services import rag_llm as llm
from scripts import evaluate_program_rag as evaluation

CASES = evaluation.CASES + evaluation.VARIANT_CASES
KNOWN_ERROR_CODES = {
    "invalid_api_key", "model_not_found", "permission_denied", "insufficient_quota",
    "rate_limit_exceeded", "invalid_request_error", "unsupported_parameter",
    "unsupported_value", "context_length_exceeded", "organization_restricted",
}


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def messages_for(case, rows):
    spans = llm.build_citation_spans(rows)
    payload = {
        "program_id": evaluation.PROGRAM_ID,
        "question": case["question"],
        "retrieved_passages": [
            {**{key: row[key] for key in ("chunk_id", "title", "body")},
             "citation_spans": [
                 {"id": key, "text": span.quote}
                 for key, span in spans.items() if span.chunk_id == row["chunk_id"]
             ]}
            for row in rows
        ],
    }
    return [
        {"role": "system", "content": llm.SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def prepare_snapshot():
    cases = []
    for fixture in CASES:
        rows = evaluation.search_program_evidence_hybrid(
            evaluation.PROGRAM_ID, fixture["question"], limit=rag.RETRIEVAL_LIMIT
        )
        rag._validate_evidence(evaluation.PROGRAM_ID, rows)
        if not rows:
            raise ValueError("평가 사례의 검색 근거가 없습니다.")
        cases.append({
            "fixture": deepcopy(fixture), "evidence": deepcopy(rows),
            "messages": messages_for(fixture, rows),
        })
        evaluation.emit("snapshot_case", id=fixture["id"], chunks=len(rows))
    return {
        "version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "program_id": evaluation.PROGRAM_ID, "system_prompt": llm.SYSTEM_PROMPT,
        "schema": RagDraft.model_json_schema(), "cases": cases,
    }


def validate_snapshot(snapshot):
    if (snapshot["version"] != 1 or snapshot["program_id"] != evaluation.PROGRAM_ID
            or snapshot["system_prompt"] != llm.SYSTEM_PROMPT
            or snapshot["schema"] != RagDraft.model_json_schema()
            or [item["fixture"] for item in snapshot["cases"]] != CASES):
        raise ValueError("평가 스냅샷의 프로그램·질문·프롬프트·스키마가 현재 코드와 다릅니다.")
    for item in snapshot["cases"]:
        rows = item["evidence"]
        rag._validate_evidence(evaluation.PROGRAM_ID, rows)
        if not rows or item["messages"] != messages_for(item["fixture"], rows):
            raise ValueError("평가 스냅샷의 본문·구절 ID·순서가 고정 입력과 다릅니다.")


def baseline_comparison(snapshot, path):
    if path is None:
        return {"available": False, "exact_previous_input_verified": False}
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    previous = {event["id"]: event for event in events if event.get("event") == "case"}
    cases = []
    for item in snapshot["cases"]:
        fixture = item["fixture"]
        old = previous.get(fixture["id"])
        cases.append({
            "id": fixture["id"], "previous_result_available": old is not None,
            "question_equal": old["question"] == fixture["question"] if old else None,
            "chunk_order_equal": [r["chunk_id"] for r in old["retrieved_chunks"]]
            == [r["chunk_id"] for r in item["evidence"]] if old else None,
            "previous_status": old["status"] if old else None,
            "previous_actual_model": old["actual_model"] if old else None,
            "previous_elapsed_seconds_including_retrieval": old["elapsed_seconds"] if old else None,
        })
    return {
        "available": True, "record_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cases": cases, "exact_previous_input_verified": False,
        "limitations": [
            "이전 기록에 전체 입력·프롬프트 해시가 없어 입력 동일성은 확정할 수 없음",
            "이전 시간은 검색 포함이며 토큰 사용량은 기록되지 않음",
        ],
    }


def request_observer(parse, metrics, messages, model, effort):
    """Observe the unchanged SDK call; never retry or substitute a model."""
    def observed(resource, **kwargs):
        if metrics["requests"]:
            raise RuntimeError("평가 사례당 LLM 요청은 한 번만 허용합니다.")
        if (kwargs["input"] != messages or kwargs["model"] != model
                or kwargs.get("reasoning") != ({"effort": effort} if effort is not None else None)
                or kwargs["text_format"] is not RagDraft
                or kwargs["max_output_tokens"] != 2500 or kwargs["store"] is not False):
            raise RuntimeError("실제 LLM 호출이 고정한 평가 설정과 다릅니다.")
        metrics["requests"] += 1
        started = time.perf_counter()
        try:
            response = parse(resource, **kwargs)
        finally:
            metrics["llm_seconds"] = round(time.perf_counter() - started, 3)
        metrics["actual_model"] = response.model
        reasoning = getattr(response, "reasoning", None)
        metrics["response_reasoning_effort"] = getattr(reasoning, "effort", None)
        usage = getattr(response, "usage", None)
        metrics["usage"] = {
            key: getattr(usage, key, None)
            for key in ("input_tokens", "output_tokens", "total_tokens")
        }
        for key, detail, field in (
            ("reasoning_tokens", "output_tokens_details", "reasoning_tokens"),
            ("cached_input_tokens", "input_tokens_details", "cached_tokens"),
        ):
            metrics["usage"][key] = getattr(getattr(usage, detail, None), field, None)
        parsed = getattr(response, "output_parsed", None)
        if isinstance(parsed, RagDraft):
            metrics["draft"] = parsed.model_dump()
        return response
    return observed


def evaluate_snapshot(snapshot):
    validate_snapshot(snapshot)
    llm.load_llm_environment()
    model, effort = llm.get_rag_settings()
    evaluation.emit(
        "configuration", requested_model=model, reasoning_effort=effort,
        max_output_tokens=2500, timeout_seconds=45.0, max_retries=0, store=False,
        sdk_version=version("openai"), snapshot_sha256=digest(snapshot),
        prompt_sha256=digest(llm.SYSTEM_PROMPT), schema_sha256=digest(snapshot["schema"]),
        timing_scope="고정 입력 사용: 검색·로컬 임베딩 시간 제외",
    )
    succeeded = structural = gold = failed = requests = 0
    stop = False
    for item in snapshot["cases"]:
        case, rows = item["fixture"], item["evidence"]
        if stop:
            evaluation.emit("case_skipped", id=case["id"], reason="request_configuration_or_access_error")
            continue
        metrics = {"requests": 0, "usage": None, "actual_model": None}
        observed = request_observer(Responses.parse, metrics, item["messages"], model, effort)
        started = time.perf_counter()
        try:
            # Only this evaluation uses frozen rows; production retrieval is unchanged.
            with patch.object(rag, "search_program_evidence_hybrid", return_value=deepcopy(rows)), \
                    patch.object(Responses, "parse", observed):
                result = rag.answer_program_question(evaluation.PROGRAM_ID, case["question"])
        except (RagLLMError, RagSearchError, RagResponseValidationError) as exc:
            failed += 1
            cause = exc.__cause__
            status = getattr(cause, "status_code", None)
            status = status if type(status) is int else None
            code = getattr(cause, "code", None)
            code = code if isinstance(code, str) and code in KNOWN_ERROR_CODES else None
            evaluation.emit(
                "execution_error", id=case["id"], error_type=type(exc).__name__,
                http_status=status, api_error_code=code,
                validation_issues=exc.issues if isinstance(exc, RagResponseValidationError) else [],
                metrics=metrics, elapsed_seconds=round(time.perf_counter() - started, 3),
            )
            stop = (status in {400, 401, 403, 404, 429} or code == "insufficient_quota"
                    or isinstance(exc, RagConfigurationError))
        else:
            succeeded += 1
            checks = evaluation.check_result(result, case)
            structural += checks["structure_valid"] and checks["citation_identity_quote_and_provenance_match"]
            gold += checks["status_matches"] and checks["expected_evidence_cited_or_no_claims"]
            evaluation.emit(
                "case", id=case["id"], question=case["question"],
                input_sha256=digest(item["messages"]), metrics=metrics,
                elapsed_seconds=round(time.perf_counter() - started, 3),
                status=result["status"], answer=result["answer"], claims=result["claims"],
                question_parts=result["question_parts"], unanswered_parts=result["unanswered_parts"],
                checks=checks,
            )
        requests += metrics["requests"]
    evaluation.emit(
        "summary", planned=len(snapshot["cases"]), requests=requests, completed=succeeded,
        execution_errors=failed, structural_checks_passed=structural,
        expected_status_and_evidence_checks_passed=gold,
        semantic_review="자동 구조·정답 청크 검증은 주장과 인용의 의미적 일치를 보장하지 않음",
    )
    return 0 if structural == gold == len(snapshot["cases"]) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--baseline-log", type=Path)
    args = parser.parse_args()
    if args.prepare:
        if args.snapshot.exists():
            parser.error("스냅샷 파일이 이미 있습니다. 덮어쓰지 않습니다.")
        snapshot = prepare_snapshot()
        with args.snapshot.open("x", encoding="utf-8") as stream:
            json.dump(snapshot, stream, ensure_ascii=False, indent=2)
        evaluation.emit("snapshot_created", path=str(args.snapshot), sha256=digest(snapshot))
        return 0
    snapshot = json.loads(args.snapshot.read_text())
    validate_snapshot(snapshot)
    evaluation.emit("baseline_comparison", **baseline_comparison(snapshot, args.baseline_log))
    return evaluate_snapshot(snapshot)


if __name__ == "__main__":
    raise SystemExit(main())
