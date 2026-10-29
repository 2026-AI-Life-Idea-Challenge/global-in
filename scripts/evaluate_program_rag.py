"""Four base cases plus four optional variants; stdout only, no writes.

Run from the project root:
    env -u OPENAI_API_KEY /opt/miniconda3/envs/global-in/bin/python -B \
        -m scripts.evaluate_program_rag --live --include-variants

Structural/gold checks below are not a general semantic-entailment judge.
Read each emitted claim and quote to review its actual support and scope.
"""

import argparse
import json
import os
import time

# Only query embeddings execute locally; prevent Hugging Face network access.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from app.models.rag import RagLLMError, RagResponseValidationError, RagSearchError
from app.retrieval.hybrid_search import search_program_evidence_hybrid
from app.services.program_rag import answer_program_question, question_part_in_request
from app.services.rag_llm import load_llm_environment
from scripts.evaluate_program_retrieval import EVIDENCE, PROGRAM_ID

CASES = [
    {
        "id": "age_ko", "expected_status": "answered", "topic": "age",
        "question": "한국 국적자는 호주 첫 번째 워킹홀리데이 비자(subclass 417)를 몇 살까지 신청할 수 있나요?",
    },
    {
        "id": "funds_en", "expected_status": "answered", "topic": "funds",
        "question": "How much money should I have for my initial stay, and is onward travel money separate, for the first Working Holiday visa (subclass 417)?",
    },
    {
        "id": "insurance_ko", "expected_status": "insufficient_evidence", "topic": None,
        "question": "호주 첫 번째 워킹홀리데이 비자(subclass 417)는 건강보험 가입이 의무인가요?",
    },
    {
        "id": "age_and_insurance_ko", "expected_status": "partial", "topic": "age",
        "question": "한국 국적자의 호주 첫 번째 워킹홀리데이 비자(subclass 417) 신청 연령 상한과 건강보험 가입 의무를 각각 알려주세요.",
    },
]

# Evaluation fixtures only: never passed to generation as expected answers.
VARIANT_CASES = [
    {
        "id": "age_en_variant", "expected_status": "answered", "topic": "age",
        "question": "What is the upper application age for a Republic of Korea passport holder seeking a first Australian subclass 417 visa?",
    },
    {
        "id": "funds_ko_variant", "expected_status": "answered", "topic": "funds",
        "question": "호주 첫 워홀 417의 초기 체류비 안내 금액은 얼마이고, 출국 항공료는 그 금액과 별도로 필요한가요?",
    },
    {
        "id": "insurance_en_variant", "expected_status": "insufficient_evidence", "topic": None,
        "question": "Is purchasing health insurance mandatory for a first Australian Working Holiday visa (subclass 417)?",
    },
    {
        "id": "age_and_insurance_en_variant", "expected_status": "partial", "topic": "age",
        "question": "For a Korean passport holder applying for the first Australian subclass 417 visa, what is the maximum age and must they buy health insurance?",
    },
]


def emit(event, **values):
    print(json.dumps({"event": event, **values}, ensure_ascii=False), flush=True)


def check_result(result, case):
    rows = {row["chunk_id"]: row for row in result["evidence"]}
    citation_checks = []
    cited_ids = set()
    for claim in result["claims"]:
        for citation in claim["citations"]:
            row = rows[citation["chunk_id"]]
            cited_ids.add(citation["chunk_id"])
            citation_checks.append(
                citation["quote"] in row["body"]
                and all(citation[key] == row[key] for key in (
                    "source_urls", "source_references", "answer_approved",
                    "content_review_status", "document_id", "revision_id", "title",
                ))
            )
    expected_chunk = EVIDENCE[case["topic"]]["chunk_id"] if case["topic"] else None
    gold_ok = expected_chunk in cited_ids if expected_chunk else not result["claims"]
    return {
        "status_matches": result["status"] == case["expected_status"],
        "citation_identity_quote_and_provenance_match": all(citation_checks),
        "expected_evidence_cited_or_no_claims": gold_ok,
        "question_parts_in_request": all(question_part_in_request(part, case["question"]) for part in result["question_parts"]),
        "development_only": result["development_only"],
        "public_release_status": result["public_release_status"],
        "eligibility_assessed": result["eligibility_assessed"],
    }


