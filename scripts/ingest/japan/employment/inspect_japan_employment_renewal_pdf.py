
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/raw/japan/employment"

PDF_PATH = (
    RAW / "japan_employment_renewal_pdfs/001367009.pdf"
)

HASH_PATH = (
    RAW / "japan_employment_renewal_pdf_hashes.json"
)

EXPECTED_SHA = (
    "472a27d772b1649e61fb99a2ec569e8eb48ee8cc6811789160cf1160a17fa622"
)

print("===== STEP 63-73 재류기간 갱신 PDF 구조 분석 =====")

# 1. 원본 파일 무결성 검증
assert PDF_PATH.is_file(), "공식 PDF 원본 누락"
assert HASH_PATH.is_file(), "SHA-256 기록 누락"

pdf_bytes = PDF_PATH.read_bytes()
actual_sha = hashlib.sha256(pdf_bytes).hexdigest()

hash_data = json.loads(
    HASH_PATH.read_text(encoding="utf-8")
)

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

assert actual_sha == EXPECTED_SHA
assert actual_sha == record["sha256"]

assert hash_data["route_id"] == "JP-EM"
assert hash_data["application_type"] == "renewal"

print("파일명:", PDF_PATH.name)
print("SHA-256:", actual_sha)
print("원본 무결성: PASS")

# 2. PDF 내용 분석
with pymupdf.open(
    stream=pdf_bytes,
    filetype="pdf",
) as pdf:

    print("\n[PDF 기본 정보]")
    print("전체 페이지:", len(pdf))

    for page_number, page in enumerate(pdf, start=1):
        print("\n" + "=" * 65)
        print(f"페이지 {page_number}")
        print("페이지 크기:", page.rect)

        text = page.get_text("text", sort=True)

        print("추출된 문자 수:", len(text))
        print(
            "일본어 포함:",
            bool(
                re.search(
                    r"[\u3040-\u30ff\u4e00-\u9fff]",
                    text,
                )
            ),
        )

        print("\n[일본어 원문]")
        print(text if text.strip() else "(추출된 텍스트 없음)")

        # 3. 제출서류 번호·제출 기호 좌표 확인
        words = page.get_text("words", sort=False)

        print("\n[숫자 단어 후보]")

        for word in words:
            x0, y0, x1, y1, value, *_ = word
            value = value.strip()

            if re.fullmatch(r"\d{1,2}", value):
                print(
                    f"번호={value} | "
                    f"X={x0:.1f} | Y={y0:.1f}"
                )

        print("\n[제출 기호 후보]")

        symbols = Counter()

        for word in words:
            x0, y0, x1, y1, value, *_ = word
            value = value.strip()

            if value in {"○", "△", "□", "－", "●"}:
                symbols[value] += 1

                print(
                    f"{value} | "
                    f"X={x0:.1f} | Y={y0:.1f}"
                )

        print("제출 기호별 개수:", dict(symbols))

        # 4. PDF 표 도형 구성 확인
        drawings = page.get_drawings()

        types = Counter(
            item[0]
            for drawing in drawings
            for item in drawing["items"]
        )

        print("\n[PDF 도형 구성]")
        print("Drawing 객체 수:", len(drawings))
        print("도형 유형별 개수:", dict(types))

        print("\n[수평 경계 후보]")

        boundaries = set()

        for drawing in drawings:
            for item in drawing["items"]:

                if item[0] == "l":
                    p1, p2 = item[1], item[2]

                    if abs(p1.y - p2.y) <= 0.8:
                        x0 = min(p1.x, p2.x)
                        x1 = max(p1.x, p2.x)

                        if x1 - x0 >= 100:
                            boundaries.add(round(p1.y, 2))

                elif item[0] == "re":
                    rect = item[1]

                    if rect.width >= 100:
                        boundaries.add(round(rect.y0, 2))
                        boundaries.add(round(rect.y1, 2))

        for y in sorted(boundaries):
            print("Y =", y)

        print("수평 경계 후보 수:", len(boundaries))

print("\n===== STEP 63-73 최종 결과 =====")
print("원본 PDF SHA-256: 일치")
print("원문 및 표 구조 분석: 완료")
print("기존 JSON 변경: 없음")
print("신규 구조화 JSON: 미생성")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")