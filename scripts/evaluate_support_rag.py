"""선택한 지원제도 RAG를 사례당 한 번 평가하고 전체 결과를 JSONL에 기록한다.

프로젝트 루트에서:
    /opt/miniconda3/envs/global-in/bin/python -B -m scripts.evaluate_support_rag
    /opt/miniconda3/envs/global-in/bin/python -B -m scripts.evaluate_support_rag --live

기본 모드는 계획만 출력한다. --live는 읽기 전용 DB 조회와 기존 OpenAI 호출을
실행한다. --output 미지정 시 임시 디렉터리에 새 로그를 만들며 기존 파일은
덮어쓰지 않는다. 로그에는 질문·전체 답변·인용·안전한 오류·계측을 기록한다.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from openai.resources.responses import Responses

from app.models.rag import RagConfigurationError, RagResponseValidationError
from app.models.support_rag import SupportRagResult
from app.services import support_rag as rag


CASES = (
    {"id": "rtp_covered", "support_program_id": "AU_RTP", "expected_status": "answered",
     "question": "RTP는 어떤 학위 과정이 대상이며, 학사와 수업형 석사도 포함되나요?"},
    {"id": "rtp_missing", "support_program_id": "AU_RTP", "expected_status": "insufficient_evidence",
     "question": "RTP가 건강보험료를 매달 얼마 지원하는지 알려주세요."},
    {"id": "settlement_mixed", "support_program_id": "KR_SUPPORT_SETTLEMENT", "expected_status": "partial",
     "question": "해외취업정착지원금의 최대 지원금, 2027년 신청 마감일, 현재 모집 중인지 각각 알려주세요."},
)


def check_result(result):
    """자동 검사는 구조·원문·출처 연결만 확인한다. 의미 판단은 별도이다."""
    SupportRagResult.model_validate_json(json.dumps(result, ensure_ascii=False))
    rows = {row["chunk_id"]: row for row in result["evidence"]}
    checks = []
    for claim in result["claims"]:
        for citation in claim["citations"]:
            row = rows[citation["chunk_id"]]
            checks.append(
                row["support_program_id"] == result["support_program_id"]
                and citation["quote"] in row["body"]
                and citation["source_missing"] == (not row["source_urls"])
                and all(citation[key] == row[key] for key in (
                    "document_id", "revision_id", "title", "source_urls", "source_references",
                    "answer_approved", "content_review_status",
                ))
            )
    return {
        "structure_valid": True, "citation_count": len(checks),
        "citation_identity_quote_source_and_approval_match": all(checks),
        "development_flags_preserved": result["development_only"] is True
        and result["public_release_status"] == "not_assessed" and result["eligibility_assessed"] is False,
        "semantic_quality_automatically_certified": False,
    }


def request_observer(parse, metrics):
    def observed(resource, **kwargs):
        if metrics["requests"]:
            raise RuntimeError("사례당 LLM 호출은 한 번만 허용합니다.")
        metrics["requests"] += 1
        metrics["requested_model"] = kwargs["model"]
        metrics["reasoning"] = kwargs.get("reasoning")
        started = time.perf_counter()
        try:
            response = parse(resource, **kwargs)
        finally:
            metrics["llm_seconds"] = round(time.perf_counter() - started, 3)
        metrics["actual_model"] = response.model
        usage = getattr(response, "usage", None)
        metrics["usage"] = {key: getattr(usage, key, None) for key in (
            "input_tokens", "output_tokens", "total_tokens",
        )}
        parsed = getattr(response, "output_parsed", None)
        metrics["draft"] = parsed.model_dump(mode="json") if parsed is not None else None
        return response
    return observed


def _safe_error(exc):
    status = getattr(exc.__cause__, "status_code", None)
    code = getattr(exc.__cause__, "code", None)
    return {
        "error_type": type(exc).__name__,
        "http_status": status if type(status) is int else None,
        "error_code": code if isinstance(code, str) and code in {
            "invalid_api_key", "model_not_found", "permission_denied",
            "insufficient_quota", "rate_limit_exceeded",
        } else None,
        "validation_issues": exc.issues if isinstance(exc, RagResponseValidationError) else [],
    }


def evaluate_cases(stream, cases=CASES):
    def record(event, **fields):
        stream.write(json.dumps({"event": event, **fields}, ensure_ascii=False) + "\n")
        stream.flush()

    rag.load_llm_environment()
    configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    try:
        model, effort = rag.get_rag_settings()
    except Exception as exc:
        record("configuration_error", **_safe_error(exc))
        return 1
    record("environment", utc=datetime.now(timezone.utc).isoformat(),
           api_key_configured=configured, requested_model=model, reasoning_effort=effort,
           maximum_requests=len(cases))
    if not configured:
        record("summary", completed=0, errors=0, skipped=len(cases), llm_requests=0,
               reason="OPENAI_API_KEY_not_configured")
        return 1
    completed = errors = total_requests = skipped = 0
    stop = False
    for case in cases:
        if stop:
            skipped += 1
            record("case_skipped", id=case["id"], reason="request_configuration_or_access_error")
            continue
        metrics, snapshot = {"requests": 0}, {}
        load_info, load_evidence = rag._load_support_info, rag._load_all_evidence

        def observed_info(sid):
            info = load_info(sid)
            snapshot["support_info"] = info.model_dump(mode="json") if info is not None else None
            return info

        def observed_evidence(sid):
            rows = load_evidence(sid)
            snapshot["evidence"] = deepcopy(rows)
            return rows

        result = None
        started = time.perf_counter()
        try:
            with patch.object(Responses, "parse", request_observer(Responses.parse, metrics)), \
                    patch.object(rag, "_load_support_info", observed_info), \
                    patch.object(rag, "_load_all_evidence", observed_evidence):
                result = rag.answer_support_question(case["support_program_id"], case["question"])
            checks = check_result(result)
        except Exception as exc:
            errors += 1
            error = _safe_error(exc)
            record("execution_error", **case, error=error, result=result, snapshot=snapshot, metrics=metrics,
                   elapsed_seconds=round(time.perf_counter() - started, 3))
            stop = isinstance(exc, RagConfigurationError) or error["http_status"] in {400, 401, 403, 404, 429}
            print(json.dumps({"id": case["id"], "event": "execution_error", **error}, ensure_ascii=False), flush=True)
        else:
            completed += 1
            record("case", **case, result=result, snapshot=snapshot, metrics=metrics, checks=checks,
                   status_matches_expected=result["status"] == case["expected_status"],
                   elapsed_seconds=round(time.perf_counter() - started, 3),
                   semantic_review="주장·조건·수치와 인용의 의미는 별도 검토 필요")
            print(json.dumps({"id": case["id"], "status": result["status"], "checks": checks}, ensure_ascii=False), flush=True)
        total_requests += metrics["requests"]
    record("summary", planned=len(cases), completed=completed, errors=errors, skipped=skipped,
           llm_requests=total_requests, semantic_quality_automatically_certified=False)
    return 0 if completed == len(cases) and not errors else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.live:
        print(json.dumps({"event": "plan", "cases": CASES, "maximum_requests": len(CASES),
                          "model_selection": "기존 get_rag_settings() 설정 사용"}, ensure_ascii=False))
        return 0
    if args.output is None:
        fd, path = tempfile.mkstemp(prefix="global_in_support_rag_", suffix=".jsonl")
        stream = os.fdopen(fd, "w", encoding="utf-8")
    else:
        path = str(args.output)
        stream = args.output.open("x", encoding="utf-8")
    print(json.dumps({"event": "log", "path": path}, ensure_ascii=False), flush=True)
    with stream:
        return evaluate_cases(stream)


if __name__ == "__main__":
    raise SystemExit(main())