def evaluate_live_cases(cases):
    """A case failure is recorded, not converted into insufficient evidence.

    Authentication failures are global configuration failures: do not repeat
    the same unauthorized request for the remaining cases.
    """
    checks = []
    errors = skipped = 0
    authentication_failed = False
    for case in cases:
        if authentication_failed:
            skipped += 1
            emit("case_skipped", case=case["id"], reason="authentication_configuration_failed")
            continue
        started = time.perf_counter()
        try:
            result = answer_program_question(PROGRAM_ID, case["question"])
        except (RagSearchError, RagLLMError, RagResponseValidationError) as exc:
            # Never print SDK messages, response bodies, connection strings or keys.
            cause = exc.__cause__
            status = getattr(cause, "status_code", None)
            status = status if type(status) is int else None
            errors += 1
            emit("execution_error", case=case["id"], error_type=type(exc).__name__,
                 cause_type=type(cause).__name__ if cause else None,
                 http_status=status,
                 validation_issues=exc.issues if isinstance(exc, RagResponseValidationError) else [],
                 elapsed_seconds=round(time.perf_counter() - started, 3))
            authentication_failed = status == 401
            continue
        outcome = check_result(result, case)
        checks.append(outcome)
        emit("case", id=case["id"], question=case["question"],
             elapsed_seconds=round(time.perf_counter() - started, 3),
             requested_model=result["requested_model"], actual_model=result["model"],
             status=result["status"], answer=result["answer"], claims=result["claims"],
             question_parts=result["question_parts"],
             unanswered_parts=result["unanswered_parts"],
             retrieved_chunks=[{
                 "chunk_id": row["chunk_id"], "answer_approved": row["answer_approved"],
                 "rrf_score": row["rrf_score"],
             } for row in result["evidence"]],
             checks=outcome, semantic_review="각 주장과 원문 인용의 의미·대상·한정 조건을 검토해야 함")
    passed = sum(
        c["status_matches"] and c["citation_identity_quote_and_provenance_match"]
        and c["expected_evidence_cited_or_no_claims"] and c["question_parts_in_request"]
        for c in checks
    )
    emit("summary", status="completed_with_errors" if errors else "completed",
         cases_planned=len(cases), live_cases_completed=len(checks),
         execution_errors=errors, skipped_cases=skipped,
         structural_and_gold_checks_passed=passed,
         semantic_review="자동 구조·정답 청크 검증과 별도로 출력된 주장·인용문을 검토해야 함")
    return 0 if passed == len(cases) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="사례당 실제 OpenAI 호출 최대 1회")
    mode.add_argument("--retrieval-only", action="store_true", help="외부 전송 없이 검색 결과만 확인")
    parser.add_argument("--include-variants", action="store_true", help="표현을 바꾼 4개 질문 추가")
    args = parser.parse_args()
    cases = CASES + VARIANT_CASES if args.include_variants else CASES
    if args.retrieval_only:
        for case in cases:
            rows = search_program_evidence_hybrid(PROGRAM_ID, case["question"], limit=5)
            emit("retrieval_only", id=case["id"], question=case["question"],
                 external_llm_called=False, retrieved_chunks=[{
                     "chunk_id": row["chunk_id"], "title": row["title"],
                     "body_characters": len(row["body"]),
                     "source_urls": row["source_urls"],
                     "answer_approved": row["answer_approved"],
                     "document_active": row["document_active"],
                     "chunk_active": row["chunk_active"],
                 } for row in rows])
        return 0
    if not args.live:
        emit("plan", cases=len(cases), instruction="실제 평가를 실행하려면 --live를 지정하세요.")
        return 0
    load_llm_environment()
    key_configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    emit("environment", key_configured=key_configured,
         requested_model=os.environ.get("CONSULT_MODEL", "gpt-4o-mini"),
         maximum_requests=len(cases))
    if not key_configured:
        emit("summary", status="skipped", reason="OPENAI_API_KEY 미설정",
             live_cases_completed=0, semantic_review="미검증")
        return 0
    return evaluate_live_cases(cases)


if __name__ == "__main__":
    raise SystemExit(main())
