"""Evaluate retrieval coverage, ranks, truncation, and query instructions.

Run from the project root:
    /opt/miniconda3/envs/global-in/bin/python -B -m scripts.evaluate_program_retrieval

Only query embeddings are computed. Document vectors and existing files are
never changed. Output is JSON Lines on stdout, with no full bodies or vectors.
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

from collections import Counter
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True

from psycopg.rows import dict_row

from app.retrieval import query_embedding as qe
from app.retrieval.vector_search import search_program_evidence_by_vector
from app.services.database import get_connection

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "AU:subclass_417_first"
INSTRUCTION = (
    "Given a web search query, retrieve relevant passages that answer the query"
)
INSTRUCTION_SOURCE = "https://huggingface.co/Qwen/Qwen3-Embedding-0.6B#transformers-usage"
EXPECTED_BODY_HASHES = {
    "POLICY:AU_417_FIRST_POL_01::wording-v2-20261028:f700ab7f87a2b095::chunk0": "f700ab7f87a2b095157fb8c50d3c93318141f78749fd90d1631a0ec088ecaa99",
    "POLICY:AU_417_FIRST_POL_02::age-scope-v1-20261028:4c064cfb5cf75fa1::chunk0": "4c064cfb5cf75fa15256d22a4acb7ce04e42fdcea535c949f1b8c61e25005156",
    "POLICY:AU_417_FIRST_POL_03::wording-v2-20261028:847eda7a1e566652::chunk0": "847eda7a1e56665235b05faee2f608135c4d59622082121eea6c67b3f096bbec",
    "POLICY:AU_417_FIRST_POL_04::wording-v2-20261028:3d8bc7eb2f623a6d::chunk0": "3d8bc7eb2f623a6dc45c73f3678dd7c6985c38f55cb4ba627710d65484980758",
    "POLICY:AU_417_FIRST_POL_05::wording-v2-20261028:3e1020426eabb510::chunk0": "3e1020426eabb51064ee52d7c893efc7aae704089fe99a6027ea0af644c15451",
    "POLICY:AU_417_FIRST_POL_06::wording-v2-20261028:72e3c349c20476f1::chunk0": "72e3c349c20476f1562a625a1a7fd0d73635870de8089472e73ba6f797809ad9",
    "POLICY:AU_417_FIRST_POL_07::wording-v2-20261028:7985a6819e9cb92c::chunk0": "7985a6819e9cb92c33c5a9f0d64ba71ae4d625ad803daa7c14910803a83ab366",
    "POLICY:AU_417_FIRST_POL_08::wording-v2-20261028:8dbc315999538c7d::chunk0": "8dbc315999538c7d0b7e64d311d813f801e5b0b2c7eee10f811d2a02dc343818",
    "POLICY:AU_417_FIRST_POL_09::wording-v2-20261028:639486f3c27e6d61::chunk0": "639486f3c27e6d615dc1c6b5d91aa59c49b97169370ab96ec34308e9808f4ff2"
}
EVIDENCE = {
    "age": {
        "chunk_id": "POLICY:AU_417_FIRST_POL_02::age-scope-v1-20261028:4c064cfb5cf75fa1::chunk0",
        "reason": "한국 여권국의 연령 상한과 신청 접수 시 연령 조건을 직접 명시한다.",
        "quotes": ["신청 접수 시 만 18세 이상", "Republic of Korea: 35세;"],
    },
    "funds": {
        "chunk_id": "POLICY:AU_417_FIRST_POL_04::wording-v2-20261028:3d8bc7eb2f623a6d::chunk0",
        "reason": "체류 자금의 통상 안내 금액과 별도 출국 비용을 직접 설명한다.",
        "quotes": [
            "This is usually about AUD5,000 for your initial stay",
            "plus the fare to where you are going after leaving Australia.",
        ],
    },
    "employer": {
        "chunk_id": None,
        "reason": "9개 본문에 동일 고용주 근무 기간 제한의 직접 근거가 없다.",
        "quotes": [],
    },
    "insurance": {
        "chunk_id": None,
        "reason": "9개 본문에 건강보험 가입 필요성의 직접 근거가 없다. PIC 건강 심사 기준과 구분했다.",
        "quotes": [],
    },
}
CASES = [
    {
        "id": "age_ko", "topic": "age", "language": "ko", "original_test": True,
        "question": "한국 국적자는 호주 첫 번째 워킹홀리데이 비자(subclass 417)를 몇 살까지 신청할 수 있나요?",
    },
    {
        "id": "age_en", "topic": "age", "language": "en", "original_test": False,
        "question": "What is the maximum age for a South Korean citizen applying for the first Working Holiday visa (subclass 417)?",
    },
    {
        "id": "funds_ko", "topic": "funds", "language": "ko", "original_test": False,
        "question": "호주 첫 번째 워킹홀리데이 비자(subclass 417)를 신청할 때 체류비로 얼마를 준비해야 하나요?",
    },
    {
        "id": "funds_en", "topic": "funds", "language": "en", "original_test": True,
        "question": "How much money should I have to support myself when applying for the first Working Holiday visa (subclass 417)?",
    },
    {
        "id": "employer_ko", "topic": "employer", "language": "ko", "original_test": True,
        "question": "호주 첫 워킹홀리데이 비자에서 같은 고용주 밑에서 얼마나 오래 일할 수 있나요?",
    },
    {
        "id": "insurance_en", "topic": "insurance", "language": "en", "original_test": True,
        "question": "Do I need health insurance for my first Working Holiday visa (subclass 417)?",
    },
]
PROTECTED_FILES = (
    "requirements.txt",
    "app/services/database.py",
    "app/retrieval/program_evidence.py",
    "app/retrieval/query_embedding.py",
    "app/retrieval/vector_search.py",
    "scripts/ingest/common/knowledge/embed_chunks.py",
    "scripts/evaluate_program_retrieval.py",
)


def emit(event: str, **values) -> None:
    print(json.dumps({"event": event, **values}, ensure_ascii=False), flush=True)


def file_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in PROTECTED_FILES
    }


def load_snapshot() -> dict[str, dict]:
    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SHOW transaction_read_only")
            if cursor.fetchone()["transaction_read_only"] != "on":
                raise RuntimeError("읽기 전용 트랜잭션이 아닙니다.")
            cursor.execute(
                """
                SELECT
                    d.document_id, d.revision_id, c.chunk_id, c.body, d.title,
                    d.active AS document_active, c.active AS chunk_active,
                    d.metadata -> 'answer_approved' AS answer_approved
                FROM public.programs AS p
                JOIN public.knowledge_document_targets AS t
                  ON t.target_id = p.program_id AND t.target_type = %s
                JOIN public.knowledge_documents AS d
                  ON (d.document_id, d.revision_id) = (t.document_id, t.revision_id)
                JOIN public.knowledge_chunks AS c
                  ON (c.document_id, c.revision_id) = (d.document_id, d.revision_id)
                WHERE p.program_id = %s AND d.active = TRUE AND c.active = TRUE
                ORDER BY d.document_id, d.revision_id, c.ordinal, c.chunk_id
                """,
                ("PROGRAM", PROGRAM_ID),
            )
            rows = cursor.fetchall()
    chunks = {row["chunk_id"]: row for row in rows}
    observed = {
        key: hashlib.sha256(row["body"].encode("utf-8")).hexdigest()
        for key, row in chunks.items()
    }
    if len(chunks) != len(rows) or observed != EXPECTED_BODY_HASHES:
        raise RuntimeError("9개 청크가 조사 시점과 다릅니다. 평가 근거를 다시 검토하세요.")
    return chunks


def tokenize_body(tokenizer, text: str) -> tuple[dict, dict]:
    full = tokenizer(
        text, padding=False, truncation=False,
        return_offsets_mapping=True,
    )
    kept = tokenizer(
        text, padding=True, truncation=True, max_length=qe.MAX_LENGTH,
        return_offsets_mapping=True,
    )
    return full, kept


def locate_quote(text: str, quote: str, full: dict, kept: dict) -> dict:
    start = text.find(quote)
    if start < 0:
        raise RuntimeError("평가 기준의 근거 문구가 본문에 없습니다.")
    end = start + len(quote)
    indices = [
        index
        for index, (left, right) in enumerate(full["offset_mapping"])
        if left < end and right > start
    ]
    if not indices:
        raise RuntimeError("근거 문구의 토큰 위치를 확인할 수 없습니다.")
    needed = Counter(
        (full["input_ids"][index], *full["offset_mapping"][index])
        for index in indices
    )
    retained = Counter(
        (token, left, right)
        for token, (left, right) in zip(
            kept["input_ids"], kept["offset_mapping"], strict=True
        )
        if left < end and right > start
    )
    return {
        "quote": quote,
        "character_start": start,
        "character_end_exclusive": end,
        "first_token_1based": min(indices) + 1,
        "last_token_1based": max(indices) + 1,
        "fully_retained": all(retained[key] >= count for key, count in needed.items()),
    }


def main() -> None:
    before = file_hashes()
    chunks = load_snapshot()
    tokenizer, model = qe._get_local_components()
    if not tokenizer.is_fast:
        raise RuntimeError("토큰 위치 확인에 fast tokenizer가 필요합니다.")
    if model.config._commit_hash != qe.MODEL_REVISION:
        raise RuntimeError("모델 revision이 지정값과 다릅니다.")
    if tokenizer.padding_side != "right" or tokenizer.truncation_side != "right":
        raise RuntimeError("padding/truncation 방향이 기존 설정과 다릅니다.")
    if model.training or any(
        parameter.device.type != "cpu" or str(parameter.dtype) != "torch.float32"
        for parameter in model.parameters()
    ):
        raise RuntimeError("모델이 CPU float32 eval 상태가 아닙니다.")

    emit(
        "settings", program_id=PROGRAM_ID, model=qe.MODEL_NAME,
        revision=qe.MODEL_REVISION, device="cpu", dtype="float32",
        padding_side="right", truncation_side="right", max_length=qe.MAX_LENGTH,
        pooling="attention-mask mean", normalization="L2",
        instruction=INSTRUCTION, instruction_template="Instruct: {task}\nQuery:{question}",
        instruction_source=INSTRUCTION_SOURCE, offline=True,
        document_vectors_recomputed=False, python=platform.python_version(),
        packages={name: version(name) for name in (
            "torch", "transformers", "tokenizers", "psycopg", "pgvector",
        )},
        missing_reproduction_script=not (ROOT / "scripts/verify_embedding_reproduction.py").exists(),
        truncation_basis="current DB bodies and pinned cached tokenizer; historical tokenizer provenance unverified",
        labels_basis="manual review of all nine full active chunk bodies; not a legal eligibility judgment",
    )

    tokenized = {}
    for chunk_id, row in chunks.items():
        full, kept = tokenize_body(tokenizer, row["body"])
        tokenized[chunk_id] = (full, kept)
        emit(
            "chunk_tokens", chunk_id=chunk_id,
            body_sha256=EXPECTED_BODY_HASHES[chunk_id],
            tokens_total=len(full["input_ids"]),
            tokens_retained=len(kept["input_ids"]),
            truncated=len(full["input_ids"]) > len(kept["input_ids"]),
        )

    evidence_windows = {}
    for topic, label in EVIDENCE.items():
        chunk_id = label["chunk_id"]
        windows = []
        if chunk_id is not None:
            full, kept = tokenized[chunk_id]
            windows = [
                locate_quote(chunks[chunk_id]["body"], quote, full, kept)
                for quote in label["quotes"]
            ]
        evidence_windows[topic] = windows
        emit(
            "evidence_label", topic=topic, evidence_exists=chunk_id is not None,
            gold_chunk_id=chunk_id, reason=label["reason"], quote_windows=windows,
        )

    results = []
    for case in CASES:
        gold_id = EVIDENCE[case["topic"]]["chunk_id"]
        for mode in ("raw", "instruction"):
            text = case["question"]
            if mode == "instruction":
                text = f"Instruct: {INSTRUCTION}\nQuery:{text}"
            query_tokens = len(tokenizer(text, truncation=False)["input_ids"])
            vector = qe.embed_query_local(text)
            hits = search_program_evidence_by_vector(PROGRAM_ID, vector, limit=100)
            if len(hits) != len(chunks) or {hit["chunk_id"] for hit in hits} != set(chunks):
                raise RuntimeError("검색 후보가 평가 대상 9개 청크와 다릅니다.")
            if any(
                hit["body"] != chunks[hit["chunk_id"]]["body"]
                or hit["document_active"] is not True
                or hit["chunk_active"] is not True
                or hit["program_id"] != PROGRAM_ID
                for hit in hits
            ):
                raise RuntimeError("검색 대상 본문 또는 프로그램/활성 상태가 달라졌습니다.")
            rank = next(
                (index for index, hit in enumerate(hits, 1) if hit["chunk_id"] == gold_id),
                None,
            )
            if gold_id is not None and rank is None:
                raise RuntimeError("알려진 근거 청크가 전체 검색 결과에 없습니다.")
            row = {
                "case_id": case["id"], "topic": case["topic"],
                "language": case["language"], "original_test": case["original_test"],
                "question": case["question"], "mode": mode,
                "evidence_exists": gold_id is not None, "gold_chunk_id": gold_id,
                "gold_rank": rank,
                "top1_hit": rank == 1 if gold_id is not None else None,
                "top3_hit": rank <= 3 if rank is not None else None,
                "gold_evidence_fully_retained": (
                    all(window["fully_retained"] for window in evidence_windows[case["topic"]])
                    if gold_id is not None else None
                ),
                "query_tokens_total": query_tokens,
                "query_truncated": query_tokens > qe.MAX_LENGTH,
                "returned_count": len(hits),
                "results_without_direct_evidence": gold_id is None and bool(hits),
                "top3": [
                    {
                        "chunk_id": hit["chunk_id"],
                        "document_id": hit["document_id"],
                        "similarity": hit["similarity"],
                        "is_gold": hit["chunk_id"] == gold_id,
                    }
                    for hit in hits[:3]
                ],
            }
            results.append(row)
            emit("retrieval", **row)

    metrics = {}
    for mode in ("raw", "instruction"):
        supported = [
            row for row in results if row["mode"] == mode and row["evidence_exists"]
        ]
        metrics[mode] = {
            "answerable_cases": len(supported),
            "top1_hits": sum(row["top1_hit"] for row in supported),
            "top3_hits": sum(row["top3_hit"] for row in supported),
            "unanswerable_queries_returning_results": sum(
                row["mode"] == mode and row["results_without_direct_evidence"]
                for row in results
            ),
        }
    if load_snapshot() != chunks:
        raise RuntimeError("평가 도중 청크나 상태가 변경되었습니다.")
    if file_hashes() != before:
        raise RuntimeError("평가 도중 보호 대상 파일이 변경되었습니다.")
    emit(
        "summary", status="completed", metrics=metrics,
        total_embedding_and_search_calls=len(results),
        all_query_inputs_within_limit=not any(row["query_truncated"] for row in results),
        all_document_bodies_within_limit=all(
            len(full["input_ids"]) <= qe.MAX_LENGTH for full, _ in tokenized.values()
        ),
        document_vectors_recomputed=False, protected_files_unchanged=True,
        note="Four answerable queries represent only two topics and one program; no general quality claim.",
    )


if __name__ == "__main__":
    main()
