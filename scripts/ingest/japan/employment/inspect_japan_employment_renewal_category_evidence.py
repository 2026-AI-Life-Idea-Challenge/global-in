
from pathlib import Path
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_renewal_pdfs/001367009.pdf"
HASH_PATH = RAW / "japan_employment_renewal_pdf_hashes.json"
JSON_PATH = PROCESSED / "japan_employment_renewal_structured.json"

PDF_SHA = (
    "472a27d772b1649e61fb99a2ec569e8eb48ee8cc6811789160cf1160a17fa622"
)

JSON_SHA = (
    "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef"
)

# No.4의 실제 표 경계 (STEP 63-73)
Y_TOP = 270.94
Y_BOTTOM = 520.78

# 카테고리 기호의 X 좌표를 기준으로 설정한 임시 열 범위
# 실제 PDF 추출 결과를 보고 확정할 예정
COLUMN_RANGES = {
    "1": (270.0, 327.7),
    "2": (327.7, 393.25),
    "3": (393.25, 458.75),
    "4": (458.75, 535.0),
}

def verify_sha(path, expected):
    assert path.is_file(), f"파일 누락: {path}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, f"SHA-256 불일치: {path}"
    return actual


print("===== STEP 63-76 No.4 카테고리별 증빙 분석 =====")

verify_sha(PDF_PATH, PDF_SHA)
verify_sha(JSON_PATH, JSON_SHA)

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))
assert hash_data["application_type"] == "renewal"
assert any(
    item["filename"] == PDF_PATH.name
    and item["sha256"] == PDF_SHA
    for item in hash_data["files"]
)

dataset = json.loads(JSON_PATH.read_text(encoding="utf-8"))
document = next(
    row for row in dataset["documents"]
    if row["row_number"] == 4
)

assert document["document_id"] == "JP_EM_RENEWAL_DOC_004"
assert document["page"] == 1

with pymupdf.open(PDF_PATH) as pdf:
    page = pdf[0]

    print("\n[카테고리별 원문 추출]")

    for category, (x0, x1) in COLUMN_RANGES.items():
        clip = pymupdf.Rect(
            x0, Y_TOP, x1, Y_BOTTOM
        )

        text = page.get_text(
            "text",
            clip=clip,
            sort=True,
        ).strip()

        print("\n" + "=" * 55)
        print(f"Category {category}")
        print(f"X 범위: {x0:.2f} ~ {x1:.2f}")
        print("문자 수:", len(text))
        print(text if text else "(추출된 텍스트 없음)")

    # 텍스트가 열 경계에 걸쳐 있는지 확인하기 위한
    # 원본 단어 좌표 출력
    print("\n" + "=" * 55)
    print("[No.4 오른쪽 표 영역 단어 좌표]")

    words = page.get_text("words", sort=False)

    for w in sorted(words, key=lambda x: (round(x[1], 1), x[0])):
        x0, y0, x1, y1, value, *_ = w
        center_y = (y0 + y1) / 2

        if (
            265 <= x0 <= 535
            and Y_TOP <= center_y <= Y_BOTTOM
        ):
            print(
                f"X={x0:6.1f}~{x1:6.1f} "
                f"Y={y0:6.1f} | {value}"
            )

print("\n===== STEP 63-76 최종 결과 =====")
print("공식 PDF SHA-256: 일치")
print("기존 구조화 JSON SHA-256: 일치")
print("No.4 카테고리별 열 분석: 완료")
print("열 경계 최종 확정: 후속 검토 필요")
print("파일 생성·수정: 없음")
print("정책 검증 상태: needs_review")