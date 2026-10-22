
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(
    "data/processed/usa/employment/"
    "h1b_specialty_occupation"
)

INPUT_JSON = BASE / "h1b_structured_policies_2026_draft.json"

INPUT_CSV = BASE / "h1b_policy_human_review_annotated_2026.csv"

OUTPUT = BASE / "h1b_structured_policies_2026_reviewed_draft.json"

VALID_DECISIONS = {
    "policy_draft_candidate",
    "context_required",
    "legal_effect_review",
    "duplicate_support",
    "exclude_from_core_policy",
}

REQUIRED_COLUMNS = {
    "policy_id",
    "source_id",
    "source_url",
    "evidence_excerpt",
    "policy_statement_ko",
    "applicability",
    "requirements",
    "exceptions",
    "effective_date",
    "expiration_date",
    "legal_status",
    "human_review_decision",
    "review_rationale_ko",
    "semantic_support_verified",
    "legal_effect_verified",
    "review_status",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f, delimiter="\t")

        if not REQUIRED_COLUMNS.issubset(
            set(reader.fieldnames or [])
        ):
            raise ValueError("Required CSV columns are missing")

        return list(reader)


def parse_list(value, field):
    value = value.strip()

    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{field} must be a JSON array"
        ) from exc

    if not isinstance(parsed, list) or not all(
        isinstance(item, str) for item in parsed
    ):
        raise ValueError(
            f"{field} must be an array of strings"
        )

    return parsed


def parse_date(value):
    value = value.strip()

    if not value:
        return None

    # Date fields must use YYYY-MM-DD.
    if (
        len(value) != 10
        or datetime.strptime(value, "%Y-%m-%d")
        .strftime("%Y-%m-%d") != value
    ):
        raise ValueError(f"Invalid ISO date: {value}")

    return value


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    original = load_json(INPUT_JSON)
    csv_rows = read_csv(INPUT_CSV)

    policies = original["policy_records"]

    if len(policies) != 111 or len(csv_rows) != 111:
        raise ValueError("Expected exactly 111 records")

    if original["validation_status"] != "needs_review":
        raise ValueError("Unexpected original review status")

    policy_map = {
        item["policy_id"]: item
        for item in policies
    }

    csv_map = {
        row["policy_id"]: row
        for row in csv_rows
    }

    if (
        len(policy_map) != 111
        or len(csv_map) != 111
        or set(policy_map) != set(csv_map)
    ):
        raise ValueError(
            "Missing or duplicate policy IDs"
        )

    merged = []

    for policy in policies:
        pid = policy["policy_id"]
        row = csv_map[pid]

        if row["source_id"] != policy["source_id"]:
            raise ValueError(f"Source ID mismatch: {pid}")

        if row["source_url"] != policy["source_url"]:
            raise ValueError(f"Source URL mismatch: {pid}")

        if row["evidence_excerpt"] != policy["evidence_excerpt"]:
            raise ValueError(f"Evidence changed: {pid}")

        if digest(row["evidence_excerpt"]) != policy["excerpt_sha256"]:
            raise ValueError(f"Evidence hash mismatch: {pid}")

        decision = row["human_review_decision"].strip()

        if decision not in VALID_DECISIONS:
            raise ValueError(
                f"Invalid review decision: {pid}"
            )

        if row["legal_status"].strip() != "unverified":
            raise ValueError(
                f"Unexpected legal status: {pid}"
            )

        if (
            row["semantic_support_verified"].strip().lower()
            != "false"
            or row["legal_effect_verified"].strip().lower()
            != "false"
            or row["review_status"].strip()
            != "needs_review"
        ):
            raise ValueError(
                f"Unsafe CSV review state: {pid}"
            )

        statement = (
            row["policy_statement_ko"].strip()
            or None
        )

        rationale = (
            row["review_rationale_ko"].strip()
            or None
        )

        if not rationale:
            raise ValueError(
                f"Missing review rationale: {pid}"
            )

        updated = {
            **policy,
            "policy_statement_ko": statement,
            "applicability": (
                row["applicability"].strip() or None
            ),
            "requirements": parse_list(
                row["requirements"], "requirements"
            ),
            "exceptions": parse_list(
                row["exceptions"], "exceptions"
            ),
            "effective_date": parse_date(
                row["effective_date"]
            ),
            "expiration_date": parse_date(
                row["expiration_date"]
            ),
            "legal_status": "unverified",
            "human_review_decision": decision,
            "review_rationale_ko": rationale,
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        merged.append(updated)

    counts = Counter(
        item["human_review_decision"]
        for item in merged
    )

    result = {
        **original,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_type": "human_review_merged_policy_draft",
        "record_count": len(merged),
        "human_review_merge_completed": True,
        "human_review_decision_counts": dict(counts),
        "policy_records": merged,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    saved = load_json(OUTPUT)
    saved_records = saved["policy_records"]

    if len(saved_records) != 111:
        raise ValueError("Saved record count mismatch")

    for old, new in zip(policies, saved_records):
        if (
            old["policy_id"] != new["policy_id"]
            or old["source_sha256"] != new["source_sha256"]
            or old["excerpt_sha256"] != new["excerpt_sha256"]
            or old["evidence_excerpt"] != new["evidence_excerpt"]
            or digest(new["evidence_excerpt"])
            != new["excerpt_sha256"]
        ):
            raise ValueError("Saved evidence integrity failure")

    if any(
        p["semantic_support_verified"]
        or p["legal_effect_verified"]
        or p["review_status"] != "needs_review"
        or p["legal_status"] != "unverified"
        for p in saved_records
    ):
        raise ValueError("Unsafe saved review state")

    if any(
        saved[field] is not False
        for field in (
            "approved_for_user_answers",
            "approved_for_embedding",
            "automatic_eligibility_rules_enabled",
            "embedding_generated",
        )
    ):
        raise ValueError("Unsafe approval state")

    print("\n=== H-1B HUMAN REVIEW MERGE ===")
    print("ORIGINAL RECORDS:", len(policies))
    print("CSV RECORDS:", len(csv_rows))
    print("MERGED RECORDS:", len(saved_records))
    print("POLICY ID MATCH: PASS")
    print("SOURCE MATCH: PASS")
    print("EVIDENCE INTEGRITY: PASS")

    print("\n=== HUMAN REVIEW DECISIONS ===")
    for decision, count in sorted(counts.items()):
        print(decision, ":", count)

    print("\n=== KOREAN STATEMENTS ===")
    print(
        "POPULATED:",
        sum(bool(p["policy_statement_ko"]) for p in saved_records)
    )
    print(
        "EMPTY:",
        sum(not p["policy_statement_ko"] for p in saved_records)
    )

    print("\n=== SAFETY ===")
    print("VERIFIED POLICIES: 0")
    print("LEGAL STATUS: unverified")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("AUTO ELIGIBILITY: False")
    print("VALIDATION:", saved["validation_status"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()