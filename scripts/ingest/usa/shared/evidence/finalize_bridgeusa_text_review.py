
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]

FOLDER = ROOT / "data/processed/usa/employment"

INPUT = FOLDER / "bridgeusa_j1_text_review_draft.json"
OUTPUT = FOLDER / "bridgeusa_j1_text_review_v2_draft.json"

BOUNDARIES = {
    8: (
        "educational and cultural exchange programs "
        "in the United States."
    ),
    13: "as appropriate in specific circumstances.",
}


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"기존 결과를 덮어쓰지 않습니다: {OUTPUT}"
        )

    original_bytes = INPUT.read_bytes()
    original = json.loads(original_bytes.decode("utf-8"))
    revised = copy.deepcopy(original)

    expected = {
        "j1_intern": "US-EM-02",
        "j1_trainee": "US-EM-03",
    }

    assert set(revised["programs"]) == set(expected)

    review_records = []

    for name, program in revised["programs"].items():
        assert program["program_id"] == expected[name]
        assert program["section_count"] == 13
        assert len(program["sections"]) == 13

        for section in program["sections"]:
            index = section["section_index"]

            if index not in BOUNDARIES:
                continue

            text = section["cleaned_text"]
            marker = BOUNDARIES[index]

            # 각 섹션에서 예상한 정책 종료 문장이
            # 정확히 한 번만 나타나는 경우에만 처리
            if text.count(marker) != 1:
                raise ValueError(
                    f"{name} section {index}: "
                    "정책 경계를 확정할 수 없습니다."
                )

            before, separator, after = text.partition(marker)
            assert separator == marker

            # 지금까지 확인한 정책 문장은 전부 보존
            policy_text = (before + marker).strip()

            if not policy_text or not after.strip():
                raise ValueError(
                    f"{name} section {index}: "
                    "제거 대상이 예상과 다릅니다."
                )

            section["cleaned_text"] = policy_text
            section["ui_tail_excluded"] = True
            section["excluded_tail_sha256"] = sha256(after)
            section["excluded_tail_length"] = len(after)
            section["review_boundary"] = marker

            review_records.append({
                "program": name,
                "section_index": index,
                "kept_length": len(policy_text),
                "excluded_length": len(after),
                "excluded_preview": after.strip()[:150],
                "original_links_preserved": True,
            })

    assert len(review_records) == 4

    # 원본 HTML 및 기존 근거 데이터와의
    # 연결 정보는 변경하지 않음
    revised["revision"] = "v2"
    revised["revision_method"] = (
        "explicitly_reviewed_section_tail_boundaries"
    )
    revised["previous_draft_sha256"] = hashlib.sha256(
        original_bytes
    ).hexdigest()
    revised["excluded_tail_review"] = review_records

    revised["section_boundaries_verified"] = False
    revised["semantic_review_completed"] = False
    revised["validation_status"] = "needs_review"
    revised["approved_for_user_answers"] = False
    revised["approved_for_embedding"] = False
    revised["automatic_eligibility_rules_enabled"] = False
    revised["embedding_generated"] = False
    revised["existing_files_modified"] = False

    # 모든 프로그램의 검수 상태 유지
    for program in revised["programs"].values():
        program["section_boundaries_verified"] = False
        program["eligibility_rules_verified"] = False
        program["validation_status"] = "needs_review"

    # 원본 파일을 읽기만 하고 새 초안 생성
    payload = json.dumps(
        revised, ensure_ascii=False, indent=2
    ) + "\n"

    OUTPUT.write_text(payload, encoding="utf-8")

    saved = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert saved == revised
    assert INPUT.read_bytes() == original_bytes

    for record in review_records:
        print(
            "[PASS]",
            record["program"],
            "section",
            record["section_index"],
            "kept=",
            record["kept_length"],
            "excluded=",
            record["excluded_length"],
        )
        print("  Excluded:", record["excluded_preview"])

    print("[PASS] Four reviewed section boundaries applied")
    print("[PASS] Existing draft unchanged")
    print("[PASS] Original links retained")
    print("[PASS] New JSON syntax and content")
    print("Output:", OUTPUT.relative_to(ROOT))
    print("Status: needs_review")


if __name__ == "__main__":
    main()