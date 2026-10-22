
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("data/processed/usa/employment/h1b_specialty_occupation")
BATCH = BASE / "h1b_remaining_batch_review_2026_draft.json"
POLICIES = BASE / "h1b_policy_consolidation_2026_cap_gap_draft.json"
OUTPUT = BASE / "h1b_final_review_packet_2026_draft.json"

TOPICS = {
    "specialty_occupation": [
        r"specialty occupation", r"degree", r"directly related",
        r"bachelor", r"equivalent", r"normally",
    ],
    "registration_weighted_selection": [
        r"registration", r"registrant", r"OEWS",
        r"weighted selection", r"wage level",
    ],
    "lca_wage_employer": [
        r"labor condition application", r"\bLCA\b",
        r"prevailing wage", r"required wage", r"employer",
    ],
    "status_portability_family": [
        r"portability", r"\bH-4\b", r"dependent",
        r"extension of stay", r"recapture", r"cap-gap",
    ],
    "fees_biometrics": [
        r"biometric fee", r"9-11", r"covered employer",
        r"fraud fee", r"filing fee",
    ],
    "entry_restrictions": [
        r"proclamation", r"\$100,000", r"restriction on entry",
        r"national interest", r"visa application",
    ],
    "enforcement": [
        r"revocation", r"debarment", r"violation",
        r"penalt", r"false attestation",
    ],
}

LEGAL_SOURCES = {
    "DHS-H1B-BIOMETRIC-FEE-2026",
    "DOS-H1B-2025-RESTRICTION",
    "H1B-PROCLAMATION-2026",
}

def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def main():
    batch = load(BATCH)
    consolidated = load(POLICIES)

    rows = batch["review_records"]
    if len(rows) != 1352:
        raise ValueError("잔여 원문 수 불일치")

    patterns = {
        topic: [re.compile(p, re.I) for p in items]
        for topic, items in TOPICS.items()
    }

    policies = [
        r
        for v in consolidated.values()
        if isinstance(v, list)
        for r in v
        if isinstance(r, dict) and r.get("policy_id")
    ]

    policy_groups = defaultdict(list)
    for policy in policies:
        text = str(policy.get("policy_statement_ko", ""))
        if text:
            policy_groups[policy.get("source_id", "unknown")].append({
                "policy_id": policy["policy_id"],
                "statement": text,
            })

    groups = defaultdict(list)
    topics_count = Counter()
    unmapped = []

    for row in rows:
        text = row["evidence_excerpt"]
        matches = [
            topic
            for topic, ps in patterns.items()
            if any(p.search(text) for p in ps)
        ]

        item = {
            "candidate_id": row["candidate_id"],
            "source_id": row["source_id"],
            "priority_tier": row["priority_tier"],
            "priority_score": row["priority_score"],
            "review_track": row["review_track"],
            "matched_topics": matches,
            "excerpt_sha256": row["excerpt_sha256"],
            "excerpt_preview": text[:700],
            "legal_effect_verified": False,
            "semantic_support_verified": False,
            "review_status": "needs_review",
        }

        if not matches:
            unmapped.append(item)
        else:
            for topic in matches:
                topics_count[topic] += 1
                groups[topic].append(item)

    review_groups = {}

    for topic, items in groups.items():
        ordered = sorted(
            items,
            key=lambda r: (
                0 if r["source_id"] in LEGAL_SOURCES else 1,
                {"high": 0, "legal_review": 1,
                 "medium": 2, "low": 3}.get(
                     r["priority_tier"], 4
                 ),
                -r["priority_score"],
                r["candidate_id"],
            ),
        )

        source_ids = {r["source_id"] for r in ordered}
        review_groups[topic] = {
            "candidate_count": len(ordered),
            "source_counts": dict(Counter(
                r["source_id"] for r in ordered
            )),
            "related_policy_records_same_source": [
                policy
                for source_id in sorted(source_ids)
                for policy in policy_groups.get(source_id, [])
            ],
            "priority_samples": ordered[:12],
            "all_candidate_ids": [
                r["candidate_id"] for r in ordered
            ],
            "decision": "needs_human_review",
        }

    report = {
        "program_id": "US-WK-01",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_files": [BATCH.name, POLICIES.name],
        "method": "topic_keyword_routing_not_legal_validation",
        "total_reviewed_candidate_ids": len(rows),
        "existing_policy_id_records": len(policies),
        "topic_counts_overlapping": dict(topics_count),
        "topic_groups": review_groups,
        "unmapped_candidate_count": len(unmapped),
        "unmapped_candidate_ids": [
            r["candidate_id"] for r in unmapped
        ],
        "unmapped_priority_samples": sorted(
            unmapped,
            key=lambda r: (
                {"high": 0, "legal_review": 1,
                 "medium": 2, "low": 3}.get(
                     r["priority_tier"], 4
                 ),
                -r["priority_score"],
            ),
        )[:15],
        "critical_legal_review_required": [
            "2026 biometric fee applicability and effective date",
            "H-1B entry restriction and proclamation applicability",
            "weighted selection effective date and transition",
            "current validity of legacy AFM guidance",
        ],
        "completeness_verified": False,
        "legal_effect_verified": False,
        "automatic_exclusion_performed": False,
        "new_policies_auto_approved": False,
        "review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
    }

    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    saved = load(OUTPUT)
    if saved["total_reviewed_candidate_ids"] != 1352:
        raise ValueError("저장 검증 실패")

    print("=== H-1B FINAL REVIEW PACKET ===")
    print("REVIEWED CANDIDATES:", len(rows))
    print("POLICY-ID RECORDS:", len(policies))
    print("TOPICS:", len(review_groups))
    print("TOPIC COUNTS (OVERLAPPING):")
    for topic, count in sorted(topics_count.items()):
        print(" ", topic, ":", count)
    print("UNMAPPED:", len(unmapped))
    print("LEGAL EFFECT VERIFIED: False")
    print("COMPLETENESS VERIFIED: False")
    print("APPROVED FOR ANSWERS: False")
    print("SAVED:", OUTPUT)
    print("=== END ===")

if __name__ == "__main__":
    main()