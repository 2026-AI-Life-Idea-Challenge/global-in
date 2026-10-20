
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

FILES = {
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

print("===== STEP 63-60 변경 신청 데이터 무결성 검증 =====")

data = {}

# 1. 각 파일의 SHA-256 검사
for key, (filename, expected_sha) in FILES.items():
    path = BASE / filename

    assert path.is_file(), f"파일 누락: {filename}"

    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()

    assert actual_sha == expected_sha, (
        f"SHA-256 불일치: {filename}"
    )

    data[key] = json.loads(raw.decode("utf-8"))

    print(f"[PASS] {key}: SHA-256 일치")

main = data["main"]
activity = data["activity"]
education = data["education"]
tax = data["tax"]

# 2. 신청 유형 및 문서 ID 검사
assert all(
    d["route_id"] == "JP-EM"
    and d["application_type"] == "change"
    for d in data.values()
)

docs = {
    doc["document_id"]: doc
    for doc in main["documents"]
}

assert len(docs) == 8
assert main["document_count"] == 8

for key, number in [
    ("activity", 7),
    ("education", 8),
    ("tax", 14),
]:
    detail = data[key]
    parent_id = f"JP_EM_CHANGE_DOC_{number:03d}"

    assert detail["parent_document_id"] == parent_id
    assert parent_id in docs
    assert detail["source_row_number"] == number
    assert detail["source_json_sha256"] == FILES["main"][1]
    assert detail["validation_status"] == "needs_review"

    print(f"[PASS] No.{number}: 부모 서류 연결 정상")

# 3. No.7 활동 유형별 분기
assert activity["option_count"] == 3
assert len(activity["options"]) == 3

assert all(
    option["validation_status"] == "needs_review"
    for option in activity["options"]
)

print("[PASS] No.7: 활동 유형 3개")

# 4. No.8 학력·경력 증빙
assert education["resume_evidence"]["evidence_text_ja"]

alternatives = education["alternative_evidence"]

assert alternatives["option_count"] == 4
assert len(alternatives["options"]) == 4

assert [
    o["source_clause"]
    for o in alternatives["options"]
] == ["ア", "イ", "ウ", "エ"]

it_option = next(
    o for o in alternatives["options"]
    if o["source_clause"] == "ウ"
)

assert (
    it_option["source_note_ja"]
    == "※５の資料を提出している場合は不要"
)

assert education["automatic_eligibility_rules_enabled"] is False

print("[PASS] No.8: 이력서 + 선택지 4개, IT 주석 보존")

# 5. No.14 원천징수 관련 분기
branches = tax["branches"]

assert len(branches) == 2
assert len(branches[1]["items"]) == 2
assert len(branches[1]["items"][1]["options"]) == 2

assert tax["category_requirements"]["3"]["symbol"] is None
assert tax["category_requirements"]["4"]["symbol"] == "○"

assert tax["automatic_eligibility_rules_enabled"] is False

print("[PASS] No.14: 조건 분기 2개 및 하위 증빙 정상")

# 6. 정책 검증 상태
assert all(
    d["validation_status"] == "needs_review"
    for d in data.values()
)

assert all(
    doc["validation_status"] == "needs_review"
    for doc in main["documents"]
)

print("[PASS] 정책 검증 상태: needs_review")

print("\n===== STEP 63-60 최종 결과 =====")
print("JSON SHA-256: 4/4 일치")
print("부모 서류 ID 연결: 3/3 정상")
print("No.7 활동 유형: 3개")
print("No.8 대체 증빙: 4개")
print("No.14 최상위 조건: 2개")
print("자동 자격 판정: 비활성화")
print("기존 파일 변경: 없음")
print("최종 결과: PASS")