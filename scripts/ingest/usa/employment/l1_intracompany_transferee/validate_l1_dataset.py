
import hashlib
import json
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from scripts.ingest.usa.shared.evidence.build_e2_policy_evidence import (
    extract_text,
)


ROOT = Path(
    "data/processed/usa/employment/l1_intracompany_transferee"
)

POLICY_PATH = ROOT / "l1_policy_review_2026_draft.json"
EVIDENCE_PATH = ROOT / "l1_policy_evidence_2026_draft.json"
REPORT_PATH = ROOT / "l1_validation_report_2026_draft.json"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    return " ".join(text.split())


def main():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    sources = policy["official_sources"]
    policies = policy["policy_records"]
    records = evidence["evidence_records"]

    source_by_id = {s["source_id"]: s for s in sources}
    policy_by_id = {p["policy_id"]: p for p in policies}

    checks = {}

    # 1. 기본 구조
    checks["source_count"] = (
        len(sources) == len(source_by_id) == 8
    )
    checks["policy_count"] = (
        len(policies) == len(policy_by_id) == 26
    )
    checks["evidence_count"] = (
        len(records) == 30
        and evidence["evidence_count"] == 30
    )

    checks["program_identity"] = (
        policy["team_reference_program_id"] == "US-WK-03"
        and policy["internal_program_id"] is None
    )

    # 2. 공식 원본 검증
    source_texts = {}
    source_hash_results = {}

    for source_id, source in source_by_id.items():
        path = Path(source["local_path"])
        raw = path.read_bytes()

        hash_ok = sha256(raw) == source["sha256"]
        source_hash_results[source_id] = hash_ok

        if path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            texts = [
                normalize(page.extract_text() or "")
                for page in reader.pages
            ]
        else:
            texts = [normalize(extract_text(raw))]

        source_texts[source_id] = texts

    checks["official_source_hashes"] = all(
        source_hash_results.values()
    )

    # 3. 정책과 출처 연결
    checks["policy_source_links"] = all(
        bool(p["source_ids"])
        and set(p["source_ids"]).issubset(source_by_id)
        for p in policies
    )

    # 4. Evidence와 공식 원문 연결
    evidence_ids = [r["evidence_id"] for r in records]

    checks["unique_evidence_ids"] = (
        len(evidence_ids) == len(set(evidence_ids))
    )

    excerpt_hash_ok = True
    source_match_ok = True
    policy_link_ok = True
    page_match_ok = True

    mismatch_details = []

    for record in records:
        evidence_id = record["evidence_id"]
        policy_id = record["policy_id"]
        source_id = record["source_id"]

        if (
            policy_id not in policy_by_id
            or source_id not in source_by_id
            or source_id not in policy_by_id[policy_id]["source_ids"]
        ):
            policy_link_ok = False
            mismatch_details.append(
                {"evidence_id": evidence_id, "issue": "invalid_link"}
            )
            continue

        source = source_by_id[source_id]

        if (
            record["source_sha256"] != source["sha256"]
            or record["source_path"] != source["local_path"]
        ):
            source_match_ok = False
            mismatch_details.append(
                {"evidence_id": evidence_id, "issue": "source_metadata"}
            )

        excerpt = record["evidence_excerpt"]

        if sha256(excerpt.encode("utf-8")) != record["excerpt_sha256"]:
            excerpt_hash_ok = False
            mismatch_details.append(
                {"evidence_id": evidence_id, "issue": "excerpt_hash"}
            )

        texts = source_texts[source_id]
        page = record["source_page"]

        if page is None:
            correct_page = len(texts) == 1
            text_index = 0
        else:
            correct_page = (
                isinstance(page, int)
                and not isinstance(page, bool)
                and 1 <= page <= len(texts)
                and source["local_path"].lower().endswith(".pdf")
            )
            text_index = page - 1 if correct_page else None

        if not correct_page:
            page_match_ok = False
            source_match_ok = False
            mismatch_details.append(
                {"evidence_id": evidence_id, "issue": "invalid_page"}
            )
        elif excerpt not in texts[text_index]:
            source_match_ok = False
            mismatch_details.append(
                {"evidence_id": evidence_id, "issue": "excerpt_not_in_source"}
            )

    checks["evidence_policy_links"] = policy_link_ok
    checks["excerpt_sha256"] = excerpt_hash_ok
    checks["evidence_source_matches"] = source_match_ok
    checks["pdf_page_references"] = page_match_ok

    covered = {r["policy_id"] for r in records}

    checks["all_policies_covered"] = (
        covered == set(policy_by_id)
        and evidence["covered_policy_count"] == 26
        and evidence["missing_search_count"] == 0
    )

    # 5. 미승인 안전 설정
    checks["review_flags"] = (
        policy["validation_status"] == "needs_review"
        and evidence["validation_status"] == "needs_review"
        and all(p["review_status"] == "needs_review" for p in policies)
        and all(
            r["review_status"] == "needs_review"
            and r["semantic_support_verified"] is False
            for r in records
        )
    )

    checks["approval_and_embedding_disabled"] = (
        all(
            policy[key] is False
            for key in [
                "approved_for_user_answers",
                "approved_for_embedding",
                "automatic_eligibility_rules_enabled",
                "embedding_generated",
            ]
        )
        and all(
            evidence[key] is False
            for key in [
                "approved_for_user_answers",
                "approved_for_embedding",
                "embedding_generated",
            ]
        )
    )

    # 6. 최종 리포트
    all_pass = all(checks.values())

    pending_items = list(
        dict.fromkeys(
            policy.get("pending_review_items", [])
            + [
                "final_semantic_and_legal_review",
                "current_uscis_and_dos_fee_reverification",
                "l1_blanket_petition_eligibility_review",
                "south_korea_consular_procedure_review",
                "l1_source_currentness_review",
            ]
        )
    )

    report = {
        "country": "USA",
        "team_reference_program_id": "US-WK-03",
        "program_name": "L-1A/L-1B Intracompany Transferee",
        "report_date": date.today().isoformat(),
        "validation_status": "needs_review",
        "structural_validation_passed": all_pass,
        "semantic_validation_approved": False,
        "legal_validation_approved": False,
        "summary": {
            "official_sources": len(sources),
            "policy_records": len(policies),
            "evidence_records": len(records),
            "covered_policies": len(covered),
            "source_mismatches": len(mismatch_details),
        },
        "checks": checks,
        "source_hash_results": source_hash_results,
        "mismatch_details": mismatch_details,
        "pending_review_items": pending_items,
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== L-1 VALIDATION REPORT ===")
    print("Official sources:", len(sources))
    print("Policy records:", len(policies))
    print("Evidence records:", len(records))

    for name, passed in checks.items():
        print(
            "[PASS]" if passed else "[FAIL]",
            name,
        )

    print("Structural validation:", "PASS" if all_pass else "FAIL")
    print("Pending review items:", len(pending_items))
    print("Saved:", REPORT_PATH)

    if not all_pass:
        raise SystemExit("Validation failed; review the report.")

    print("[PASS] L-1 validation report generated")
    print("[INFO] Semantic and legal approval remains pending")


if __name__ == "__main__":
    main()