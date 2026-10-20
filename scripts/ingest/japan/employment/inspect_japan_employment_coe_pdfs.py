
from pathlib import Path
import hashlib
import json

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit(
        "PyMuPDF가 없습니다. pip install pymupdf 실행 후 재시도하세요."
    )

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = ROOT / "data/raw/japan/employment"
PDF_DIR = RAW_DIR / "japan_employment_coe_pdfs"
HASH_PATH = RAW_DIR / "japan_employment_coe_pdf_hashes.json"

print("===== STEP 63-8 일본 취업 COE PDF 구조 분석 =====")

assert HASH_PATH.is_file(), "PDF 해시 기록이 없습니다."

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))

assert hash_data["route_id"] == "JP-EM"
assert len(hash_data["files"]) == 3

KEYWORDS = [
    "カテゴリー１",
    "カテゴリー２",
    "カテゴリー３",
    "カテゴリー４",
    "カテゴリー",
    "提出書類",
    "申請人",
    "所属機関",
    "学歴",
    "職歴",
    "報酬",
]

for record in hash_data["files"]:
    filename = record["filename"]
    path = PDF_DIR / filename

    print("\n" + "=" * 65)
    print("PDF:", filename)
    print("설명:", record["description_ko"])

    assert path.is_file(), f"PDF 누락: {filename}"

    data = path.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()

    assert actual_hash == record["sha256"], (
        f"PDF SHA-256 불일치: {filename}"
    )

    with fitz.open(stream=data, filetype="pdf") as doc:
        print("페이지 수:", len(doc))

        page_texts = [
            page.get_text("text", sort=True)
            for page in doc
        ]

        total_chars = sum(len(t) for t in page_texts)
        print("추출된 문자 수:", total_chars)

        print("\n[키워드가 등장하는 페이지]")
        for keyword in KEYWORDS:
            pages = [
                i + 1
                for i, text in enumerate(page_texts)
                if keyword in text
            ]
            if pages:
                print(f"{keyword}: {pages[:20]}")

        print("\n[페이지별 본문 미리보기]")
        # 최대 4페이지까지만 출력하여 결과 길이 제한
        for i, text in enumerate(page_texts[:4], start=1):
            print(f"\n--- {i}페이지 ---")

            if not text.strip():
                print("(추출된 텍스트 없음)")
                continue

            print(text[:1800])

        if len(page_texts) > 4:
            print(
                f"\n나머지 {len(page_texts) - 4}페이지 "
                "미리보기 생략"
            )

    print("\n원본 SHA-256: 일치")

print("\n===== STEP 63-8 최종 결과 =====")
print("PDF 3개 읽기 및 해시 검증: 성공")
print("파일 수정·생성: 없음")
print("정책 검증 상태: needs_review")