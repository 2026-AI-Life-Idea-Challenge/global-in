
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(
    "data/processed/usa/employment/"
    "h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_review_packet_2026_draft.json"

OUTPUT_JSON = BASE / "h1b_structured_policies_2026_draft.json"

OUTPUT_CSV = BASE / "h1b_policy_human_review_2026_draft.csv"

SENSITIVE_SOURCES = {
    "USCIS-H1B-2025-MEMO",
    "DOS-H1B-2025-RESTRICTION",
    "H1B-PROCLAMATION-2026",
    "DHS-H1B-BIOMETRIC-FEE-2026",
}

TOPIC_LABELS = {
    "eligibility": "신청 자격",
    "employer_requirements": "고용주 요건",
    "registration_selection": "등록 및 선정",
    "petition_process": "청원 절차",
    "fees": "수수료",
    "stay_extension": "체류 및 연장",
    "family": "가족 및 H-4",
    "restrictions_screening": "입국 제한 및 심사",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def legal_flags(item):
    flags = set(item.get("review_flags", []))
    text = item["evidence_excerpt"]
    source_id = item["source_id"]

    if source_id in SENSITIVE_SOURCES:
        flags.add("time_sensitive_legal_review")

    if re.search(
        r"\$100,000|100,000 payment|"
        r"vacated|stay pending appeal",
        text,
        re.IGNORECASE,
    ):
        flags.add("payment_or_court_order_review")

    if source_id == "USCIS-AFM-CH31":
        flags.add("historical_guidance")

    return sorted(flags)


def main():
    for path in (OUTPUT_JSON, OUTPUT_CSV):
        if path.exists():
            raise FileExistsError(
                f"Refusing to overwrite: {path}"
            )

    packet = read_json(INPUT)
    items = packet["review_items"]

    if len(items) != packet["review_item_count"]:
        raise ValueError("Review packet count mismatch")

    if packet["validation_status"] != "needs_review":
        raise ValueError("Unexpected input review status")

    policies = []
    seen_ids = set()
    seen_evidence = set()

    for item in items:
        candidate_id = item["candidate_id"]

        if candidate_id in seen_ids:
            raise ValueError(
                f"Duplicate candidate: {candidate_id}"
            )

        if sha256(item["evidence_excerpt"]) != item["excerpt_sha256"]:
            raise ValueError(
                f"Evidence hash mismatch: {candidate_id}"
            )

        if item["excerpt_sha256"] in seen_evidence:
            raise ValueError(
                f"Duplicate evidence: {candidate_id}"
            )

        seen_ids.add(candidate_id)
        seen_evidence.add(item["excerpt_sha256"])

        topics = item["topic_candidates"]
        flags = legal_flags(item)

        policies.append({
            "policy_id": (
                f"US-WK-01-POL-{len(policies) + 1:04d}"
            ),
            "program_id": "US-WK-01",
            "program_name": "H-1B Specialty Occupation",
            "source_candidate_id": candidate_id,
            "review_item_id": item["review_item_id"],
            "topic_candidates": topics,
            "topic_labels_ko": [
                TOPIC_LABELS[t]
                for t in topics
                if t in TOPIC_LABELS
            ],
            "policy_statement_ko": None,
            "policy_statement_en": None,
            "applicability": None,
            "requirements": [],
            "exceptions": [],
            "effective_date": None,
            "expiration_date": None,
            "legal_status": "unverified",
            "source_id": item["source_id"],
            "source_url": item["source_url"],
            "source_sha256": item["source_sha256"],
            "source_page": item["source_page"],
            "source_paragraph_index": (
                item["source_paragraph_index"]
            ),
            "evidence_excerpt": item["evidence_excerpt"],
            "excerpt_sha256": item["excerpt_sha256"],
            "review_queue": item["original_review_queue"],
            "review_flags": flags,
            "human_review_decision": None,
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        })

    result = {
        "country": "USA",
        "program_id": "US-WK-01",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_type": "structured_policy_review_draft",
        "sampling_scope": (
            "111 representative items from 1537 source excerpts; "
            "not exhaustive policy coverage"
        ),
        "record_count": len(policies),
        "policy_records": policies,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    # A CSV worksheet for manual semantic/legal review.
    fields = [
        "policy_id",
        "source_id",
        "topics",
        "review_queue",
        "review_flags",
        "source_url",
        "source_page",
        "source_paragraph_index",
        "evidence_excerpt",
        "policy_statement_ko",
        "applicability",
        "requirements",
        "exceptions",
        "effective_date",
        "expiration_date",
        "legal_status",
        "human_review_decision",
    ]

    # Validate all records before saving.
    if len(policies) != 111:
        raise ValueError("Unexpected structured draft count")

    if any(
        record["policy_statement_ko"] is not None
        or record["legal_status"] != "unverified"
        or record["review_status"] != "needs_review"
        or record["semantic_support_verified"]
        or record["legal_effect_verified"]
        for record in policies
    ):
        raise ValueError("Unsafe draft state")

    with OUTPUT_JSON.open("x", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    with OUTPUT_CSV.open(
        "x",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()

        for record in policies:
            writer.writerow({
                "policy_id": record["policy_id"],
                "source_id": record["source_id"],
                "topics": " | ".join(
                    record["topic_candidates"]
                ),
                "review_queue": record["review_queue"],
                "review_flags": " | ".join(
                    record["review_flags"]
                ),
                "source_url": record["source_url"],
                "source_page": record["source_page"],
                "source_paragraph_index": (
                    record["source_paragraph_index"]
                ),
                "evidence_excerpt": (
                    record["evidence_excerpt"]
                ),
                "policy_statement_ko": "",
                "applicability": "",
                "requirements": "",
                "exceptions": "",
                "effective_date": "",
                "expiration_date": "",
                "legal_status": "unverified",
                "human_review_decision": "",
            })

    # Reopen both files to verify serialization.
    saved = read_json(OUTPUT_JSON)

    with OUTPUT_CSV.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        csv_rows = list(csv.DictReader(f))

    assert len(saved["policy_records"]) == 111
    assert len(csv_rows) == 111
    assert len({
        r["policy_id"] for r in csv_rows
    }) == 111
    assert all(
        a["policy_id"] == b["policy_id"]
        and a["evidence_excerpt"] == b["evidence_excerpt"]
        for a, b in zip(saved["policy_records"], csv_rows)
    )
    assert saved["approved_for_user_answers"] is False
    assert saved["approved_for_embedding"] is False
    assert saved["automatic_eligibility_rules_enabled"] is False
    assert saved["embedding_generated"] is False

    flag_counts = Counter(
        flag
        for record in policies
        for flag in record["review_flags"]
    )

    topic_counts = Counter(
        topic
        for record in policies
        for topic in record["topic_candidates"]
    )

    print("\n=== H-1B STRUCTURED POLICY DRAFT ===")
    print("STRUCTURED RECORDS:", len(policies))
    print("CSV REVIEW ROWS:", len(csv_rows))
    print("UNIQUE POLICY IDS:", len({
        r["policy_id"] for r in policies
    }))
    print("EVIDENCE HASHES: PASS")
    print("JSON-CSV CONSISTENCY: PASS")

    print("\n=== TOPIC COVERAGE ===")
    for topic in TOPIC_LABELS:
        print(topic, ":", topic_counts[topic])

    print("\n=== REVIEW FLAGS ===")
    for flag, count in sorted(flag_counts.items()):
        print(flag, ":", count)

    print("\n=== SAFETY ===")
    print("VERIFIED POLICIES:", 0)
    print("LEGAL STATUS: unverified")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("AUTO ELIGIBILITY: False")
    print("VALIDATION:", saved["validation_status"])

    print("\nJSON:", OUTPUT_JSON)
    print("CSV:", OUTPUT_CSV)


if __name__ == "__main__":
    main()