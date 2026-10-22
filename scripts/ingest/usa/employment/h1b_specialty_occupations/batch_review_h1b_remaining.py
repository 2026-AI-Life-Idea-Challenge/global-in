
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

CONSOLIDATED = BASE / (
    "h1b_policy_consolidation_2026_cap_gap_draft.json"
)
CANDIDATES = BASE / "h1b_policy_candidates_2026_v2_draft.json"
TRIAGE = BASE / "h1b_remaining_candidates_triage_2026_draft.json"
OUTPUT = BASE / "h1b_remaining_batch_review_2026_draft.json"

TIER_ORDER = {
    "high": 0,
    "legal_review": 1,
    "medium": 2,
    "low": 3,
}

SIGNALS = {
    "eligibility_or_obligation": [
        r"\bmust\b",
        r"\brequired\b",
        r"\bshall\b",
        r"\bmay not\b",
        r"\beligib",
        r"\bqualif",
        r"\bprohibit",
    ],
    "filing_or_registration": [
        r"\bfile\b",
        r"\bfiling\b",
        r"\bpetition",
        r"\bregistr",
        r"\bform i-129\b",
        r"\blca\b",
    ],
    "employment_or_status": [
        r"\bemploy",
        r"\bauthoriz",
        r"\bstatus\b",
        r"\bportability\b",
        r"\bwage",
    ],
    "effective_date_or_transition": [
        r"\beffective date\b",
        r"\beffective on\b",
        r"\bimplementation date\b",
        r"\btransition",
        r"\bexpiration\b",
    ],
    "proposal_or_commentary": [
        r"\bproposed rule\b",
        r"\bproposes to\b",
        r"\bcommenter",
        r"\bpublic comment",
        r"\bnprm\b",
    ],
    "administrative_or_statistical": [
        r"\binformation collection\b",
        r"\bpaperwork reduction\b",
        r"\bannual burden\b",
        r"\brespondents\b",
        r"\btable \d+\b",
    ],
    "sanction_or_enforcement": [
        r"\bpenalt",
        r"\brevoke\b",
        r"\brevocation\b",
        r"\bviolation\b",
        r"\bdebar",
        r"\bfalse attest",
    ],
}

