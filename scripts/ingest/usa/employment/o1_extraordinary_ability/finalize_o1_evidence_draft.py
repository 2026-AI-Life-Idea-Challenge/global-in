
import hashlib
import json
import re
from pathlib import Path

from scripts.ingest.usa.employment.o1_extraordinary_ability.build_o1_policy_evidence import (
    load_source_pages,
)
from scripts.ingest.usa.employment.o1_extraordinary_ability import (
    validate_o1_dataset,
)


ROOT = Path(
    "data/processed/usa/employment/o1_extraordinary_ability"
)

POLICY_PATH = (
    ROOT / "o1_policy_review_2026_semantic_refined_draft.json"
)

EVIDENCE_INPUT = (
    ROOT / "o1_policy_evidence_2026_semantic_refined_draft.json"
)

EVIDENCE_OUTPUT = (
    ROOT / "o1_policy_evidence_2026_final_draft.json"
)

VALIDATION_OUTPUT = (
    ROOT / "o1_validation_report_2026_final_draft.json"
)

TARGET_POLICY_ID = "O1-71"
TARGET_SOURCE_ID = "DOS-DS160-INSTRUCTIONS"
TARGET_PHRASE = "Print and keep the DS-160 barcode page."


def sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def main():
    # 기존 파일 덮어쓰기 금지
    for path in [EVIDENCE_OUTPUT, VALIDATION_OUTPUT]:
        if path.exists():
            raise FileExistsError(
                f"Output already exists: {path}"
            )

    policy_data = json.loads(
        POLICY_PATH.read_text(encoding="utf-8")
    )

    evidence_data = json.loads(
        EVIDENCE_INPUT.read_text(encoding="utf-8")
    )

    policies = policy_data["policy_records"]
    records = evidence_data["evidence_records"]

    assert len(policies) == 77
    assert len(records) == 77

    sources = {
        source["source_id"]: source
        for source in policy_data["official_sources"]
    }

    policy = next(
        record for record in policies
        if record["policy_id"] == TARGET_POLICY_ID
    )

    evidence = next(
        record for record in records
        if record["policy_id"] == TARGET_POLICY_ID
    )

    assert TARGET_SOURCE_ID in policy["source_ids"]

    source = sources[TARGET_SOURCE_ID]

    # 저장된 원본 파일의 SHA-256 검증 및 텍스트 추출
    pages = load_source_pages(source)

    candidate = None

    for page_number, text in pages:
        match = re.search(
            re.escape(TARGET_PHRASE),
            text,
            flags=re.IGNORECASE,
        )

        if match:
            start = max(0, match.start() - 500)
            end = min(len(text), match.end() + 950)

            candidate = {
                "source_page": page_number,
                "search_phrase": match.group(0),
                "evidence_excerpt": text[start:end],
            }
            break

    if candidate is None:
        raise ValueError(
            "O1-71 target phrase not found in official source"
        )

    # O1-71 Evidence 수정
    evidence["source_id"] = TARGET_SOURCE_ID
    evidence["source_path"] = source["local_path"]
    evidence["source_sha256"] = source["sha256"]
    evidence["source_page"] = candidate["source_page"]
    evidence["search_phrase"] = candidate["search_phrase"]
    evidence["evidence_excerpt"] = candidate["evidence_excerpt"]

    evidence["excerpt_sha256"] = sha256_text(
        candidate["evidence_excerpt"]
    )

    evidence["evidence_type"] = "candidate_excerpt"
    evidence["semantic_support_verified"] = False
    evidence["review_status"] = "needs_review"

    # 보완 대상 28개가 모두 재추출됐는지 확인
    refined_ids = set(
        evidence_data.get("refined_policy_ids", [])
    )

    refined_ids.add(TARGET_POLICY_ID)

    assert len(refined_ids) == 28, (
        f"Expected 28 refined policies, got {len(refined_ids)}"
    )

    evidence_data["refined_policy_ids"] = sorted(refined_ids)
    evidence_data["refinement_status"] = (
        "candidate_refinement_complete_review_pending"
    )

    # 검토 상태 유지
    assert all(
        record["review_status"] == "needs_review"
        for record in policies
    )

    assert all(
        record["review_status"] == "needs_review"
        and record["semantic_support_verified"] is False
        for record in records
    )

    for field in [
        "approved_for_user_answers",
        "approved_for_embedding",
        "embedding_generated",
    ]:
        evidence_data[field] = False

    evidence_data["validation_status"] = "needs_review"

    # 새로운 Evidence JSON 저장
    EVIDENCE_OUTPUT.write_text(
        json.dumps(
            evidence_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== O1-71 EVIDENCE FINALIZATION ===")
    print("Policies:", len(policies))
    print("Evidence:", len(records))
    print("Refined evidence:", len(refined_ids))
    print("Target policy:", TARGET_POLICY_ID)
    print("Target phrase:", evidence["search_phrase"])
    print("Semantic support verified:", False)
    print("Saved:", EVIDENCE_OUTPUT)

    # 기존 검증 함수를 재사용하되 수정본 경로 지정
    validate_o1_dataset.POLICY_PATH = POLICY_PATH
    validate_o1_dataset.EVIDENCE_PATH = EVIDENCE_OUTPUT
    validate_o1_dataset.REPORT_PATH = VALIDATION_OUTPUT

    validate_o1_dataset.main()

    # 검증 보고서 결과 확인
    report = json.loads(
        VALIDATION_OUTPUT.read_text(encoding="utf-8")
    )

    assert report["structural_validation_passed"] is True
    assert report["semantic_validation_approved"] is False
    assert report["legal_validation_approved"] is False

    print("=== FINAL DRAFT STATUS ===")
    print("Policies:", len(policies))
    print("Evidence:", len(records))
    print("Refined evidence:", len(refined_ids))
    print("Structural validation:", "PASS")
    print("Semantic validation:", "PENDING")
    print("Legal validation:", "PENDING")
    print("[PASS] O visa final draft structurally validated")


if __name__ == "__main__":
    main()