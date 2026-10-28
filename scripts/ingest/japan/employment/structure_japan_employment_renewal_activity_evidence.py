
from pathlib import Path
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_renewal_pdfs/001367009.pdf"
SOURCE = PROCESSED / "japan_employment_renewal_structured.json"

OUTPUT = (
    PROCESSED / "japan_employment_renewal_activity_evidence.json"
)

EXPECTED_PDF_SHA = (
    "472a27d772b1649e61fb99a2ec569e8eb48ee8cc6811789160cf1160a17fa622"
)

EXPECTED_JSON_SHA = (
    "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef"
)

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def compact(text):
    return "".join(text.split())

print("===== STEP 63-80 No.8 활동 증빙 구조화 =====")

# 1. 입력 파일 검증
assert PDF_PATH.is_file(), "PDF 원본 누락"
assert SOURCE.is_file(), "기본 구조화 JSON 누락"

assert not OUTPUT.exists(), (
    "출력 JSON이 이미 존재합니다. 덮어쓰지 않습니다."
)

pdf_bytes = PDF_PATH.read_bytes()
source_bytes = SOURCE.read_bytes()

assert sha256(pdf_bytes) == EXPECTED_PDF_SHA
assert sha256(source_bytes) == EXPECTED_JSON_SHA

dataset = json.loads(source_bytes.decode("utf-8"))

assert dataset["route_id"] == "JP-EM"
assert dataset["application_type"] == "renewal"

document = next(
    d for d in dataset["documents"]
    if d["row_number"] == 8
)

assert document["document_id"] == "JP_EM_RENEWAL_DOC_008"
assert document["page"] == 2

assert document["category_requirements"]["3"]["symbol"] == "○"
assert document["category_requirements"]["4"]["symbol"] == "○"

# 2. PDF 본문 열 추출
# 오른쪽 카테고리 제출 기호를 제외한다.
with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    page = pdf[1]

    words = [
        w for w in page.get_text("words", sort=False)
        if 55 <= w[0] < 415
        and 71.26 <= (w[1] + w[3]) / 2 <= 208.18
    ]

    words.sort(key=lambda w: (w[5], w[6], w[7]))

    groups = {}

    for w in words:
        key = (w[5], w[6])
        groups.setdefault(key, []).append(w)

    lines = []

    for line_words in groups.values():
        line_words.sort(key=lambda w: w[0])
        lines.append("".join(w[4] for w in line_words))

    raw_text = "\n".join(lines).strip()

assert raw_text, "No.8 본문 추출 실패"

assert "活動内容等を明らかにする" in compact(raw_text)

# 3. 활동 유형별 원문 분리
markers = ["（１）", "（２）", "（３）"]

positions = [raw_text.find(marker) for marker in markers]

assert all(p >= 0 for p in positions), (
    "활동 유형 분기 표시 누락"
)

assert positions == sorted(positions), (
    "활동 유형 분기 순서 이상"
)

intro = raw_text[:positions[0]].strip()

segments = [
    raw_text[positions[0]:positions[1]].strip(),
    raw_text[positions[1]:positions[2]].strip(),
    raw_text[positions[2]:].strip(),
]

assert "いずれかの資料" in compact(intro)

# 원문이 누락되거나 중복되지 않았는지 검증
assert compact(raw_text) == compact(
    intro + "".join(segments)
)

ACTIVITY_TYPES = [
    "employment_contract",
    "japanese_company_officer",
    "foreign_branch_transfer_or_other_organization_officer",
]

EXPECTED_PHRASES = [
    ["労働契約", "労働条件"],
    ["日本法人", "役員報酬", "株主"],
    ["外国法人", "地位", "報酬額"],
]

options = []

for index, segment in enumerate(segments):
    normalized = compact(segment)

    for phrase in EXPECTED_PHRASES[index]:
        assert phrase in normalized, (
            f"분기 {index + 1} 원문 누락: {phrase}"
        )

    options.append({
        "option_id": (
            f"JP_EM_RENEWAL_DOC_008_OPT_{index + 1:02d}"
        ),
        "source_clause": f"({index + 1})",
        "activity_type": ACTIVITY_TYPES[index],
        "source_text_ja": segment,
        "validation_status": "needs_review",
    })

# 4. 추가 제출 조건 원문 연결
scope_note = dataset["additional_submission_note_ja"]

assert "転職後の初回の更新許可申請" in compact(scope_note)
assert "カテゴリー３又は４" in compact(scope_note)

result = {
    "route_id": "JP-EM",
    "application_type": "renewal",
    "parent_document_id": "JP_EM_RENEWAL_DOC_008",
    "source_row_number": 8,
    "source_page": 2,
    "source_pdf_sha256": EXPECTED_PDF_SHA,
    "source_json_sha256": EXPECTED_JSON_SHA,
    "source_intro_ja": intro,
    "raw_body_text_ja": raw_text,
    "applicability_scope": "additional_documents_after_job_change",
    "applicability_note_ja": scope_note,
    "category_requirements": document["category_requirements"],
    "selection_type": "activity_based_alternatives",
    "option_count": len(options),
    "options": options,
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

assert len(options) == 3
assert len({o["option_id"] for o in options}) == 3

# 5. 신규 파일 저장 (UTF-8, LF)
output_bytes = json.dumps(
    result,
    ensure_ascii=False,
    indent=2,
).encode("utf-8")

with OUTPUT.open("xb") as f:
    f.write(output_bytes)

assert OUTPUT.read_bytes() == output_bytes
assert json.loads(OUTPUT.read_text(encoding="utf-8")) == result

print("\n[구조화 결과]")

for option in options:
    print(
        option["option_id"],
        "|",
        option["activity_type"],
        "|",
        len(option["source_text_ja"]),
        "자",
    )

print("\n===== STEP 63-80 최종 결과 =====")
print("부모 서류: JP_EM_RENEWAL_DOC_008")
print("활동 유형 분기: 3개")
print("원문 구간 복원: 성공")
print("Category 3·4 제출 표시: 보존")
print("이직 후 첫 갱신 관련 주석: 보존")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", sha256(output_bytes))
print("기존 PDF·JSON: 변경 없음")
print("자동 자격 판정: 비활성화")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")