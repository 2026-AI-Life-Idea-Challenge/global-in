import hashlib
import json
import os
import re
import shutil
from pathlib import Path

RAW = Path("data/raw/australia/employment")
OUT = Path("data/processed/australia/employment")

HEADINGS = {
    "subclass_191_regional_provisional": [
        "Have an eligible visa",
        "Satisfy the income requirement",
        "Meet our health requirement",
        "Meet our character requirement",
        "Sign the Australian values statement",
        "Pay back your debt to the Australian Government",
    ],
    "subclass_491": [
        "Be invited to apply",
        "Be nominated or sponsored",
        "Be this age",
        "Have a suitable skills assessment",
        "Be able to score 65 points or more",
        "Have this level of English language",
        "Meet the skills requirement",
        "Meet our health requirement",
        "Meet our character requirement",
        "Have paid back your debt to the Australian government",
        "Sign the Australian values statement",
    ],
    "subclass_494_employer_sponsored": [
        "Be this age",
        "Be nominated by an approved sponsor",
        "Have relevant skills, qualifications and work experience",
        "Have a positive skills assessment",
        "Have this level of English language",
        "Meet our health requirement",
        "Meet our character requirement",
        "Have paid back your debt to the Australian government",
        "Sign the Australian values statement",
    ],
    "subclass_494_labour_agreement": [
        "Be working under a labour agreement",
        "Be this age",
        "Have relevant skills, qualifications and work experience",
        "Have a positive skills assessment",
        "Have this level of English language",
        "Meet our health requirement",
        "Meet our character requirement",
        "Have paid back your debt to the Australian government",
        "Sign the Australian values statement",
    ],
}

STEP_PATTERN = re.compile(
    r"(?im)^[ \t]*Step[ \t]+([1-9][0-9]*)"
    r"(?:\.[0-9]+)?(?=[ \t\r\n–—-])"
)

STEP_PROGRAMS = [
    "subclass_491",
    "subclass_482_core_skills",
    "subclass_482_specialist_skills",
]


def load_json(name):
    path = OUT / f"{name}_evidence_draft.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("program") != name:
        raise ValueError(f"Program mismatch: {path}")
    if data.get("review_status") != "needs_review":
        raise ValueError(f"Unexpected approval state: {name}")
    if (
        data.get("legal_validation_approved") is not False
        or data.get("approved_for_eligibility_decision") is not False
    ):
        raise ValueError(f"Protected approval state: {name}")
    return path, data


