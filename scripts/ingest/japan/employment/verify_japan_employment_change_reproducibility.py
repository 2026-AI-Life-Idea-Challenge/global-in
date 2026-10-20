
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

TARGET = BASE / "japan_employment_change_integrated.json"

EXPECTED_TARGET_SHA = (
    "6e3fbddc14dc408ee73064211b0eef9c36d08f8652095c0bd5811bd86b1f0cc7"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


print("===== STEP 63-62 통합 JSON 재현성 검증 =====")

assert TARGET.is_file(), "기존 통합 JSON 누락"

target_bytes = TARGET.read_bytes()

assert sha256(target_bytes) == EXPECTED_TARGET_SHA, (
    "기존 통합 JSON SHA-256 불일치"
)

data = {}

for key, (filename, expected_sha) in INPUTS.items():
    path = BASE / filename
    assert path.is_file(), f"입력 파일 누락: {filename}"

    raw = path.read_bytes()
    assert sha256(raw) == expected_sha, (
        f"입력 파일 SHA-256 불일치: {filename}"
    )

    data[key] = json.loads(raw.decode("utf-8"))
    print(f"[PASS] {key}: SHA-256 일치")


# 1. STEP 63-61의 통합 로직을 독립적으로 재실행
main = data["main"]

assert main["route_id"] == "JP-EM"
assert main["application_type"] == "change"
assert main["document_count"] == 8
assert len(main["documents"]) == 8
assert [r["row_number"] for r in main["documents"]] == list(range(7, 15))

detail_map = {
    7: ("activity", "activity_evidence"),
    8: ("education", "education_evidence"),
    14: ("tax", "tax_evidence"),
}

for row in main["documents"]:
    number = row["row_number"]
    assert row["document_id"] == f"JP_EM_CHANGE_DOC_{number:03d}"
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

    if number == 7:
        assert detail["option_count"] == len(detail["options"]) == 3

        row[field_name] = {
            "selection_type": detail["selection_type"],
            "option_count": detail["option_count"],
            "options": detail["options"],
            "validation_status": "needs_review",
        }

    elif number == 8:
        assert detail["automatic_eligibility_rules_enabled"] is False

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
        assert detail["automatic_eligibility_rules_enabled"] is False
        assert len(detail["branches"]) == 2
        assert len(detail["branches"][1]["items"]) == 2
        assert len(
            detail["branches"][1]["items"][1]["options"]
        ) == 2
        assert row["category_requirements"] == detail["category_requirements"]

        row[field_name] = {
            "source_intro_ja": detail["source_intro_ja"],
            "branches": detail["branches"],
            "automatic_eligibility_rules_enabled": False,
            "validation_status": "needs_review",
        }

    print(f"[PASS] No.{number}: 세부 증빙 재연결")


# 2. 통합 메타데이터 재생성
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


# 3. 구조 및 주요 조건 검증
rows = main["documents"]
by_number = {r["row_number"]: r for r in rows}

assert len(by_number) == 8
assert len(by_number[7]["activity_evidence"]["options"]) == 3
assert len(
    by_number[8]["education_evidence"]["alternative_evidence"]["options"]
) == 4
assert len(by_number[14]["tax_evidence"]["branches"]) == 2

assert all(
    by_number[13]["category_requirements"][c]["symbol"] == "△"
    for c in ("3", "4")
)

assert by_number[14]["category_requirements"]["3"]["symbol"] is None
assert by_number[14]["category_requirements"]["4"]["symbol"] == "○"
assert all(row["raw_row_text_ja"] for row in rows)


# 4. STEP 63-61과 동일한 JSON 직렬화 방식
reproduced_text = json.dumps(
    main,
    ensure_ascii=False,
    indent=2,
)

# STEP 63-61에서 Windows 텍스트 모드로 저장한
# JSON의 CRLF 줄바꿈 방식을 재현한다.
reproduced_bytes = reproduced_text.replace(
    "\n", "\r\n"
).encode("utf-8")

reproduced_sha = sha256(reproduced_bytes)

# Windows 텍스트 저장 방식과 LF 방식 비교
reproduced_crlf = reproduced_text.replace(
    "\n", "\r\n"
).encode("utf-8")

print("\n[줄바꿈 진단]")
print("기존 CRLF 개수:", target_bytes.count(b"\r\n"))
print("기존 LF 개수:", target_bytes.count(b"\n"))
print("재생성 LF SHA-256:", reproduced_sha)
print("재생성 CRLF SHA-256:", sha256(reproduced_crlf))
print("CRLF 바이트 일치:", reproduced_crlf == target_bytes)

print("\n[재현성 비교]")
print("기존 SHA-256:", sha256(target_bytes))
print("재생성 SHA-256:", reproduced_sha)

assert reproduced_sha == EXPECTED_TARGET_SHA, (
    "재생성 SHA-256 불일치"
)

assert reproduced_bytes == target_bytes, (
    "기존 JSON과 바이트 단위 결과 불일치"
)

assert json.loads(target_bytes.decode("utf-8")) == main

print("\n===== STEP 63-62 최종 결과 =====")
print("입력 JSON SHA-256: 4/4 일치")
print("통합 제출서류: 8개")
print("세부 증빙 연결: 3/3 일치")
print("기존·재생성 JSON SHA-256: 일치")
print("바이트 단위 재현성: PASS")
print("파일 생성·수정: 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")