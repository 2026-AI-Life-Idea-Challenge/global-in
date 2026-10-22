
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .collect_h1b_sources import ROOT


BASE = Path(
    "data/processed/usa/employment/"
    "h1b_specialty_occupation"
)

INPUT = (
    BASE / "h1b_policy_candidates_2026_v3_refined_draft.json"
)

MANIFEST = (
    ROOT / "h1b_official_sources_2026_extended_draft.json"
)

OUTPUT = (
    BASE / "h1b_policy_review_packet_2026_draft.json"
)

TOPICS = [
    "eligibility",
    "employer_requirements",
    "registration_selection",
    "petition_process",
    "fees",
    "stay_extension",
    "family",
    "restrictions_screening",
]

PER_TOPIC = 12

QUEUE_PRIORITY = {
    "priority_policy_review": 0,
    "general_review": 1,
    "multi_topic_review": 2,
    "segmentation_review": 3,
    "context_review": 4,
    "commentary_review": 5,
    "historical_review": 6,
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(content):
    return hashlib.sha256(content).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT}"
        )

    manifest = load(MANIFEST)
    data = load(INPUT)

    sources = manifest["official_sources"]
    candidates = data["candidate_records"]

    if len(sources) != 15 or len(candidates) != 1537:
        raise ValueError("Unexpected input counts")

    source_map = {
        s["source_id"]: s for s in sources
    }

    if len(source_map) != 15:
        raise ValueError("Duplicate source IDs")

    for source in sources:
        path = Path(source["local_path"])

        if not path.is_file():
            raise FileNotFoundError(path)

        if digest(path.read_bytes()) != source["sha256"]:
            raise ValueError(
                "Source hash mismatch: "
                + source["source_id"]
            )

    candidate_ids = set()
    for record in candidates:
        cid = record["candidate_id"]
        sid = record["source_id"]

        if cid in candidate_ids:
            raise ValueError("Duplicate candidate ID")

        candidate_ids.add(cid)

        if sid not in source_map:
            raise ValueError(f"Unknown source: {sid}")

        source = source_map[sid]

        if record["source_sha256"] != source["sha256"]:
            raise ValueError(
                f"Source reference mismatch: {cid}"
            )

        if (
            digest(record["evidence_excerpt"].encode("utf-8"))
            != record["excerpt_sha256"]
        ):
            raise ValueError(
                f"Excerpt hash mismatch: {cid}"
            )

    selected = {}
    source_counts = Counter()

    def add(record, reason):
        cid = record["candidate_id"]

        if cid in selected:
            selected[cid]["selection_reasons"].append(reason)
            return

        source_id = record["source_id"]

        selected[cid] = {
            "review_item_id": None,
            "candidate_id": cid,
            "source_id": source_id,
            "source_url": source_map[source_id]["url"],
            "source_sha256": record["source_sha256"],
            "source_page": record["source_page"],
            "source_paragraph_index": (
                record["source_paragraph_index"]
            ),
            "topic_candidates": (
                record["topic_candidates_v3"]
            ),
            "evidence_excerpt": (
                record["evidence_excerpt"]
            ),
            "excerpt_sha256": (
                record["excerpt_sha256"]
            ),
            "original_review_queue": (
                record["review_queue"]
            ),
            "review_flags": (
                record["review_flags_v3"]
            ),
            "selection_reasons": [reason],
            "policy_statement": None,
            "applicability": None,
            "exceptions": None,
            "effective_date": None,
            "human_review_decision": None,
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        source_counts[source_id] += 1

    # Preserve at least one representative from each source.
    # Historical/context-only sources remain explicitly flagged.
    for source in sources:
        sid = source["source_id"]

        options = [
            r for r in candidates
            if r["source_id"] == sid
        ]

        if not options:
            raise ValueError(
                f"No candidates for source: {sid}"
            )

        options.sort(
            key=lambda r: (
                QUEUE_PRIORITY.get(
                    r["review_queue"], 99
                ),
                len(r["evidence_excerpt"]) > 2400,
                r["source_paragraph_index"],
            )
        )

        add(options[0], "source_coverage")

    # Add candidates by topic, balancing source coverage.
    for topic in TOPICS:
        options = [
            r for r in candidates
            if topic in r["topic_candidates_v3"]
        ]

        if not options:
            raise ValueError(
                f"No candidates for topic: {topic}"
            )

        topic_selected = 0

        while topic_selected < PER_TOPIC:
            remaining = [
                r for r in options
                if r["candidate_id"] not in selected
            ]

            if not remaining:
                break

            remaining.sort(
                key=lambda r: (
                    QUEUE_PRIORITY.get(
                        r["review_queue"], 99
                    ),
                    source_counts[r["source_id"]],
                    len(r["evidence_excerpt"]) > 2400,
                    len(r["topic_candidates_v3"]),
                    r["source_paragraph_index"],
                )
            )

            chosen = remaining[0]
            add(chosen, f"topic_coverage:{topic}")
            topic_selected += 1

    review_items = list(selected.values())

    for number, item in enumerate(review_items, 1):
        item["review_item_id"] = (
            f"H1B-REVIEW-{number:04d}"
        )

    selected_source_counts = Counter(
        x["source_id"] for x in review_items
    )

    selected_topic_counts = Counter(
        topic
        for item in review_items
        for topic in item["topic_candidates"]
    )

    selected_queue_counts = Counter(
        x["original_review_queue"]
        for x in review_items
    )

    if set(selected_source_counts) != set(source_map):
        raise ValueError("Incomplete source coverage")

    if not all(selected_topic_counts[t] > 0 for t in TOPICS):
        raise ValueError("Incomplete topic coverage")

    if any(
        item["semantic_support_verified"]
        or item["legal_effect_verified"]
        or item["review_status"] != "needs_review"
        for item in review_items
    ):
        raise ValueError("Unsafe review state")

    result = {
        "country": "USA",
        "program_id": "US-WK-01",
        "program_name": "H-1B Specialty Occupation",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_candidate_count": len(candidates),
        "official_source_count": len(sources),
        "review_item_count": len(review_items),
        "selection_strategy": (
            "source_coverage_then_balanced_topic_sampling"
        ),
        "review_item_source_counts": dict(
            selected_source_counts
        ),
        "review_item_topic_counts": dict(
            selected_topic_counts
        ),
        "review_item_queue_counts": dict(
            selected_queue_counts
        ),
        "sampling_warning": (
            "Representative review sample only; "
            "not exhaustive legal or policy coverage."
        ),
        "review_items": review_items,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # Verify the file after writing.
    saved = load(OUTPUT)

    assert saved["review_item_count"] == len(
        saved["review_items"]
    )

    assert len({
        x["candidate_id"]
        for x in saved["review_items"]
    }) == len(review_items)

    assert all(
        digest(x["evidence_excerpt"].encode("utf-8"))
        == x["excerpt_sha256"]
        for x in saved["review_items"]
    )

    assert saved["approved_for_user_answers"] is False
    assert saved["approved_for_embedding"] is False
    assert saved["automatic_eligibility_rules_enabled"] is False
    assert saved["embedding_generated"] is False

    print("\n=== H-1B REVIEW PACKET VALIDATION ===")
    print("ORIGINAL CANDIDATES:", len(candidates))
    print("REVIEW ITEMS:", len(review_items))
    print("SOURCES COVERED:", len(selected_source_counts))
    print("TOPICS COVERED:", len(selected_topic_counts))
    print("DUPLICATE IDS: 0")
    print("SOURCE HASHES: PASS")
    print("EXCERPT HASHES: PASS")

    print("\n=== REVIEW QUEUES ===")
    for name, count in sorted(
        selected_queue_counts.items()
    ):
        print(name, ":", count)

    print("\n=== TOPIC COVERAGE ===")
    for topic in TOPICS:
        print(topic, ":", selected_topic_counts[topic])

    print("\n=== SAFETY ===")
    print("SEMANTIC VERIFIED: 0")
    print("LEGAL VERIFIED: 0")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("VALIDATION:", saved["validation_status"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()