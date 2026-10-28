
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"

PDF_PATH = (
    RAW / "japan_employment_change_pdfs/001437255.pdf"
)

HASH_PATH = (
    RAW / "japan_employment_change_pdf_hashes.json"
)

EXPECTED_SHA = (
    "9eab6a01e10204096ad569adafa70cab06246634000621442b0651c0e730bdb3"
)

print("===== STEP 63-51 재류자격 변경 PDF 구조 분석 =====")

# 1. 원본 파일 및 SHA-256 검증
assert PDF_PATH.is_file(), "PDF 원본 누락"
assert HASH_PATH.is_file(), "SHA-256 기록 누락"

pdf_bytes = PDF_PATH.read_bytes()
actual_sha = hashlib.sha256(pdf_bytes).hexdigest()

assert actual_sha == EXPECTED_SHA, (
    "PDF SHA-256이 다운로드 당시와 다릅니다."
)

hash_data = json.loads(
    HASH_PATH.read_text(encoding="utf-8")
)

assert hash_data["route_id"] == "JP-EM"
assert hash_data["application_type"] == "change"

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

assert record["sha256"] == actual_sha

print("파일명:", PDF_PATH.name)
print("SHA-256:", actual_sha)
print("원본 무결성: 확인")

# 2. PDF 원문 추출
with pymupdf.open(
    stream=pdf_bytes,
    filetype="pdf",
) as pdf:

    print("\n[PDF 기본 정보]")
    print("전체 페이지:", len(pdf))

    for page_index, page in enumerate(pdf, start=1):
        print("\n" + "=" * 65)
        print(f"페이지 {page_index}")
        print("페이지 크기:", page.rect)

        text = page.get_text(
            "text",
            sort=True,
        )

        print("추출된 문자 수:", len(text))
        print("일본어 포함:", bool(
            re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text)
        ))

        print("\n[PDF 일본어 원문 전체]")
        print(text if text.strip() else "(추출된 텍스트 없음)")

        # 3. 서류 번호 위치 분석
        words = page.get_text("words", sort=False)

        number_candidates = []

        for word in words:
            x0, y0, x1, y1, value, *_ = word
            value = value.strip()

            if re.fullmatch(r"\d{1,2}", value):
                number_candidates.append({
                    "number": int(value),
                    "x": round(x0, 1),
                    "y": round(y0, 1),
                })

        print("\n[숫자 단어 후보]")
        for item in number_candidates:
            print(item)

        # 4. 카테고리별 기호 위치 분석
        print("\n[제출 기호 위치]")

        symbol_counts = {}

        for word in words:
            x0, y0, x1, y1, value, *_ = word
            value = value.strip()

            if value in {"○", "△", "□", "－", "●"}:
                symbol_counts[value] = (
                    symbol_counts.get(value, 0) + 1
                )

                print(
                    f"{value} "
                    f"x={x0:.1f} "
                    f"y={y0:.1f}"
                )

        print("\n제출 기호 개수:", symbol_counts)

print("\n===== STEP 63-51 최종 결과 =====")
print("원본 PDF SHA-256: 일치")
print("PDF 구조 분석: 완료")
print("원본 PDF 수정: 없음")
print("기존 COE JSON 수정: 없음")
print("구조화 JSON 생성: 미실행")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")