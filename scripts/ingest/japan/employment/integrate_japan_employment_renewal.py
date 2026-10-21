
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

INPUTS = {
    "main": (
        "japan_employment_renewal_structured.json",
        "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef",
    ),
    "category": (
        "japan_employment_renewal_category_evidence.json",
        "27db1ad63a15ba5b2c4a0e9946983ffd6656fef7e21b58d5b5152e3240317b7a",
    ),
    "dispatch": (
        "japan_employment_renewal_dispatch_evidence.json",
        "3f735ab9b7c7c9581c38e83e0a176c321cebe6e413575a1b661e75e9c7691df5",
    ),
    "activity": (
        "japan_employment_renewal_activity_evidence.json",
        "67421741ccb63c4a3b5dd105588cba5479353ef9c9c0037d8fedadd981d153db",
    ),
    "tax": (
        "japan_employment_renewal_tax_evidence.json",
        "f48361c0db679f78c276e4a3cf7da0d48ddf8f87d6d83c204ff83ed551036447",
    ),
}

OUTPUT = BASE / "japan_employment_renewal_integrated.json"

print("===== STEP 63-83 갱신 신청 데이터 통합 =====")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# 1. 기존 출력 보호
assert not OUTPUT.exists(), (
    "통합 JSON이 이미 존재합니다. 덮어쓰지 않습니다."
)

# 2. 입력 JSON 무결성 검사
data = {}

for key, (filename, expected_hash) in INPUTS.items():
    path = BASE / filename

    assert path.is_file(), f"입력 파일 누락: {filename}"

    raw = path.read_bytes()

    assert sha256(raw) == expected_hash, (
        f"SHA-256 불일치: {filename}"
    )

    data[key] = json.loads(raw.decode("utf-8"))
    print(f"[PASS] {key}: SHA-256 일치")


# 3. 기본 제출서류 검증
main = data["main"]

assert main["route_id"] == "JP-EM"
assert main["program_id"] == "JP-EM-01"
assert main["application_type"] == "renewal"
assert main["document_count"] == 13
assert len(main["documents"]) == 13
assert main["validation_status"] == "needs_review"
assert main["automatic_eligibility_rules_enabled"] is False

rows = main["documents"]

assert [r["row_number"] for r in rows] == list(range(1, 14))

assert len({r["document_id"] for r in rows}) == 13

assert all(
    r["raw_row_text_ja"]
    and r["validation_status"] == "needs_review"
    for r in rows
)

assert "提出資料１３は不要" in "".join(
    main["additional_submission_note_ja"].split()
)

# 4. 세부 증빙과 부모 서류 연결 설정
detail_map = {
    4: ("category", "category_evidence"),
    5: ("dispatch", "dispatch_evidence"),
    8: ("activity", "activity_evidence"),
    13: ("tax", "tax_evidence"),
}

connected = set()

