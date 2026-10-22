
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

from scripts.ingest.usa.employment.o1_extraordinary_ability.build_o1_policy_evidence import (
    load_source_pages,
)


ROOT = Path("data/processed/usa/employment/o1_extraordinary_ability")

POLICY_INPUT = ROOT / "o1_policy_review_2026_draft.json"
EVIDENCE_INPUT = ROOT / "o1_policy_evidence_2026_refined_draft.json"

POLICY_OUTPUT = ROOT / "o1_policy_review_2026_semantic_refined_draft.json"
EVIDENCE_OUTPUT = ROOT / "o1_policy_evidence_2026_semantic_refined_draft.json"
AUDIT_OUTPUT = ROOT / "o1_semantic_refinement_audit_2026.json"


# 1차 의미 검토에서 보완 대상으로 분류한 정책 28개.
# 검색어는 원본 문서의 실제 영어 표현을 우선 사용한다.
# regex 문법을 지원하며 대소문자는 구분하지 않는다.
#
# 찾지 못하면 기존 Evidence를 조용히 승인하지 않고,
# audit 파일에 실패 이유를 기록한다.

TARGETS = {
    "O1-01": (
        "USCIS-O1-OVERVIEW",
        [r"To qualify for an O-1 visa"],
    ),
    "O1-03": (
        "USCIS-O1-OVERVIEW",
        [r"extraordinary achievement\. This is evidenced"],
    ),
    "O1-04": (
        "USCIS-O-CH4",
        [r"Criterion 1: Documentation of the beneficiary.s receipt"],
    ),
    "O1-05": (
        "USCIS-O-CH4",
        [r"distinction in the field of arts",
         r"significant national or international award or prize"],
    ),
    "O1-11": (
        "USCIS-O-CH4",
        [r"Criterion 5: Evidence of the beneficiary.s original"],
    ),
    "O1-15": (
        "USCIS-O-CH4",
        [r"When a Petitioner May Use Comparable Evidence"],
    ),
    "O1-17": (
        "USCIS-O-CH4",
        [r"national or international recognition for achievements",
         r"critical reviews or other published materials"],
    ),
    "O1-21": (
        "USCIS-O-CH4",
        [r"Criterion 6: Evidence that the beneficiary has either commanded",
         r"Criterion 6: Evidence that the beneficiary has commanded"],
    ),
    "O1-22": (
        "USCIS-O-CH4",
        [r"comparable evidence.*?field of the arts",
         r"comparable evidence.*?beneficiar(?:y|ies) in the arts",
         r"comparable evidence.*?O-1B"],
    ),
    "O1-23": (
        "USCIS-O-CH4",
        [r"comparable evidence.*?not applicable.*?motion picture",
         r"motion picture or television.*?comparable evidence",
         r"cannot use comparable evidence"],
    ),
    "O1-25": (
        "USCIS-O-CH4",
        [r"distinction means a high level of achievement",
         r"totality of the evidence"],
    ),
    "O1-26": (
        "USCIS-O-CH4",
        [r"extraordinary achievement.*?motion picture",
         r"totality of the evidence"],
    ),
    "O1-35": (
        "USCIS-O-CH3",
        [r"In the case of an O-1 or O-2 beneficiary whose employment"],
    ),
    "O1-39": (
        "USCIS-O-CH7",
        [r"The summary does not have to be signed by both parties"],
    ),
    "O1-42": (
        "USCIS-O-CH7",
        [r"Up to 25 O-2 accompanying beneficiaries"],
    ),
    "O1-44": (
        "USCIS-O-CH7",
        [r"O-1B \(MPTV\).*?both the union",
         r"union representing the beneficiary.s occupational peers"],
    ),
    "O1-45": (
        "USCIS-O-CH7",
        [r"O-2 \(Arts and Athletics\)",
         r"labor organization having expertise in the skill area"],
    ),
    "O1-47": (
        "USCIS-O-CH7",
        [r"If the petitioner establishes that no appropriate peer group exists"],
    ),
    "O1-48": (
        "USCIS-O-CH7",
        [r"USCIS may waive the consultation requirement"],
    ),
    "O1-50": (
        "USCIS-O-CH5",
        [r"USCIS may not grant O-2 classification"],
    ),
    "O1-64": (
        "USCIS-O-CH9",
        [r"up to 60 days or until the end of the authorized validity period"],
    ),
    "O1-68": (
        "USCIS-G1055-20261016",
        [r"Asylum Program Fee"],
    ),
    "O1-69": (
        "DOS-TEMP-WORKER",
        [r"\$205"],
    ),
    "O1-70": (
        "USCIS-G1055-20261016",
        [r"\$2,965"],
    ),
    "O1-71": (
        "DOS-DS160-INSTRUCTIONS",
        [r"DS-160 confirmation page",
         r"print.*?confirmation page",
         r"Complete the Online Visa Application"],
    ),
    "O1-72": (
        "DOS-TEMP-WORKER",
        [r"Once USCIS approves the petition"],
    ),
    "O1-76": (
        "USCIS-O-CH9",
        [r"O-3 dependents may request an extension of stay or change of status"],
    ),
    "O1-77": (
        "USCIS-O-CH9",
        [r"In the case of a professional O-1 athlete traded"],
    ),
}


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, obj):
    if path.exists():
        raise FileExistsError(f"Output already exists: {path}")

    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_excerpt(pages, patterns, before=350, after=1750):
    for pattern in patterns:
        for page_number, content in pages:
            match = re.search(pattern, content, flags=re.I | re.S)

            if not match:
                continue

            start = max(0, match.start() - before)
            end = min(len(content), match.end() + after)
            excerpt = content[start:end]

            return {
                "source_page": page_number,
                "search_phrase": match.group(0),
                "evidence_excerpt": excerpt,
            }

    return None


