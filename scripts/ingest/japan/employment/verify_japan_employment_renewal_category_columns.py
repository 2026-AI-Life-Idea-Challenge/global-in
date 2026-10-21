
from pathlib import Path
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_renewal_pdfs/001367009.pdf"
JSON_PATH = PROCESSED / "japan_employment_renewal_structured.json"

EXPECTED_PDF_SHA = (
    "472a27d772b1649e61fb99a2ec569e8eb48ee8cc6811789160cf1160a17fa622"
)

EXPECTED_JSON_SHA = (
    "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef"
)

# STEP 63-76에서 실제로 확인된 단어 시작 X 좌표
COLUMN_RANGES = {
    "1": (265.0, 330.0),
    "2": (330.0, 396.0),
    "3": (396.0, 461.0),
    "4": (461.0, 535.0),
}

Y_TOP = 270.94
Y_BOTTOM = 520.78


def verify_sha(path, expected):
    assert path.is_file(), f"파일 누락: {path}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, f"SHA-256 불일치: {path}"


print("===== STEP 63-77 No.4 열 분리 검증 =====")

verify_sha(PDF_PATH, EXPECTED_PDF_SHA)
verify_sha(JSON_PATH, EXPECTED_JSON_SHA)

data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

doc = next(
    row for row in data["documents"]
    if row["row_number"] == 4
)

assert doc["document_id"] == "JP_EM_RENEWAL_DOC_004"

results = {}

with pymupdf.open(PDF_PATH) as pdf:
    page = pdf[0]
    words = page.get_text("words", sort=False)

    for category, (left, right) in COLUMN_RANGES.items():
        selected = []

        for word in words:
            x0, y0, x1, y1, text, *_ = word

            center_y = (y0 + y1) / 2

            if not (Y_TOP <= center_y <= Y_BOTTOM):
                continue

            if not (left <= x0 < right):
                continue

            selected.append(word)

        # PDF 단어의 블록·행 번호로 정렬
        selected.sort(
            key=lambda w: (
                w[5], w[6], w[7]
            )
        )

        lines = {}

        for word in selected:
            key = (word[5], word[6])
            lines.setdefault(key, []).append(word)

        text_lines = []

        for key, line_words in lines.items():
            line_words.sort(key=lambda w: w[0])
            text_lines.append(
                "".join(w[4] for w in line_words)
            )

        text = "\n".join(text_lines).strip()
        results[category] = text

        print("\n" + "=" * 55)
        print(f"Category {category}")
        print("선택된 단어:", len(selected))
        print("문자 수:", len(text))
        print(text if text else "(별도 증빙 문구 없음)")

# PDF 줄바꿈과 공백을 제거한 검증용 문자열
# 원본 텍스트는 변경하지 않는다.
normalized = {
    category: "".join(text.split())
    for category, text in results.items()
}

# 카테고리별 핵심 문구 검증
assert "四季報" in normalized["1"]
assert "高度専門職省令" in normalized["1"]
assert "一定の条件を満た" in normalized["1"]

assert "法定調書合計表" in normalized["2"]
assert "在留申請オンライン" in normalized["2"]

assert "法定調書合計表" in normalized["3"]

assert not normalized["4"], (
    "Category 4에서 예상하지 못한 텍스트 발견"
)

# 다른 카테고리 열의 내용이 섞이지 않았는지 확인
assert "四季報" not in normalized["2"]
assert "在留申請オンライン" not in normalized["3"]

print("\n[정규화 검증]")
print("Category 1: PASS")
print("Category 2: PASS")
print("Category 3: PASS")
print("Category 4: PASS")

print("\n===== STEP 63-77 최종 결과 =====")
print("Category 1 원문: 검증 성공")
print("Category 2 원문: 검증 성공")
print("Category 3 원문: 검증 성공")
print("Category 4 별도 증빙 문구 없음: 확인")
print("PDF 및 JSON SHA-256: 일치")
print("파일 생성·수정: 없음")
print("정책 검증 상태: needs_review")