for row in rows:
    number = row["row_number"]

    assert row["document_id"] == (
        f"JP_EM_RENEWAL_DOC_{number:03d}"
    )

    if number not in detail_map:
        continue

    key, field_name = detail_map[number]
    detail = data[key]

    # 공통 부모 연결 검증
    assert detail["route_id"] == main["route_id"]
    assert detail["application_type"] == "renewal"
    assert detail["parent_document_id"] == row["document_id"]
    assert detail["source_row_number"] == number

    assert detail["source_json_sha256"] == INPUTS["main"][1]
    assert detail["validation_status"] == "needs_review"

    assert detail["automatic_eligibility_rules_enabled"] is False
    assert field_name not in row

    if "category_requirements" in detail:
        assert (
            row["category_requirements"]
            == detail["category_requirements"]
        )

    if "source_pdf_sha256" in detail:
        assert (
            detail["source_pdf_sha256"]
            == main["source"]["source_sha256"]
        )

    # No.4 Category별 소속기관 증빙
    if number == 4:
        evidence = detail["category_evidence"]

        expected_counts = {
            "1": 4,
            "2": 2,
            "3": 1,
            "4": 0,
        }

        assert set(evidence) == set(expected_counts)

        for category, count in expected_counts.items():
            item = evidence[category]

            assert item["option_count"] == count
            assert len(item["options"]) == count

        assert evidence["4"]["no_separate_evidence_text"] is True
        assert evidence["4"]["source_text_ja"] == ""

        row[field_name] = {
            "selection_type": detail["selection_type"],
            "category_evidence": evidence,
            "category_4_interpretation": (
                detail["category_4_interpretation"]
            ),
            "automatic_eligibility_rules_enabled": False,
            "validation_status": "needs_review",
        }

    # No.5 파견근로 관련 증빙
    elif number == 5:
        pledge = detail["pledge_documents"]
        dispatch = detail["dispatch_activity_documents"]

        assert pledge["item_count"] == len(
            pledge["items"]
        ) == 2

        assert dispatch["item_count"] == len(
            dispatch["items"]
        ) == 5

        assert (
            dispatch["selection_type"]
            == "source_listed_documents"
        )

        assert "直近の在留期間中" in dispatch["source_note_ja"]

        row[field_name] = {
            "applicability_condition_ja": (
                detail["applicability_condition_ja"]
            ),
            "pledge_documents": pledge,
            "dispatch_activity_documents": dispatch,
            "automatic_eligibility_rules_enabled": False,
            "validation_status": "needs_review",
        }

    # No.8 활동 유형별 증빙
    elif number == 8:
        assert detail["selection_type"] == (
            "activity_based_alternatives"
        )

        assert detail["option_count"] == len(
            detail["options"]
        ) == 3

        assert detail["applicability_scope"] == (
            row["applicability_scope"]
        )

        assert detail["applicability_note_ja"] == (
            main["additional_submission_note_ja"]
        )

        row[field_name] = {
            "source_intro_ja": detail["source_intro_ja"],
            "selection_type": detail["selection_type"],
            "option_count": detail["option_count"],
            "options": detail["options"],
            "automatic_eligibility_rules_enabled": False,
            "validation_status": "needs_review",
        }

    # No.13 원천징수 증빙
    elif number == 13:
        branches = detail["branches"]

        assert detail["branch_count"] == len(branches) == 2

        assert len(branches[1]["components"]) == 2

        assert len(
            branches[1]["components"][1]["options"]
        ) == 2

        assert (
            branches[1]["components"][1]["selection_type"]
            == "source_stated_alternatives"
        )

        assert detail["applicability_scope"] == (
            row["applicability_scope"]
        )

        assert detail["applicability_note_ja"] == (
            main["additional_submission_note_ja"]
        )

        assert row["category_requirements"]["3"][
            "symbol"
        ] is None

        assert row["category_requirements"]["4"][
            "symbol"
        ] == "○"

        row[field_name] = {
            "source_intro_ja": detail["source_intro_ja"],
            "branch_count": detail["branch_count"],
            "branches": branches,
            "automatic_eligibility_rules_enabled": False,
            "validation_status": "needs_review",
        }

    connected.add(number)

    print(f"[PASS] No.{number}: {field_name} 연결 완료")


# 5. 통합 메타데이터
assert connected == set(detail_map)

main["dataset_type"] = "integrated_renewal_documents"

main["integration_sources"] = [
    {
        "role": key,
        "filename": INPUTS[key][0],
        "sha256": INPUTS[key][1],
    }
    for key in INPUTS
]

main["automatic_eligibility_rules_enabled"] = False
main["validation_status"] = "needs_review"


# 6. 최종 스키마 및 조건 검증
by_number = {
    row["row_number"]: row
    for row in main["documents"]
}

assert len(by_number) == 13

assert len(
    by_number[4]["category_evidence"][
        "category_evidence"
    ]["1"]["options"]
) == 4

assert len(
    by_number[5]["dispatch_evidence"][
        "dispatch_activity_documents"
    ]["items"]
) == 5

assert len(
    by_number[8]["activity_evidence"]["options"]
) == 3

assert len(
    by_number[13]["tax_evidence"]["branches"]
) == 2

assert by_number[12]["category_requirements"]["3"][
    "symbol"
] == "△"

assert by_number[12]["category_requirements"]["4"][
    "symbol"
] == "△"

assert by_number[13]["category_requirements"]["3"][
    "symbol"
] is None

assert by_number[13]["category_requirements"]["4"][
    "symbol"
] == "○"

assert len(main["integration_sources"]) == 5

# 7. 신규 통합 JSON 저장
# 기존 5개 입력 파일은 수정하지 않음
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

output_bytes = json.dumps(
    main,
    ensure_ascii=False,
    indent=2,
).encode("utf-8")

with OUTPUT.open("xb") as f:
    f.write(output_bytes)

assert OUTPUT.read_bytes() == output_bytes

saved = json.loads(OUTPUT.read_text(encoding="utf-8"))

assert saved == main

output_hash = sha256(OUTPUT.read_bytes())

# 8. 최종 결과 출력
print("\n===== STEP 63-83 최종 결과 =====")
print("신청 유형:", main["application_type"])
print("통합 제출서류:", len(rows))
print("세부 증빙 연결:", len(connected), "/4")
print("No.4 Category별 증빙: 4/2/1/0")
print("No.5 파견 서약서: 2종")
print("No.5 활동 증빙: 5종")
print("No.8 활동 유형: 3개")
print("No.13 원천징수 상위 분기: 2개")
print("No.13 중첩 선택지: 2개")
print("원문 및 제출 기호: 유지")
print("자동 자격 판정: 비활성화")
print("출력 JSON:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", output_hash)
print("기존 입력 JSON 5개: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")