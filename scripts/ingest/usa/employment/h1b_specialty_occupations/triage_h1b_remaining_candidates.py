
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_consolidation_2026_registration_draft.json"
CANDIDATES = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_remaining_candidates_triage_2026_draft.json"

REVIEW_GROUPS = [
    "policy_records",
    "supplemental_stay_evidence",
    "additional_core_policy_drafts",
    "additional_supporting_evidence",
    "additional_legal_review_evidence",
    "additional_registration_policy_drafts",
    "registration_supporting_evidence",
    "registration_operational_information",
    "registration_context_review",
]

SOURCE_WEIGHTS = {
    "USCIS-H1B-OVERVIEW": 8,
    "USCIS-H1B-REGISTRATION": 8,
    "DOL-H1B-PROGRAM": 8,
    "DOL-H1B-LCA-LAW": 7,
    "DHS-H1B-MODERNIZATION-2024": 3,
    "DHS-H1B-WEIGHTED-2025": 3,
    "DHS-H1B-BIOMETRIC-FEE-2026": 5,
    "H1B-PROCLAMATION-2026": 5,
    "DOS-H1B-2025-RESTRICTION": 5,
    "DOS-H1B-H4-SCREENING-2025": 5,
    "DOS-TEMP-WORKER": 4,
    "USCIS-H1B-2025-MEMO": 4,
    "USCIS-AFM-CH31": 0,
    "DOS-EXPANDED-SCREENING-2026": 1,
}

RULE_PATTERNS = {
    "mandatory_language": (
        r"\bmust\b|\bshall\b|\brequired to\b|"
        r"\bmay not\b|\bprohibited\b"
    ),
    "eligibility": (
        r"\beligib(?:le|ility)\b|\bqualif(?:y|ies|ication)\b|"
        r"\bspecialty occupation\b"
    ),
    "filing": (
        r"\bform i-129\b|\bpetition(?:er|s)?\b|"
        r"\bregistration\b|\bapplication\b"
    ),
    "employment": (
        r"\bemployer\b|\bwage\b|\blabor condition\b|"
        r"\bprevailing wage\b"
    ),
    "stay": (
        r"\bextension\b|\bperiod of stay\b|"
        r"\bchange of status\b|\bportability\b"
    ),
    "family": (
        r"\bh-4\b|\bdependent spouse\b|"
        r"\bdependent children\b"
    ),
}

COMMENTARY_PATTERN = re.compile(
    r"\bdhs (?:believes|estimates|acknowledges|disagrees)\b|"
    r"\bcommenters? (?:stated|suggested|argued)\b|"
    r"\bregulatory impact analysis\b|"
    r"\bdiscount rate\b|\bnet cost savings\b|"
    r"\bnepa\b|\bpaperwork reduction act\b",
    re.IGNORECASE,
)

HIGH_RISK_PATTERN = re.compile(
    r"\$100,000|\b100,000 payment\b|"
    r"\bproclamation\b|\bcourt\b|\bvacat(?:ed|ur)\b|"
    r"\bstay pending appeal\b|"
    r"\b9-11 biometric fee\b|"
    r"\bbiometric entry-exit fee\b",
    re.IGNORECASE,
)

