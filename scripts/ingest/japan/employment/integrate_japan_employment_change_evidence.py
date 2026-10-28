
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

INPUTS = {
    "main": (
        "japan_employment_change_category34_structured.json",
        "489ae6144f2f52b8af26092ccd44713ec91220583ceb3640127bb2fbad2517d0",
    ),
    "activity": (
        "japan_employment_change_activity_evidence.json",
        "6b6ed6e78de41e420598283dd4f7ca88b2e1db4381e7bd162cc58bfd862ed596",
    ),
    "education": (
        "japan_employment_change_education_evidence.json",
        "23ea16b31d1cc26a4f9c2e9570629edd2c641a42320dd1a175ddebadf9b53e7b",
    ),
    "tax": (
        "japan_employment_change_tax_evidence.json",
        "d0c04cac2597ebfdc092c67af94802715bf28e4beb192029dbd04e63e6672c7c",
    ),
}

OUTPUT = (
    BASE / "japan_employment_change_integrated.json"
)

print("===== STEP 63-61 변경 신청 데이터 통합 =====")

assert not OUTPUT.exists(), (
    "통합 JSON이 이미 존재합니다. 덮어쓰지 않습니다."
)

def sha256(data):
    return hashlib.sha256(data).hexdigest()

# 1. 입력 파일 로드 및 SHA-256 검증
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

main = data["main"]

assert main["route_id"] == "JP-EM"
assert main["application_type"] == "change"
assert main["document_count"] == 8
assert len(main["documents"]) == 8

assert [row["row_number"] for row in main["documents"]] == (
    list(range(7, 15))
)

# 2. 세부 증빙을 부모 서류에 연결
detail_map = {
    7: ("activity", "activity_evidence"),
    8: ("education", "education_evidence"),
    14: ("tax", "tax_evidence"),
}

for row in main["documents"]:
    number = row["row_number"]

    assert row["document_id"] == (
        f"JP_EM_CHANGE_DOC_{number:03d}"
    )
    assert row["validation_status"] == "needs_review"

    if number not in detail_map:
        continue

    key, field_name = detail_map[number]
    detail = data[key]

    assert detail["route_id"] == main["route_id"]
    assert detail["application_type"] == "change"

    assert detail["parent_document_id"] == row["document_id"]
    assert detail["source_row_number"] == number
    assert detail["source_json_sha256"] == INPUTS["main"][1]
    assert detail["validation_status"] == "needs_review"

    assert field_name not in row

    # 연결 정보는 중복 저장하지 않고,
    # 해당 서류의 실제 증빙 구조만 삽입
    if number == 7:
        assert detail["option_count"] == len(
            detail["options"]
        ) == 3

        row[field_name] = {
            "selection_type": detail["selection_type"],
            "option_count": detail["option_count"],
            "options": detail["options"],
            "validation_status": "needs_review",
        }

    elif number == 8:
        assert detail[
            "automatic_eligibility_rules_enabled"
        ] is False

        alternatives = detail["alternative_evidence"]

        assert alternatives["option_count"] == len(
            alternatives["options"]
        ) == 4

        row[field_name] = {
            "resume_evidence": detail["resume_evidence"],
            "alternative_evidence": alternatives,
            "automatic_eligibility_rules_enabled": False,
            "validation_status": "needs_review",
        }

    elif number == 14:
        assert detail[
            "automatic_eligibility_rules_enabled"
        ] is False

        assert len(detail["branches"]) == 2
        assert len(detail["branches"][1]["items"]) == 2
        assert len(
            detail["branches"][1]["items"][1]["options"]
        ) == 2

        assert (
            row["category_requirements"]
            == detail["category_requirements"]
        )

        row[field_name] = {
            "source_intro_ja": detail["source_intro_ja"],
            "branches": detail["branches"],
            "automatic_eligibility_rules_enabled": False,
            "validation_status": "needs_review",
        }

    print(
        f"[PASS] No.{number}: "
        f"{field_name} 연결 완료"
    )

# 3. 통합 데이터 메타데이터
main["dataset_type"] = "integrated_change_documents"

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

# 4. 최종 스키마 검증
rows = main["documents"]
by_number = {r["row_number"]: r for r in rows}

assert len(by_number) == 8

assert len(
    by_number[7]["activity_evidence"]["options"]
) == 3

assert len(
    by_number[8]["education_evidence"][
        "alternative_evidence"
    ]["options"]
) == 4

assert len(
    by_number[14]["tax_evidence"]["branches"]
) == 2

assert by_number[13]["category_requirements"]["3"][
    "symbol"
] == "△"

assert by_number[13]["category_requirements"]["4"][
    "symbol"
] == "△"

assert by_number[14]["category_requirements"]["3"][
    "symbol"
] is None

assert by_number[14]["category_requirements"]["4"][
    "symbol"
] == "○"

assert all(
    row["raw_row_text_ja"]
    for row in rows
)

# 5. 신규 파일 저장 — 기존 파일 덮어쓰기 금지
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("x", encoding="utf-8") as f:
    json.dump(
        main,
        f,
        ensure_ascii=False,
        indent=2,
    )

saved = json.loads(
    OUTPUT.read_text(encoding="utf-8")
)

assert saved == main

output_hash = sha256(OUTPUT.read_bytes())

print("\n===== STEP 63-61 최종 결과 =====")
print("신청 유형:", main["application_type"])
print("통합 제출서류:", len(rows))
print("세부 증빙 연결: 3/3")
print("No.7 활동 유형: 3개")
print("No.8 대체 증빙: 4개")
print("No.14 상위 분기: 2개")
print("원문 및 제출 기호: 유지")
print("자동 자격 판정: 비활성화")
print("출력 JSON:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", output_hash)
print("원본 JSON 4개: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")