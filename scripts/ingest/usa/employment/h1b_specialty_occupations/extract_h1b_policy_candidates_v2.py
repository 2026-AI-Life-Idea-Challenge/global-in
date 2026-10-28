
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .collect_h1b_sources import ROOT
from .extract_h1b_policy_candidates import (
    html_paragraphs,
    pdf_paragraphs,
)


MANIFEST = (
    ROOT / "h1b_official_sources_2026_extended_draft.json"
)

OUTPUT = Path(
    "data/processed/usa/employment/"
    "h1b_specialty_occupation/"
    "h1b_policy_candidates_2026_v2_draft.json"
)

# Match complete terms, not substrings inside unrelated words.
TOPICS = {
    "eligibility": [
        "specialty occupation",
        "specialty occupations",
        "bachelor",
        "degree",
        "equivalent experience",
        "qualifications",
        "directly related",
    ],
    "employer_requirements": [
        "employer",
        "petitioner",
        "labor condition application",
        "prevailing wage",
        "working conditions",
        "labor certification",
    ],
    "registration_selection": [
        "registration",
        "registrant",
        "selection",
        "lottery",
        "cap-subject",
        "cap-exempt",
        "weighted selection",
        "advanced degree exemption",
    ],
    "petition_process": [
        "form i-129",
        "petition",
        "filing",
        "approval",
        "consular notification",
        "change of status",
    ],
    "fees": [
        "fee",
        "fees",
        "payment",
        "$100,000",
        "biometric",
        "fee schedule",
    ],
    "stay_extension": [
        "period of stay",
        "extension of stay",
        "extend your stay",
        "extension",
        "extensions",
        "six years",
        "three years",
        "3 years",
        "6 years",
        "grace period",
    ],
    "family": [
        "h-4",
        "dependent",
        "dependents",
        "spouse",
        "children",
        "employment authorization",
    ],
    "restrictions_screening": [
        "proclamation",
        "restriction",
        "screening",
        "vetting",
        "entry",
        "vacated",
        "court order",
        "stay pending appeal",
    ],
}

HISTORICAL_SOURCES = {
    "USCIS-AFM-CH31",
}

LEGAL_REVIEW_SOURCES = {
    "DOS-H1B-2025-RESTRICTION",
    "USCIS-H1B-2025-MEMO",
    "H1B-PROCLAMATION-2026",
    "DHS-H1B-BIOMETRIC-FEE-2026",
    "DHS-H1B-WEIGHTED-2025",
    "DHS-H1B-MODERNIZATION-2024",
}


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def matching_terms(text, terms):
    found = []

    for term in terms:
        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(term)
            + r"(?![A-Za-z0-9])"
        )

        if re.search(pattern, text, flags=re.IGNORECASE):
            found.append(term)

    return found


def classify_all(text):
    result = {}

    for topic, terms in TOPICS.items():
        hits = matching_terms(text, terms)

        if hits:
            result[topic] = hits

    return result


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    manifest = json.loads(
        MANIFEST.read_text(encoding="utf-8-sig")
    )

    sources = manifest["official_sources"]

    if len(sources) != 15:
        raise ValueError(
            f"Expected 15 sources, got {len(sources)}"
        )

    records = []
    topic_counts = Counter()
    source_counts = {}
    short_skipped = Counter()
    long_paragraphs = Counter()

    for source in sources:
        sid = source["source_id"]
        path = Path(source["local_path"])

        if not path.is_file():
            raise FileNotFoundError(path)

        source_hash = sha256(path.read_bytes())

        if source_hash != source["sha256"]:
            raise ValueError(
                f"Source hash mismatch: {sid}"
            )

        if path.suffix.lower() == ".pdf":
            paragraphs = pdf_paragraphs(path)
        else:
            paragraphs = html_paragraphs(path)

        selected = 0
        seen = set()

        for index, (page, text) in enumerate(paragraphs):
            if len(text) < 100:
                short_skipped[sid] += 1
                continue

            labels = classify_all(text)

            if not labels:
                continue

            excerpt_hash = sha256(
                text.encode("utf-8")
            )

            if excerpt_hash in seen:
                continue

            seen.add(excerpt_hash)

            # All matched topics are retained.
            topics = list(labels.keys())

            # Descriptive ranking only.
            primary_topic = max(
                topics,
                key=lambda topic: (
                    len(labels[topic]),
                    -topics.index(topic),
                ),
            )

            flags = []

            if sid in HISTORICAL_SOURCES:
                flags.append("historical_guidance")

            if sid in LEGAL_REVIEW_SOURCES:
                flags.append("legal_effect_review")

            if len(text) > 2400:
                flags.append("long_excerpt_review")
                long_paragraphs[sid] += 1

            if len(text) < 150:
                flags.append("short_excerpt_review")

            records.append({
                "candidate_id": (
                    f"H1B-CAND-V2-{len(records) + 1:05d}"
                ),
                "source_id": sid,
                "source_path": path.as_posix(),
                "source_sha256": source_hash,
                "source_page": page,
                "source_paragraph_index": index,
                "topic_candidates": topics,
                "primary_topic_candidate": primary_topic,
                "matched_terms": labels,
                "evidence_excerpt": text,
                "excerpt_sha256": excerpt_hash,
                "extraction_method": (
                    "multi_label_keyword_paragraph"
                ),
                "review_flags": flags,
                "semantic_support_verified": False,
                "legal_effect_verified": False,
                "review_status": "needs_review",
            })

            topic_counts.update(topics)
            selected += 1

        source_counts[sid] = selected

        print(
            f"[PASS] {sid} | "
            f"PARAGRAPHS: {len(paragraphs)} | "
            f"SELECTED: {selected}"
        )

    stay_count = topic_counts["stay_extension"]

    if stay_count == 0:
        raise ValueError(
            "Stay/extension coverage is still missing"
        )

    result = {
        "country": "USA",
        "team_reference_program_id": "US-WK-01",
        "program_name": "H-1B Specialty Occupation",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_count": len(sources),
        "candidate_count": len(records),
        "candidate_type": "source_excerpt",
        "extraction_strategy": (
            "all_keyword_matched_paragraphs_multi_label"
        ),
        "source_candidate_counts": source_counts,
        "topic_candidate_counts": dict(topic_counts),
        "skipped_short_paragraphs": dict(short_skipped),
        "long_excerpt_counts": dict(long_paragraphs),
        "candidate_records": records,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    OUTPUT.parent.mkdir(
        parents=True, exist_ok=True
    )

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n=== H-1B POLICY CANDIDATES V2 ===")
    print("SOURCES:", len(sources))
    print("CANDIDATES:", len(records))
    print("TOPIC DISTRIBUTION:")

    for topic in TOPICS:
        print(
            f"  {topic}: {topic_counts[topic]}"
        )

    print(
        "LONG EXCERPTS:",
        sum(long_paragraphs.values()),
    )
    print("VALIDATION:", result["validation_status"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()