RULE_REGEX = {
    name: re.compile(pattern, re.IGNORECASE)
    for name, pattern in RULE_PATTERNS.items()
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify(candidate):
    text = candidate["evidence_excerpt"]
    source_id = candidate["source_id"]

    score = SOURCE_WEIGHTS.get(source_id, 2)
    matched = []

    for name, regex in RULE_REGEX.items():
        if regex.search(text):
            score += 2
            matched.append(name)

    is_commentary = bool(COMMENTARY_PATTERN.search(text))
    high_risk = bool(HIGH_RISK_PATTERN.search(text))

    if is_commentary:
        score -= 5

    if len(text.strip()) < 80:
        score -= 3

    if high_risk:
        tier = "legal_review"
    elif score >= 12:
        tier = "high"
    elif score >= 7:
        tier = "medium"
    else:
        tier = "low"

    return {
        "candidate_id": candidate["candidate_id"],
        "source_id": source_id,
        "source_paragraph_index": candidate["source_paragraph_index"],
        "excerpt_sha256": candidate["excerpt_sha256"],
        "excerpt_preview": text[:350],
        "priority_score": score,
        "priority_tier": tier,
        "matched_signals": matched,
        "commentary_signal": is_commentary,
        "legal_review_signal": high_risk,
        "semantic_support_verified": False,
        "legal_effect_verified": False,
        "review_status": "needs_review",
    }


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"덮어쓰기 금지: {OUTPUT}")

    source = load(CANDIDATES)
    consolidated = load(INPUT)

    candidates = source["candidate_records"]

    if len(candidates) != 1537:
        raise ValueError("원문 후보 수 불일치")

    candidate_ids = [c["candidate_id"] for c in candidates]

    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("원문 후보 ID 중복")

    used_ids = []

    for group in REVIEW_GROUPS:
        if group not in consolidated:
            raise ValueError(f"검토 그룹 누락: {group}")

        used_ids.extend(
            r["source_candidate_id"]
            for r in consolidated[group]
        )

    if len(set(used_ids)) != len(used_ids):
        raise ValueError("기존 검토 ID 중복")

    used = set(used_ids)

    if len(used) != 146:
        raise ValueError(
            f"기존 검토 대상 수 불일치: {len(used)}"
        )

    if not used.issubset(set(candidate_ids)):
        raise ValueError("원문 후보에 없는 검토 ID 발견")

    remaining = []

    for candidate in candidates:
        if candidate["candidate_id"] in used:
            continue

        if sha256(candidate["evidence_excerpt"]) != candidate["excerpt_sha256"]:
            raise ValueError(
                f"원문 해시 불일치: {candidate['candidate_id']}"
            )

        remaining.append(classify(candidate))

    if len(remaining) != 1391:
        raise ValueError(
            f"미검토 원문 수 불일치: {len(remaining)}"
        )

    tier_order = {
        "high": 0,
        "medium": 1,
        "legal_review": 2,
        "low": 3,
    }

    ranked = sorted(
        remaining,
        key=lambda x: (
            tier_order[x["priority_tier"]],
            -x["priority_score"],
            x["candidate_id"],
        ),
    )

    top_40 = [
        r for r in ranked
        if r["priority_tier"] == "high"
    ][:40]

    tier_counts = Counter(
        r["priority_tier"] for r in remaining
    )

    source_counts = Counter(
        r["source_id"] for r in remaining
    )

    source_tier_counts = defaultdict(Counter)

    for record in remaining:
        source_tier_counts[record["source_id"]][
            record["priority_tier"]
        ] += 1

    result = {
        "program_id": "US-WK-01",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_candidate_count": len(candidates),
        "previously_classified_count": len(used),
        "remaining_count": len(remaining),
        "triage_method": "heuristic_priority_only",
        "triage_tier_counts": dict(tier_counts),
        "source_counts": dict(source_counts),
        "source_tier_counts": {
            key: dict(value)
            for key, value in source_tier_counts.items()
        },
        "top_priority_candidates": top_40,
        "remaining_candidates": ranked,
        "automatic_exclusion_performed": False,
        "semantic_support_verified": False,
        "legal_effect_verified": False,
        "review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
    }

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    saved = load(OUTPUT)

    if (
        len(saved["remaining_candidates"]) != 1391
        or saved["previously_classified_count"] != 146
        or saved["automatic_exclusion_performed"] is not False
        or saved["approved_for_user_answers"] is not False
        or saved["approved_for_embedding"] is not False
    ):
        raise ValueError("결과 검증 실패")

    if sum(saved["triage_tier_counts"].values()) != 1391:
        raise ValueError("분류 집계 불일치")

    print("\n=== H-1B REMAINING CANDIDATES TRIAGE ===")
    print("TOTAL SOURCE CANDIDATES:", len(candidates))
    print("PREVIOUSLY CLASSIFIED:", len(used))
    print("REMAINING:", len(remaining))

    print("\n=== PRIORITY COUNTS ===")

    for tier in ("high", "medium", "legal_review", "low"):
        print(tier, ":", tier_counts[tier])

    print("\n=== SOURCE SUMMARY ===")

    for source_id, count in sorted(source_counts.items()):
        print(
            source_id,
            "| TOTAL:", count,
            "| HIGH:", source_tier_counts[source_id]["high"],
            "| LEGAL:", source_tier_counts[source_id]["legal_review"],
        )

    print("\n=== TOP PRIORITY 40 ===")

    for item in top_40:
        print(
            item["candidate_id"],
            "|", item["source_id"],
            "| SCORE:", item["priority_score"],
            "|", item["excerpt_preview"][:120].replace("\n", " "),
        )

    print("\n=== SAFETY ===")
    print("AUTO EXCLUSION: False")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()