COMPILED = {
    name: [re.compile(p, re.IGNORECASE) for p in patterns]
    for name, patterns in SIGNALS.items()
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def policy_records(document):
    for group, value in document.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("policy_id"):
                    yield group, item


def scan_signals(text):
    return [
        name
        for name, patterns in COMPILED.items()
        if any(p.search(text) for p in patterns)
    ]


def review_track(tier, signals):
    if tier == "legal_review":
        return "legal_effect_review"

    if tier == "high":
        return "priority_policy_comparison"

    if (
        "effective_date_or_transition" in signals
        or "proposal_or_commentary" in signals
    ):
        return "legal_effect_review"

    if (
        "eligibility_or_obligation" in signals
        or "sanction_or_enforcement" in signals
    ):
        return "potential_policy_comparison"

    if "administrative_or_statistical" in signals:
        return "administrative_context_review"

    return "context_or_duplicate_review"


def main():
    consolidated = read_json(CONSOLIDATED)
    source = read_json(CANDIDATES)
    triage = read_json(TRIAGE)

    candidates = source["candidate_records"]
    candidate_index = {
        r["candidate_id"]: r for r in candidates
    }

    if len(candidate_index) != len(candidates):
        raise ValueError("후보 ID가 중복되었습니다.")

    existing = list(policy_records(consolidated))

    # 정책 초안뿐 아니라 검토·분류 기록도 포함
    used_ids = {
        r["source_candidate_id"]
        for value in consolidated.values()
        if isinstance(value, list)
        for r in value
        if isinstance(r, dict)
        and str(r.get("source_candidate_id", "")).startswith(
            "H1B-CAND-V2-"
        )
    }

    if len(used_ids) != 185:
        raise ValueError(
            f"기존 분류 원문 수 불일치: {len(used_ids)}"
        )

    remaining_ids = set(candidate_index) - used_ids
    triage_index = {
        r["candidate_id"]: r
        for r in triage["remaining_candidates"]
    }

    if len(remaining_ids) != 1352:
        raise ValueError(
            f"최신 잔여 원문 수가 예상과 다릅니다: "
            f"{len(remaining_ids)}"
        )

    if not remaining_ids.issubset(triage_index):
        missing = remaining_ids - set(triage_index)
        raise ValueError(
            f"기존 분류에 없는 원문이 있습니다: {len(missing)}"
        )

    by_evidence = defaultdict(list)

    for group, policy in existing:
        evidence_id = policy.get("source_candidate_id")
        if evidence_id:
            by_evidence[evidence_id].append({
                "policy_id": policy["policy_id"],
                "group": group,
            })

    results = []
    tiers = Counter()
    tracks = Counter()
    sources = Counter()
    by_source_track = Counter()
    invalid_hashes = []

    for candidate_id in sorted(remaining_ids):
        raw = candidate_index[candidate_id]
        tri = triage_index[candidate_id]
        excerpt = raw["evidence_excerpt"]

        if digest(excerpt) != raw["excerpt_sha256"]:
            invalid_hashes.append(candidate_id)
            continue

        if tri["excerpt_sha256"] != raw["excerpt_sha256"]:
            invalid_hashes.append(candidate_id)
            continue

        tier = tri["priority_tier"]
        signals = scan_signals(excerpt)
        track = review_track(tier, signals)

        tiers[tier] += 1
        tracks[track] += 1
        sources[raw["source_id"]] += 1
        by_source_track[(raw["source_id"], track)] += 1

        results.append({
            "candidate_id": candidate_id,
            "source_id": raw["source_id"],
            "source_sha256": raw["source_sha256"],
            "source_paragraph_index": raw[
                "source_paragraph_index"
            ],
            "excerpt_sha256": raw["excerpt_sha256"],
            "evidence_excerpt": excerpt,
            "priority_tier": tier,
            "priority_score": tri["priority_score"],
            "original_matched_signals": tri[
                "matched_signals"
            ],
            "batch_signals": signals,
            "review_track": track,
            "existing_same_evidence_policy_links": (
                by_evidence.get(candidate_id, [])
            ),
            "duplicate_policy_verified": False,
            "new_policy_verified": False,
            "legal_effect_verified": False,
            "semantic_support_verified": False,
            "review_status": "needs_review",
            "automatic_exclusion": False,
            "approved_for_user_answers": False,
            "approved_for_embedding": False,
        })

    if invalid_hashes:
        raise ValueError(
            f"Evidence 해시 오류: {invalid_hashes[:10]}"
        )

    if len(results) != len(remaining_ids):
        raise ValueError("일괄 검토 결과 건수 불일치")

    results.sort(
        key=lambda r: (
            TIER_ORDER.get(r["priority_tier"], 99),
            -r["priority_score"],
            r["candidate_id"],
        )
    )

    source_summary = {}

    for source_id, count in sorted(sources.items()):
        source_summary[source_id] = {
            "total": count,
            "tracks": {
                track: n
                for (sid, track), n in sorted(
                    by_source_track.items()
                )
                if sid == source_id
            },
        }

    report = {
        "program_id": "US-WK-01",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_consolidation": CONSOLIDATED.name,
        "input_candidate_file": CANDIDATES.name,
        "input_triage_file": TRIAGE.name,
        "processing_method": (
            "batch_heuristic_review_routing_only"
        ),
        "total_source_candidates": len(candidates),
        "existing_policy_id_records": len(existing),
        "existing_classified_evidence": len(used_ids),
        "remaining_candidates": len(results),
        "tier_counts": dict(tiers),
        "review_track_counts": dict(tracks),
        "source_summary": source_summary,
        "priority_queue": [
            {
                "candidate_id": r["candidate_id"],
                "source_id": r["source_id"],
                "priority_tier": r["priority_tier"],
                "review_track": r["review_track"],
                "excerpt_preview": r[
                    "evidence_excerpt"
                ][:250],
            }
            for r in results
            if r["priority_tier"] in (
                "high",
                "legal_review",
            )
        ],
        "review_records": results,
        "automatic_exclusion_performed": False,
        "new_policy_auto_approved": False,
        "semantic_support_verified": False,
        "legal_effect_verified": False,
        "review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    saved = read_json(OUTPUT)

    if len(saved["review_records"]) != 1352:
        raise ValueError("저장 후 검증 실패")

    print("=== H-1B BATCH REVIEW VALIDATION ===")
    print("SOURCE CANDIDATES:", len(candidates))
    print("EXISTING POLICY-ID RECORDS:", len(existing))
    print("CLASSIFIED EVIDENCE:", len(used_ids))
    print("BATCH REVIEWED CANDIDATES:", len(results))
    print("TIER COUNTS:", dict(tiers))
    print("REVIEW TRACK COUNTS:", dict(tracks))
    print("SOURCE GROUPS:", len(source_summary))
    print("EVIDENCE SHA-256: PASS")
    print("AUTOMATIC EXCLUSION: False")
    print("NEW POLICIES AUTO APPROVED: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)

    print("\n=== HIGH PRIORITY ROUTING ===")
    for r in results:
        if r["priority_tier"] == "high":
            print(
                r["candidate_id"],
                "|",
                r["review_track"],
                "|",
                r["source_id"],
            )

    print("\n=== NEXT ACTION ===")
    print(
        "Review grouped legal-effect and policy "
        "candidates; do not treat heuristic routing "
        "as final legal validation."
    )


if __name__ == "__main__":
    main()