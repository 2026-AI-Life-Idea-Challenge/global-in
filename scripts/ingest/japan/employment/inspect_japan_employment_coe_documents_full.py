
from pathlib import Path
import hashlib
import json
import re

import fitz

ROOT = Path(__file__).resolve().parents[4]
RAW_DIR = ROOT / "data/raw/japan/employment"
PDF_DIR = RAW_DIR / "japan_employment_coe_pdfs"
HASH_PATH = RAW_DIR / "japan_employment_coe_pdf_hashes.json"

TARGETS = [
    "001404131.pdf",
    "001437254.pdf",
]

print("===== STEP 63-9 COE 제출서류 전체 원문 확인 =====")

hash_data = json.loads(
    HASH_PATH.read_text(encoding="utf-8")
)

records = {
    item["filename"]: item
    for item in hash_data["files"]
}

for filename in TARGETS:
    path = PDF_DIR / filename
    assert path.is_file(), f"파일 누락: {filename}"
    assert filename in records, f"해시 기록 누락: {filename}"

    pdf_bytes = path.read_bytes()
    actual_hash = hashlib.sha256(pdf_bytes).hexdigest()

    assert actual_hash == records[filename]["sha256"], (
        f"SHA-256 불일치: {filename}"
    )

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        print("\n" + "=" * 70)
        print("파일:", filename)
        print("페이지 수:", len(doc))
        print("SHA-256 검증: 성공")

        for page_number, page in enumerate(doc, start=1):
            text = page.get_text("text", sort=True)

            assert text.strip(), (
                f"텍스트 추출 실패: {filename} "
                f"{page_number}페이지"
            )

            print(f"\n----- {page_number}페이지 전체 원문 -----")
            print(text)

            # 단독 행 번호만 추출하는 보조 검사
            row_numbers = [
                int(line.strip())
                for line in text.splitlines()
                if re.fullmatch(r"\d{1,2}", line.strip())
            ]

            print("\n[단독 줄로 추출된 서류 번호]")
            print(row_numbers)

print("\n===== 최종 결과 =====")
print("검사 대상 PDF:", len(TARGETS))
print("원본 해시 검증: 성공")
print("기존 파일 수정: 없음")
print("정책 검증 상태: needs_review")