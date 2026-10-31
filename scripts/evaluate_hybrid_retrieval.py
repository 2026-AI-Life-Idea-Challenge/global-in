"""Compare keyword, unchanged raw-vector baseline, and RRF hybrid.

Run from the repository root:
    /opt/miniconda3/envs/global-in/bin/python -B -m scripts.evaluate_hybrid_retrieval

Ground-truth IDs/questions occur only in evaluation fixtures. The search
modules contain topic rules and never read these labels. Output is JSON Lines.
"""

import os

os.environ.update({
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
    "HF_HUB_DISABLE_PROGRESS_BARS": "1",
    "TOKENIZERS_PARALLELISM": "false",
})

import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from app.retrieval.hybrid_search import (
    CANDIDATE_LIMIT, EVIDENCE_FIELDS, RRF_K,
    _fuse_rankings, search_program_evidence_hybrid,
)
from app.retrieval.keyword_search import (
    TEXT_SEARCH_CONFIG, TOPIC_LEXICON, expand_search_terms,
    search_program_evidence_by_keyword,
)
from app.retrieval.program_evidence import search_program_evidence
from app.retrieval.query_embedding import embed_query_local
from app.retrieval.vector_search import search_program_evidence_by_vector
from scripts.evaluate_program_retrieval import (
    CASES as EXISTING_CASES,
    EVIDENCE as EXISTING_LABELS,
    PROGRAM_ID,
    load_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
NEW_CASES = [
    {
        "id": "new_age_ko", "topic": "age", "language": "ko",
        "question": "한국인이 신청할 때 적용되는 연령 상한과 접수 시점 기준이 궁금합니다.",
    },
    {
        "id": "new_age_en", "topic": "age", "language": "en",
        "question": "What age limit applies to South Korean applicants at the time of application?",
    },
    {
        "id": "new_funds_ko", "topic": "funds", "language": "ko",
        "question": "초기 체류 자금과 출국 항공료도 따로 준비해야 하나요?",
    },
    {
        "id": "new_funds_en", "topic": "funds", "language": "en",
        "question": "What savings are expected for the initial stay, and is onward travel money separate?",
    },
    {
        "id": "new_passport_ko", "topic": "passport", "language": "ko",
        "question": "유효한 여권을 가진 어느 나라 시민이 신청할 수 있나요?",
    },
    {
        "id": "new_passport_en", "topic": "passport", "language": "en",
        "question": "Which passports are eligible for this visa?",
    },
    {
        "id": "new_character_ko", "topic": "character", "language": "ko",
        "question": "인성 심사와 경찰 증명서 제출 기준에 대한 근거를 찾고 싶어요.",
    },
    {
        "id": "new_character_en", "topic": "character", "language": "en",
        "question": "What character requirements and police certificates are mentioned for applicants?",
    },
    {
        "id": "new_insurance_ko", "topic": "insurance", "language": "ko",
        "question": "해외 체류 중 건강보험 가입이 의무인가요?",
    },
    {
        "id": "new_employer_en", "topic": "employer", "language": "en",
        "question": "How long may I work for the same employer?",
    },
]
PROTECTED = (
    "requirements.txt", "app/services/database.py",
    "app/retrieval/program_evidence.py", "app/retrieval/query_embedding.py",
    "app/retrieval/vector_search.py", "scripts/evaluate_program_retrieval.py",
    "app/retrieval/keyword_search.py", "app/retrieval/hybrid_search.py",
    "scripts/evaluate_hybrid_retrieval.py",
    "scripts/ingest/common/knowledge/embed_chunks.py",
)


def emit(event: str, **values) -> None:
    print(json.dumps({"event": event, **values}, ensure_ascii=False), flush=True)


def file_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in PROTECTED
    }


def result_metrics(rows: list[dict], gold_id: str | None, score_key: str) -> dict:
    rank = next(
        (index for index, row in enumerate(rows, 1) if row["chunk_id"] == gold_id),
        None,
    )
    return {
        "gold_rank": rank,
        "top1_hit": rank == 1 if gold_id is not None else None,
        "top3_hit": rank <= 3 if rank is not None else (
            False if gold_id is not None else None
        ),
        "returned_count": len(rows),
        "results_without_direct_evidence": gold_id is None and bool(rows),
        "score_type": score_key,
        "top3": [
            {"document_id": row["document_id"], "score": row[score_key]}
            for row in rows[:3]
        ],
    }


