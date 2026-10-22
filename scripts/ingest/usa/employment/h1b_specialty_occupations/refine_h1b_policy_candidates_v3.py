
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .collect_h1b_sources import ROOT


INPUT = Path(
    "data/processed/usa/employment/"
    "h1b_specialty_occupation/"
    "h1b_policy_candidates_2026_v2_draft.json"
)

MANIFEST = (
    ROOT / "h1b_official_sources_2026_extended_draft.json"
)

OUTPUT = INPUT.parent / (
    "h1b_policy_candidates_2026_v3_refined_draft.json"
)

COMMENTARY_PATTERN = re.compile(
    r"\b("
    r"commenter|commenters|public comments|"
    r"response to comments|DHS response|"
    r"one commenter|several commenters|"
    r"some commenters"
    r")\b",
    re.I,
)

LICENSE_PATTERN = re.compile(
    r"\b("
    r"state license|state registration|"
    r"professional registration|"
    r"license, registration, or certification"
    r")\b",
    re.I,
)

REGISTRATION_CONTEXT = re.compile(
    r"\b("
    r"electronic registration|"
    r"registration process|"
    r"selected registration|"
    r"registration fee|registrant|"
    r"cap.subject|cap.exempt|"
    r"weighted selection|lottery|"
    r"registration period"
    r")\b",
    re.I,
)

DEPENDENT_EMPLOYER = re.compile(
    r"h-1b[\s-]+dependent employer",
    re.I,
)

FAMILY_CONTEXT = re.compile(
    r"\b("
    r"h-4|dependent spouse|dependent child|"
    r"spouse|spouses|children|"
    r"family member|family members"
    r")\b",
    re.I,
)

RULE_PATTERN = re.compile(
    r"\b("
    r"must|shall|required|requires|"
    r"may not|cannot|prohibited|"
    r"eligible|ineligible|exempt|"
    r"unless|except|subject to|"
    r"no later than|not permitted"
    r")\b",
    re.I,
)

HISTORICAL_SOURCE_IDS = {
    "USCIS-AFM-CH31",
}

