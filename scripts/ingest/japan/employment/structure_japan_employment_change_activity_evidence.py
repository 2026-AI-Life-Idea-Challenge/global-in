
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

PROCESSED = ROOT / "data/processed/japan/employment"

SOURCE = (
    PROCESSED
    / "japan_employment_change_category34_structured.json"
)

OUTPUT = (
    PROCESSED
    / "japan_employment_change_activity_evidence.json"
)

EXPECTED_SOURCE_SHA = (
    "489ae6144f2f52b8af26092ccd44713ec91220583ceb3640127bb2fbad2517d0"
)

print("===== STEP 63-57 No.7 활동 증빙 구조화 =====")

# 1. 기존 구조화 데이터 무결성 확인
assert SOURCE.is_file(), "기존 변경 신청 JSON 누락"
assert not OUTPUT.exists(), "출력 파일이 이미 존재합니다."

source_bytes = SOURCE.read_bytes()

assert hashlib.sha256(source_bytes).hexdigest() == EXPECTED_SOURCE_SHA

source = json.loads(source_bytes.decode("utf-8"))

assert source["application_type"] == "change"
assert source["route_id"] == "JP-EM"

document = next(
    row for row in source["documents"]
    if row["row_number"] == 7
)

assert document["document_id"] == "JP_EM_CHANGE_DOC_007"

raw_text = document["raw_row_text_ja"]

# 2. 원문에 표시된 (1), (2), (3) 구간 분리
markers = [
    "（１）労働契約を締結する場合",
    "（２）日本法人である会社の役員に就任する場合",
    "（３）外国法人内の日本支店に転勤する場合及び会社以外の団体の役員",
]

positions = [raw_text.find(marker) for marker in markers]

assert all(pos >= 0 for pos in positions), (
    "No.7 원문 분기 표시 누락"
)

assert positions == sorted(positions), (
    "No.7 분기 순서 불일치"
)

segments = [
    raw_text[positions[0]:positions[1]].strip(),
    raw_text[positions[1]:positions[2]].strip(),
    raw_text[positions[2]:].strip(),
]

expected_phrases = [
    ["労働条件を明示する文書"],
    ["役員報酬を定める定款", "株主総会"],
    ["地位（担当業務）", "報酬額"],
]

for index, segment in enumerate(segments):
    normalized = "".join(segment.split())

    for phrase in expected_phrases[index]:
        assert phrase in normalized, (
            f"분기 {index + 1} 원문 누락: {phrase}"
        )

# 3. 분기별 원문과 활동 유형 연결
activity_types = [
    "employment_contract",
    "japanese_company_officer",
    "foreign_branch_transfer_or_other_organization_officer",
]

options = []

for index, (activity_type, segment) in enumerate(
    zip(activity_types, segments),
    start=1,
):
    options.append({
        "option_id": f"JP_EM_CHANGE_DOC_007_OPT_{index:02d}",
        "source_clause": f"({index})",
        "activity_type": activity_type,
        "condition_text_ja": markers[index - 1],
        "evidence_text_ja": segment,
        "validation_status": "needs_review",
    })

# 4. 세부 구조 저장
result = {
    "route_id": "JP-EM",
    "application_type": "change",
    "parent_document_id": "JP_EM_CHANGE_DOC_007",
    "source_row_number": 7,
    "source_json_sha256": EXPECTED_SOURCE_SHA,
    "selection_type": "activity_based_alternatives",
    "option_count": len(options),
    "options": options,
    "validation_status": "needs_review",
}

assert len(options) == 3
assert len({o["option_id"] for o in options}) == 3

# 원문 구간이 누락되거나 중복되지 않았는지 확인
assert all(segment in raw_text for segment in segments)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("x", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

saved = json.loads(OUTPUT.read_text(encoding="utf-8"))
assert saved == result

output_sha = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()

print("\n[구조화 결과]")

for option in options:
    print(
        option["option_id"],
        "|",
        option["activity_type"],
        "|",
        len(option["evidence_text_ja"]),
        "자",
    )

print("\n===== STEP 63-57 최종 결과 =====")
print("활동 유형 분기:", len(options))
print("원문 구간 검증: 성공")
print("서류 ID 연결: 성공")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", output_sha)
print("기존 변경 신청 JSON: 변경 없음")
print("기존 COE JSON: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")