def split_eligibility(name, data):
    existing = data.get("eligibility_sections", [])
    if len(existing) != 1:
        raise ValueError(f"Expected one original section: {name}")

    original = existing[0]["original_text"]
    lines = original.splitlines(keepends=True)

    wanted = HEADINGS[name]
    positions = []

    for i, line in enumerate(lines):
        normalized = line.strip().rstrip(":").casefold()
        for heading in wanted:
            if normalized == heading.casefold():
                positions.append((i, heading))

    found = [heading for _, heading in positions]
    if found != wanted:
        raise ValueError(
            f"Heading mismatch: {name}\n"
            f"Expected: {wanted}\nFound: {found}"
        )

    # 앞부분에 원문이 있으면 첫 번째 섹션에 보존
    if positions[0][0] > 0:
        positions[0] = (0, positions[0][1])

    prefix = "AU_" + name.replace("subclass_", "").upper()
    source_hash = existing[0].get("source_sha256")

    if not source_hash:
        raise ValueError(f"Missing source hash: {name}")

    sections = []
    evidence = []
    policies = []

    for i, (start, heading) in enumerate(positions):
        end = (
            positions[i + 1][0]
            if i + 1 < len(positions)
            else len(lines)
        )

        block = "".join(lines[start:end])

        if not block.strip():
            raise ValueError(f"Empty section: {name} / {heading}")

        number = i + 1
        section_id = f"{prefix}_ELIG_{number:02d}"

        sections.append({
            "section_id": section_id,
            "topic": "topic_pending_review",
            "heading": heading,
            "source_tab": "eligibility",
            "source_sha256": source_hash,
            "start_line": start + 1,
            "end_line": end,
            "original_text": block,
            "detail_status": "segmented_needs_review",
            "review_status": "needs_review",
        })

        evidence.append({
            "evidence_id": f"{prefix}_EVD_{number:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "exact_quote": block,
            "start_line": start + 1,
            "end_line": end,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"{prefix}_POL_{number:02d}",
            "program": name,
            "topic": "topic_pending_review",
            "source_section_id": section_id,
            "source_text": block,
            "requirement_type": "needs_review",
            "exception_review_status": "needs_review",
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    if "".join(x["original_text"] for x in sections) != original:
        raise ValueError(f"Original content mismatch: {name}")

    data["eligibility_sections"] = sections
    data["evidence"] = evidence
    data["policy_candidates"] = policies

    # 기존 원문 메타데이터는 유지
    data["extraction_status"] = "sectioned_needs_review"

    return data


def split_steps(text, name):
    matches = list(STEP_PATTERN.finditer(text))

    # 상위 단계가 정확히 1~5인지 확인
    numbers = sorted(set(int(m.group(1)) for m in matches))
    if numbers != [1, 2, 3, 4, 5]:
        raise ValueError(
            f"Step numbers incomplete: {name} / {numbers}"
        )

    groups = []

    for number in range(1, 6):
        candidates = [
            m for m in matches if int(m.group(1)) == number
        ]

        start = candidates[0].start()
        next_matches = [
            m.start()
            for m in matches
            if int(m.group(1)) == number + 1
        ]

        end = min(next_matches) if next_matches else len(text)

        # 491은 Step 1.1 이전 안내문도 Step 1에 포함
        if number == 1:
            start = 0

        block = text[start:end]

        if not block.strip():
            raise ValueError(f"Empty step: {name} / {number}")

        groups.append({
            "step_number": number,
            "source_tab": "step_by_step",
            "original_text": block,
            "extraction_status": "segmented_needs_review",
            "review_status": "needs_review",
        })

    if "".join(x["original_text"] for x in groups) != text:
        raise ValueError(f"Step content mismatch: {name}")

    return groups


def update_steps(name, data):
    if name == "subclass_491":
        source = RAW / "subclass_491_steps_verified.txt"
        raw = source.read_text(encoding="utf-8-sig")

        marker = "REVIEW_STATUS: needs_review"
        if marker not in raw:
            raise ValueError("491 source header missing")

        text = raw.split(marker, 1)[1].strip()

    else:
        source = RAW / f"{name}_step_by_step.txt"
        text = source.read_text(encoding="utf-8-sig")

        # 내비게이션/메뉴 영역을 제외하고 Step 1부터 보존
        match = STEP_PATTERN.search(text)
        if match is None:
            raise ValueError(f"Step 1 not found: {name}")

        text = text[match.start():]

    if len(text) < 1000:
        raise ValueError(f"Insufficient steps: {name}")

    data["application_steps"] = split_steps(text, name)

    data["application_steps_source"] = {
        "source_file": source.as_posix(),
        "source_sha256": hashlib.sha256(
            source.read_bytes()
        ).hexdigest(),
        "review_status": "needs_review",
    }

    return data


def validate(data, name):
    sections = data.get("eligibility_sections", [])
    evidence = data.get("evidence", [])
    policies = data.get("policy_candidates", [])

    if not sections:
        raise ValueError(f"Missing eligibility sections: {name}")

    if not evidence:
        raise ValueError(f"Missing evidence: {name}")

    if not policies:
        raise ValueError(f"Missing policy candidates: {name}")

    ids = [
        s.get("section_id")
        for s in sections
        if isinstance(s, dict)
    ]

    if not all(ids):
        raise ValueError(f"Missing section ID: {name}")

    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate section IDs: {name}")

    # 기존 482 Evidence는 별도 source 필드 구조를 사용할 수 있음.
    # 식별자가 실제로 존재하는 항목만 연결 관계를 검증.
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid evidence item: {name}")

        source_id = item.get("source_section_id")

        if source_id is not None and source_id not in ids:
            raise ValueError(
                f"Broken evidence link: {name} / {source_id}"
            )

    for item in policies:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid policy item: {name}")

        source_id = item.get("source_section_id")

        if source_id is not None and source_id not in ids:
            raise ValueError(
                f"Broken policy link: {name} / {source_id}"
            )

        if (
            item.get("eligibility_rule") is not None
            or item.get("legal_validation_approved") is True
            or item.get("approved_for_eligibility_decision") is True
        ):
            raise ValueError(
                f"Unsafe policy: {name}"
            )

    if data.get("review_status") != "needs_review":
        raise ValueError(f"Unexpected review status: {name}")

    if (
        data.get("legal_validation_approved") is not False
        or data.get("approved_for_eligibility_decision") is not False
    ):
        raise ValueError(f"Unsafe approval state: {name}")


def main():
    # 1. 모든 JSON을 메모리에서 먼저 보완·검증
    updates = {}

    for name in sorted(set(HEADINGS) | set(STEP_PROGRAMS)):
        path, data = load_json(name)

        if name in HEADINGS:
            data = split_eligibility(name, data)

        if name in STEP_PROGRAMS:
            data = update_steps(name, data)

        validate(data, name)
        updates[path] = data

        print(
            "READY:", name,
            "ELIG:", len(data["eligibility_sections"]),
            "STEPS:", len(data["application_steps"]),
        )

    # 2. 기존 JSON 백업 파일 충돌 확인
    for path in updates:
        backup = path.with_suffix(".json.bak")
        if backup.exists():
            raise FileExistsError(
                f"Backup already exists: {backup}"
            )

    # 3. 기존 JSON을 변경하기 전에 백업
    for path in updates:
        shutil.copy2(path, path.with_suffix(".json.bak"))

    # 4. 임시 파일 작성 후 교체
    for path, data in updates.items():
        temp = path.with_suffix(".json.tmp")

        if temp.exists():
            raise FileExistsError(f"Temp file exists: {temp}")

        with temp.open("x", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        os.replace(temp, path)
        print("UPDATED:", path.as_posix())

    print("\n=== AU STRUCTURING BATCH ===")
    print("UPDATED:", len(updates))
    print("BACKUPS:", len(updates))
    print("LEGAL_APPROVED:", 0)
    print("DECISION_APPROVED:", 0)
    print("STATUS: STRUCTURED_NEEDS_REVIEW")


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_191_regional_provisional","subclass_491","subclass_494_employer_sponsored","subclass_494_labour_agreement"])