LEGAL_REVIEW_SOURCE_IDS = {
    "DOS-H1B-2025-RESTRICTION",
    "USCIS-H1B-2025-MEMO",
    "H1B-PROCLAMATION-2026",
    "DHS-H1B-BIOMETRIC-FEE-2026",
    "DHS-H1B-WEIGHTED-2025",
    "DHS-H1B-MODERNIZATION-2024",
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def classify_record(record):
    text = record["evidence_excerpt"]
    topics = list(record["topic_candidates"])
    flags = set(record.get("review_flags", []))
    corrections = []

    if (
        "registration_selection" in topics
        and LICENSE_PATTERN.search(text)
        and not REGISTRATION_CONTEXT.search(text)
    ):
        topics.remove("registration_selection")
        corrections.append("license_registration_context")

    if (
        "family" in topics
        and DEPENDENT_EMPLOYER.search(text)
        and not FAMILY_CONTEXT.search(text)
    ):
        topics.remove("family")
        corrections.append("dependent_employer_context")

    if COMMENTARY_PATTERN.search(text):
        flags.add("commentary_suspected")

    if len(text) > 2400:
        flags.add("long_excerpt_review")

    if len(text) < 150:
        flags.add("short_excerpt_review")

    if record["source_id"] in HISTORICAL_SOURCE_IDS:
        flags.add("historical_guidance")

    if record["source_id"] in LEGAL_REVIEW_SOURCE_IDS:
        flags.add("legal_effect_review")

    if len(topics) >= 4:
        flags.add("multi_topic_review")

    if not topics:
        flags.add("no_topic_after_correction")

    rule_terms = sorted({
        match.group(0).lower()
        for match in RULE_PATTERN.finditer(text)
    })

    # This is only a review-routing heuristic.
    # It does not establish that text is a valid legal rule.
    if "no_topic_after_correction" in flags:
        queue = "context_review"

    elif "historical_guidance" in flags:
        queue = "historical_review"

    elif "commentary_suspected" in flags:
        queue = "commentary_review"

    elif "long_excerpt_review" in flags:
        queue = "segmentation_review"

    elif "short_excerpt_review" in flags:
        queue = "context_review"

    elif "multi_topic_review" in flags:
        queue = "multi_topic_review"

    elif rule_terms:
        queue = "priority_policy_review"

    else:
        queue = "general_review"

    return {
        **record,
        "topic_candidates_v3": topics,
        "topic_corrections": corrections,
        "review_flags_v3": sorted(flags),
        "rule_language_indicators": rule_terms,
        "review_queue": queue,
        "policy_status": "unverified_candidate",
        "semantic_support_verified": False,
        "legal_effect_verified": False,
        "review_status": "needs_review",
    }


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    source_data = load_json(MANIFEST)
    original = load_json(INPUT)

    sources = source_data["official_sources"]
    records = original["candidate_records"]

    if len(sources) != 15 or len(records) != 1537:
        raise ValueError(
            "Unexpected source or candidate count"
        )

    source_map = {
        source["source_id"]: source
        for source in sources
    }

    if len(source_map) != len(sources):
        raise ValueError("Duplicate source IDs")

    for source in sources:
        path = Path(source["local_path"])

        if not path.is_file():
            raise FileNotFoundError(path)

        actual_hash = sha256_bytes(path.read_bytes())

        if actual_hash != source["sha256"]:
            raise ValueError(
                f"Source hash mismatch: {source['source_id']}"
            )

    refined = []
    seen_ids = set()
    seen_hashes = set()

    for record in records:
        cid = record["candidate_id"]
        sid = record["source_id"]
        text = record["evidence_excerpt"]

        if cid in seen_ids:
            raise ValueError(f"Duplicate candidate ID: {cid}")

        if sid not in source_map:
            raise ValueError(f"Unknown source: {sid}")

        source = source_map[sid]

        if record["source_sha256"] != source["sha256"]:
            raise ValueError(f"Source reference mismatch: {cid}")

        if record["source_path"] != source["local_path"]:
            raise ValueError(f"Source path mismatch: {cid}")

        excerpt_hash = sha256_bytes(text.encode("utf-8"))

        if excerpt_hash != record["excerpt_sha256"]:
            raise ValueError(f"Excerpt hash mismatch: {cid}")

        if excerpt_hash in seen_hashes:
            raise ValueError(f"Duplicate excerpt: {cid}")

        seen_ids.add(cid)
        seen_hashes.add(excerpt_hash)

        refined.append(classify_record(record))

    queue_counts = Counter(
        r["review_queue"] for r in refined
    )

    topic_counts = Counter(
        topic
        for r in refined
        for topic in r["topic_candidates_v3"]
    )

    flag_counts = Counter(
        flag
        for r in refined
        for flag in r["review_flags_v3"]
    )

    corrections = Counter(
        correction
        for r in refined
        for correction in r["topic_corrections"]
    )

    # All records must remain unapproved and unverified.
    if any(
        r["semantic_support_verified"]
        or r["legal_effect_verified"]
        or r["review_status"] != "needs_review"
        for r in refined
    ):
        raise ValueError("Unsafe candidate review state")

    if len(refined) != len(records):
        raise ValueError("Candidate preservation failed")

    result = {
        "country": "USA",
        "team_reference_program_id": "US-WK-01",
        "program_name": "H-1B Specialty Occupation",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_count": len(sources),
        "original_candidate_count": len(records),
        "refined_candidate_count": len(refined),
        "candidate_preservation_verified": True,
        "excerpt_hash_validation": "passed",
        "source_hash_validation": "passed",
        "review_queue_counts": dict(queue_counts),
        "topic_candidate_counts_v3": dict(topic_counts),
        "review_flag_counts": dict(flag_counts),
        "topic_correction_counts": dict(corrections),
        "candidate_records": refined,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # Read the saved file again to verify serialization.
    saved = load_json(OUTPUT)

    if (
        saved["refined_candidate_count"] != len(records)
        or len(saved["candidate_records"]) != len(records)
        or saved["validation_status"] != "needs_review"
    ):
        raise ValueError("Saved output validation failed")

    print("\n=== H-1B V3 INTEGRATED VALIDATION ===")
    print("SOURCES:", len(sources))
    print("ORIGINAL CANDIDATES:", len(records))
    print("PRESERVED CANDIDATES:", len(refined))
    print("SOURCE HASHES: PASS")
    print("EXCERPT HASHES: PASS")
    print("DUPLICATE IDS: 0")
    print("DUPLICATE EXCERPTS: 0")

    print("\n=== REVIEW QUEUES ===")
    for name, count in sorted(queue_counts.items()):
        print(name, ":", count)

    print("\n=== TOPIC DISTRIBUTION V3 ===")
    for name, count in sorted(topic_counts.items()):
        print(name, ":", count)

    print("\n=== TOPIC CORRECTIONS ===")
    for name, count in sorted(corrections.items()):
        print(name, ":", count)

    print("\n=== REVIEW FLAGS ===")
    for name, count in sorted(flag_counts.items()):
        print(name, ":", count)

    print("\n=== SAFETY ===")
    print("SEMANTIC VERIFIED:", 0)
    print("LEGAL VERIFIED:", 0)
    print("APPROVED FOR ANSWERS:", False)
    print("APPROVED FOR EMBEDDING:", False)
    print("AUTO ELIGIBILITY:", False)
    print("VALIDATION:", result["validation_status"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()