def main():
    for path in [POLICY_OUTPUT, EVIDENCE_OUTPUT, AUDIT_OUTPUT]:
        if path.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing output: {path}"
            )

    policy_data = deepcopy(load_json(POLICY_INPUT))
    evidence_data = deepcopy(load_json(EVIDENCE_INPUT))

    policies = policy_data["policy_records"]
    evidence_records = evidence_data["evidence_records"]

    if len(policies) != 77 or len(evidence_records) != 77:
        raise ValueError("Expected exactly 77 policies and evidence records")

    policy_map = {p["policy_id"]: p for p in policies}
    evidence_map = {e["policy_id"]: e for e in evidence_records}
    source_map = {
        s["source_id"]: s
        for s in policy_data["official_sources"]
    }

    if len(policy_map) != 77 or len(evidence_map) != 77:
        raise ValueError("Duplicate policy or evidence IDs")

    if len(TARGETS) != 28:
        raise ValueError("Expected exactly 28 refinement targets")

    # 정책 내용 자체의 수정이 필요한 항목.
    # 기존 원본은 보존하고 새 JSON에만 적용한다.

    policy_map["O1-11"]["summary_ko"] = (
        "신청자가 해당 분야에서 수행한 독창적인 과학적, "
        "학술적 또는 사업 관련 기여가 분야 전체에 "
        "중대한 의미(major significance)를 갖는다는 증빙. "
        "단순한 독창성만으로 충분하지 않으며 "
        "기여의 중요성을 함께 입증해야 한다."
    )

    policy_map["O1-35"]["summary_ko"] = (
        "O-1 또는 O-2 수혜자의 고용이 자발적 사직 이외의 "
        "사유로 종료되는 경우, 해당 비이민 신분의 근거가 된 "
        "고용 제안을 한 고용주와 청원인(서로 다른 경우)은 "
        "미국 입국 전 수혜자의 마지막 거주지까지의 "
        "합리적인 귀국 교통비에 대해 공동으로 책임을 진다."
    )

    policy_map["O1-64"]["visa_classifications"] = [
        "O-1A", "O-1B Arts", "O-1B MPTV"
    ]
    policy_map["O1-64"]["summary_ko"] = (
        "O-1 수혜자의 고용이 종료되면 허가된 유효기간 "
        "종료일을 초과하지 않는 범위에서 최대 60일의 "
        "재량적 유예기간이 인정될 수 있다. "
        "USCIS는 상황에 따라 기간을 단축하거나 "
        "부여하지 않을 수 있으며, 이 기간 자체로 "
        "취업이 허용되는 것은 아니다. "
        "O-2에 동일 규칙이 적용되는지는 별도 검토한다."
    )

    # 출처별 텍스트는 한 번만 읽는다.
    source_cache = {}
    changed = []
    unmatched = []

    for policy_id, (source_id, patterns) in TARGETS.items():
        if policy_id not in policy_map:
            raise ValueError(f"Missing policy: {policy_id}")

        if source_id not in policy_map[policy_id]["source_ids"]:
            raise ValueError(
                f"Source {source_id} not registered for {policy_id}"
            )

        source = source_map[source_id]

        if source_id not in source_cache:
            source_cache[source_id] = load_source_pages(source)

        candidate = find_excerpt(
            source_cache[source_id],
            patterns,
        )

        if candidate is None:
            unmatched.append({
                "policy_id": policy_id,
                "source_id": source_id,
                "patterns": patterns,
                "reason": "target_phrase_not_found",
            })
            continue

        record = evidence_map[policy_id]
        excerpt = candidate["evidence_excerpt"]

        record["source_id"] = source_id
        record["source_path"] = source["local_path"]
        record["source_sha256"] = source["sha256"]
        record["source_page"] = candidate["source_page"]
        record["search_phrase"] = candidate["search_phrase"]
        record["evidence_excerpt"] = excerpt
        record["excerpt_sha256"] = digest(excerpt)
        record["evidence_type"] = "candidate_excerpt"
        record["semantic_support_verified"] = False
        record["review_status"] = "needs_review"

        changed.append(policy_id)

    # 기존 77개 Evidence와 ID를 유지한다.
    expected_ids = {
        f"O1-{i:02d}" for i in range(1, 78)
    }

    assert set(policy_map) == expected_ids
    assert set(evidence_map) == expected_ids

    assert all(
        p["review_status"] == "needs_review"
        for p in policies
    )

    assert all(
        e["review_status"] == "needs_review"
        and e["semantic_support_verified"] is False
        for e in evidence_records
    )

    # 기존 승인 및 자동 기능을 계속 비활성화.
    for field in [
        "approved_for_user_answers",
        "approved_for_embedding",
        "embedding_generated",
        "automatic_eligibility_rules_enabled",
    ]:
        policy_data[field] = False

    for field in [
        "approved_for_user_answers",
        "approved_for_embedding",
        "embedding_generated",
    ]:
        evidence_data[field] = False

    policy_data["validation_status"] = "needs_review"
    evidence_data["validation_status"] = "needs_review"
    evidence_data["refined_policy_ids"] = changed
    evidence_data["refinement_status"] = (
        "candidate_refinement_complete_review_pending"
        if not unmatched
        else "candidate_refinement_partial_review_pending"
    )

    audit = {
        "program_id": "US-WK-04",
        "refinement_target_count": len(TARGETS),
        "updated_evidence_count": len(changed),
        "updated_evidence_policy_ids": changed,
        "unmatched_count": len(unmatched),
        "unmatched_targets": unmatched,
        "policy_content_changed_ids": [
            "O1-11", "O1-35", "O1-64"
        ],
        "semantic_validation_approved": False,
        "legal_validation_approved": False,
        "remaining_semantic_review_required": True,
        "notes": (
            "Matching phrases and expanding excerpts do not "
            "constitute semantic or legal verification. "
            "PDF table row and column alignment requires review."
        ),
    }

    save_json(POLICY_OUTPUT, policy_data)
    save_json(EVIDENCE_OUTPUT, evidence_data)
    save_json(AUDIT_OUTPUT, audit)

    print("=== O VISA SEMANTIC REFINEMENT ===")
    print("Policies:", len(policies))
    print("Evidence:", len(evidence_records))
    print("Refinement targets:", len(TARGETS))
    print("Updated evidence:", len(changed))
    print("Unmatched targets:", len(unmatched))
    print("Policy content corrections:", 3)

    if unmatched:
        print("Unmatched IDs:", [
            x["policy_id"] for x in unmatched
        ])

    print("Policy output:", POLICY_OUTPUT)
    print("Evidence output:", EVIDENCE_OUTPUT)
    print("Audit output:", AUDIT_OUTPUT)
    print("All needs_review:", True)
    print("Semantic validation approved:", False)
    print("[PASS] Refinement draft files generated")
    print("[INFO] Semantic review and legal approval remain pending")


if __name__ == "__main__":
    main()