def validate_rankings(
    keyword: list[dict], vector: list[dict], hybrid: list[dict],
    baseline: dict[str, dict],
) -> None:
    for rows in (keyword, vector, hybrid):
        if len(rows) != len({row["chunk_id"] for row in rows}):
            raise RuntimeError("청크가 중복됐습니다.")
        for row in rows:
            if {key: row[key] for key in EVIDENCE_FIELDS} != baseline[row["chunk_id"]]:
                raise RuntimeError("기존 근거 필드 또는 범위/활성 상태가 달라졌습니다.")
    if keyword != sorted(keyword, key=lambda row: (-row["keyword_score"], row["chunk_id"])):
        raise RuntimeError("키워드 정렬이 잘못됐습니다.")
    if vector != sorted(vector, key=lambda row: (-row["similarity"], row["chunk_id"])):
        raise RuntimeError("벡터 정렬이 잘못됐습니다.")
    if hybrid != _fuse_rankings(vector, keyword, CANDIDATE_LIMIT):
        raise RuntimeError("공개 하이브리드 함수와 독립 검색 결과 합성이 다릅니다.")
    keyword_by_id = {row["chunk_id"]: row for row in keyword}
    vector_by_id = {row["chunk_id"]: row for row in vector}
    keyword_ranks = {row["chunk_id"]: rank for rank, row in enumerate(keyword, 1)}
    vector_ranks = {row["chunk_id"]: rank for rank, row in enumerate(vector, 1)}
    for row in hybrid:
        chunk_id = row["chunk_id"]
        kr, vr = keyword_ranks.get(chunk_id), vector_ranks.get(chunk_id)
        expected = sum(1.0 / (RRF_K + rank) for rank in (vr, kr) if rank is not None)
        if (
            row["keyword_rank"] != kr or row["vector_rank"] != vr
            or not math.isclose(row["rrf_score"], expected, rel_tol=1e-12)
            or row["keyword_score"] != keyword_by_id.get(chunk_id, {}).get("keyword_score")
            or row["vector_similarity"] != vector_by_id.get(chunk_id, {}).get("similarity")
        ):
            raise RuntimeError("검색별 점수/순위 또는 RRF 점수가 잘못됐습니다.")


def main() -> None:
    before = file_hashes()
    snapshot = load_snapshot()
    baseline_rows = search_program_evidence(PROGRAM_ID, limit=100)
    baseline = {row["chunk_id"]: row for row in baseline_rows}
    if set(baseline) != set(snapshot) or not all(len(row) == 18 for row in baseline_rows):
        raise RuntimeError("평가 대상이 기존 9개 근거와 다릅니다.")

    labels = {key: value["chunk_id"] for key, value in EXISTING_LABELS.items()}
    for topic, document_id, quote in (
        ("passport", "POLICY:AU_417_FIRST_POL_01", "You must be a citizen of and hold a valid passport"),
        ("character", "POLICY:AU_417_FIRST_POL_06", "You must meet our character requirement."),
    ):
        candidates = [
            row for row in snapshot.values()
            if row["document_id"] == document_id and quote in row["body"]
        ]
        if len(candidates) != 1:
            raise RuntimeError("새 평가 근거를 다시 검토해야 합니다.")
        labels[topic] = candidates[0]["chunk_id"]
    cases = [
        {**case, "group": "existing"} for case in EXISTING_CASES
    ] + [{**case, "group": "new"} for case in NEW_CASES]
    emit(
        "settings", program_id=PROGRAM_ID, candidate_limit=CANDIDATE_LIMIT,
        rrf_k=RRF_K, rrf_weights="equal", config=TEXT_SEARCH_CONFIG,
        title_weight="A", body_weight="B", lexicon=TOPIC_LEXICON,
        embedding_input="original question; no instruction",
        gold_labels=labels, evidence_labels_used_by_search=False,
        existing_questions=6, new_questions=10, query_count=len(cases),
        assessment_scope="one program; manually labeled topics; dictionary is not independently held out",
    )

    reports = []
    for case in cases:
        text = case["question"]
        keyword = search_program_evidence_by_keyword(PROGRAM_ID, text, limit=100)
        vector = search_program_evidence_by_vector(
            PROGRAM_ID, embed_query_local(text), limit=100
        )
        hybrid = search_program_evidence_hybrid(PROGRAM_ID, text, limit=100)
        validate_rankings(keyword, vector, hybrid, baseline)
        gold_id = labels[case["topic"]]
        report = {
            "case_id": case["id"], "group": case["group"],
            "topic": case["topic"], "language": case["language"],
            "question": text, "expanded_terms": expand_search_terms(text),
            "evidence_exists": gold_id is not None, "gold_chunk_id": gold_id,
            "keyword": result_metrics(keyword, gold_id, "keyword_score"),
            "vector": result_metrics(vector, gold_id, "similarity"),
            "hybrid": result_metrics(hybrid, gold_id, "rrf_score"),
        }
        reports.append(report)
        emit("comparison", **report)

    aggregate = {}
    for group in ("all", "existing", "new"):
        selected = [row for row in reports if group == "all" or row["group"] == group]
        supported = [row for row in selected if row["evidence_exists"]]
        unsupported = [row for row in selected if not row["evidence_exists"]]
        aggregate[group] = {}
        for method in ("keyword", "vector", "hybrid"):
            top1 = sum(row[method]["top1_hit"] for row in supported)
            top3 = sum(row[method]["top3_hit"] for row in supported)
            aggregate[group][method] = {
                "answerable_cases": len(supported),
                "top1_hits": top1, "top3_hits": top3,
                "top1_rate": top1 / len(supported) if supported else None,
                "top3_rate": top3 / len(supported) if supported else None,
                "unanswerable_cases": len(unsupported),
                "unanswerable_with_results": sum(
                    row[method]["returned_count"] > 0 for row in unsupported
                ),
            }
    if load_snapshot() != snapshot or file_hashes() != before:
        raise RuntimeError("평가 중 데이터 또는 파일이 변경됐습니다.")
    emit(
        "summary", status="completed", metrics=aggregate,
        fields_and_scope_preserved=True, ranks_and_scores_checked=True,
        no_keyword_rank_for_nonmatches=True, files_unchanged=True,
        note="Retrieval is not answerability. Candidate cutoff and dictionary coverage limit generalization.",
    )


if __name__ == "__main__":
    main()
