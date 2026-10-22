
import hashlib
import json
import re
from datetime import date
from pathlib import Path

from scripts.ingest.usa.employment.o1_extraordinary_ability.build_o1_policy_evidence import (
    load_source_pages,
    normalize_text,
)


ROOT = Path(
    "data/processed/usa/employment/o1_extraordinary_ability"
)

POLICY_PATH = ROOT / "o1_policy_review_2026_draft.json"
EVIDENCE_PATH = ROOT / "o1_policy_evidence_2026_refined_draft.json"
REPORT_PATH = ROOT / "o1_validation_report_2026_draft.json"

EXPECTED_POLICY_IDS = {
    f"O1-{i:02d}" for i in range(1, 78)
}

EXPECTED_PROGRAM_ID = "US-WK-04"


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def check(name, passed, details=None):
    return {
        "check": name,
        "passed": bool(passed),
        "details": details,
    }


def main():
    if REPORT_PATH.exists():
        raise FileExistsError(
            f"Report already exists: {REPORT_PATH}"
        )

    policy_data = json.loads(
        POLICY_PATH.read_text(encoding="utf-8")
    )
    evidence_data = json.loads(
        EVIDENCE_PATH.read_text(encoding="utf-8")
    )

    policies = policy_data["policy_records"]
    sources = policy_data["official_sources"]
    records = evidence_data["evidence_records"]
    missing = evidence_data["missing_searches"]

    policy_ids = [x["policy_id"] for x in policies]
    source_ids = [x["source_id"] for x in sources]
    evidence_ids = [x["evidence_id"] for x in records]
    evidence_policy_ids = [x["policy_id"] for x in records]

    policy_map = {
        x["policy_id"]: x for x in policies
    }
    source_map = {
        x["source_id"]: x for x in sources
    }

    checks = []
    mismatches = []
    source_hash_results = []
    source_cache = {}

    # 1. 기본 구조와 ID 검사
    checks.append(check(
        "program_id_consistency",
        policy_data.get("team_reference_program_id")
        == evidence_data.get("team_reference_program_id")
        == EXPECTED_PROGRAM_ID,
    ))

    checks.append(check(
        "policy_count_and_ids",
        len(policies) == 77
        and set(policy_ids) == EXPECTED_POLICY_IDS
        and len(set(policy_ids)) == 77,
    ))

    checks.append(check(
        "source_count_and_unique_ids",
        len(sources) == 11
        and len(set(source_ids)) == 11,
    ))

    checks.append(check(
        "evidence_count_and_unique_ids",
        len(records) == 77
        and len(set(evidence_ids)) == 77,
    ))

    checks.append(check(
        "complete_policy_coverage",
        set(evidence_policy_ids) == EXPECTED_POLICY_IDS
        and len(set(evidence_policy_ids)) == 77,
    ))

    checks.append(check(
        "no_missing_searches",
        len(missing) == 0
        and evidence_data.get("missing_search_count") == 0,
    ))

    checks.append(check(
        "declared_counts_consistent",
        evidence_data.get("policy_count") == len(policies)
        and evidence_data.get("source_count") == len(sources)
        and evidence_data.get("evidence_count") == len(records)
        and evidence_data.get("covered_policy_count")
        == len(set(evidence_policy_ids)),
    ))

    # 2. 출처 연결
    policy_source_links_valid = all(
        bool(p.get("source_ids"))
        and set(p["source_ids"]).issubset(source_map)
        for p in policies
    )

    evidence_source_links_valid = all(
        e["policy_id"] in policy_map
        and e["source_id"] in source_map
        and e["source_id"] in
        policy_map[e["policy_id"]]["source_ids"]
        for e in records
    )

    checks.append(check(
        "policy_source_references",
        policy_source_links_valid,
    ))

    checks.append(check(
        "evidence_source_references",
        evidence_source_links_valid,
    ))

    # 3. 공식 원본 SHA-256 및 텍스트 확인
    all_source_hashes_valid = True

    for source in sources:
        sid = source["source_id"]
        path = Path(source["local_path"])

        exists = path.is_file()
        actual_hash = (
            hashlib.sha256(path.read_bytes()).hexdigest()
            if exists else None
        )
        expected_hash = source["sha256"]

        matched = exists and actual_hash == expected_hash

        source_hash_results.append({
            "source_id": sid,
            "source_path": str(path),
            "exists": exists,
            "hash_matches": matched,
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
        })

        if not matched:
            all_source_hashes_valid = False
            mismatches.append({
                "type": "source_hash_mismatch",
                "source_id": sid,
            })
            continue

        try:
            source_cache[sid] = load_source_pages(source)
        except Exception as exc:
            all_source_hashes_valid = False
            mismatches.append({
                "type": "source_text_load_error",
                "source_id": sid,
                "error": str(exc),
            })

    checks.append(check(
        "official_source_sha256_and_readability",
        all_source_hashes_valid
        and len(source_cache) == 11,
    ))

    # 4. Evidence 원문·해시·검색어 일치
    all_excerpt_hashes_valid = True
    all_excerpts_in_sources = True
    all_search_phrases_in_excerpts = True
    all_evidence_metadata_valid = True

    for evidence in records:
        eid = evidence["evidence_id"]
        sid = evidence["source_id"]
        excerpt = evidence["evidence_excerpt"]
        phrase = evidence["search_phrase"]

        if sha256_text(excerpt) != evidence["excerpt_sha256"]:
            all_excerpt_hashes_valid = False
            mismatches.append({
                "type": "excerpt_hash_mismatch",
                "evidence_id": eid,
            })

        if not phrase or phrase.casefold() not in excerpt.casefold():
            all_search_phrases_in_excerpts = False
            mismatches.append({
                "type": "search_phrase_missing_from_excerpt",
                "evidence_id": eid,
            })

        source = source_map.get(sid)

        if (
            source is None
            or evidence["source_path"] != source["local_path"]
            or evidence["source_sha256"] != source["sha256"]
        ):
            all_evidence_metadata_valid = False
            mismatches.append({
                "type": "evidence_source_metadata_mismatch",
                "evidence_id": eid,
            })

        pages = source_cache.get(sid, [])
        target_page = evidence.get("source_page")

        found = any(
            page_number == target_page
            and normalize_text(excerpt) in page_text
            for page_number, page_text in pages
        )

        if not found:
            all_excerpts_in_sources = False
            mismatches.append({
                "type": "excerpt_not_found_in_source",
                "evidence_id": eid,
                "source_id": sid,
            })

    checks.append(check(
        "evidence_excerpt_sha256",
        all_excerpt_hashes_valid,
    ))

    checks.append(check(
        "evidence_excerpts_exist_in_original_sources",
        all_excerpts_in_sources,
    ))

    checks.append(check(
        "search_phrases_exist_in_excerpts",
        all_search_phrases_in_excerpts,
    ))

    checks.append(check(
        "evidence_source_metadata_consistency",
        all_evidence_metadata_valid,
    ))

    # 5. 검토 및 기능 비활성화 확인
    all_policies_unreviewed = all(
        p.get("review_status") == "needs_review"
        for p in policies
    )

    all_evidence_unreviewed = all(
        e.get("review_status") == "needs_review"
        and e.get("semantic_support_verified") is False
        and e.get("evidence_type") == "candidate_excerpt"
        for e in records
    )

    checks.append(check(
        "all_policy_and_evidence_records_unreviewed",
        all_policies_unreviewed
        and all_evidence_unreviewed,
    ))

    approval_fields = [
        "approved_for_user_answers",
        "approved_for_embedding",
        "embedding_generated",
    ]

    policy_approval_fields = approval_fields + [
        "automatic_eligibility_rules_enabled"
    ]

    all_approvals_disabled = (
        all(
            policy_data.get(field) is False
            for field in policy_approval_fields
        )
        and all(
            evidence_data.get(field) is False
            for field in approval_fields
        )
    )

    checks.append(check(
        "approvals_embedding_and_auto_eligibility_disabled",
        all_approvals_disabled,
    ))

    # 6. 보고서 작성
    passed_count = sum(x["passed"] for x in checks)
    failed_checks = [
        x["check"] for x in checks if not x["passed"]
    ]

    structural_passed = len(failed_checks) == 0

    report = {
        "country": "USA",
        "team_reference_program_id": EXPECTED_PROGRAM_ID,
        "program_name": policy_data["program_name"],
        "report_date": date.today().isoformat(),
        "validation_status": (
            "structural_pass_semantic_review_pending"
            if structural_passed
            else "structural_validation_failed"
        ),
        "structural_validation_passed": structural_passed,
        "semantic_validation_approved": False,
        "legal_validation_approved": False,
        "summary": {
            "official_source_count": len(sources),
            "policy_count": len(policies),
            "evidence_count": len(records),
            "covered_policy_count": len(
                set(evidence_policy_ids)
            ),
            "missing_search_count": len(missing),
            "total_checks": len(checks),
            "passed_checks": passed_count,
            "failed_checks": failed_checks,
            "meaning_of_structural_pass": (
                "Checks data integrity, literal excerpts, "
                "source hashes and review flags only. "
                "Does not verify whether the excerpt "
                "semantically supports the legal claim."
            ),
        },
        "checks": checks,
        "source_hash_results": source_hash_results,
        "mismatch_details": mismatches,
        "pending_review_items": policy_data.get(
            "pending_review_items", []
        ),
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== O VISA DATASET VALIDATION ===")
    print("Official sources:", len(sources))
    print("Policies:", len(policies))
    print("Evidence:", len(records))
    print("Covered policies:", len(set(evidence_policy_ids)))
    print("Missing searches:", len(missing))
    print(f"Structural checks: {passed_count}/{len(checks)} PASS")
    print("Structural validation passed:", structural_passed)
    print("Semantic validation approved:", False)
    print("Legal validation approved:", False)
    print("Pending review items:", len(report["pending_review_items"]))
    print("Report:", REPORT_PATH)

    if failed_checks:
        print("[FAIL] Structural validation issues:")
        for name in failed_checks:
            print(" -", name)
    else:
        print("[PASS] O visa structural validation complete")
        print("[INFO] Semantic and legal review remains pending")


if __name__ == "__main__":
    main()