
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/raw/japan/employment"

PDF_PATH = RAW / "japan_employment_change_pdfs/001437255.pdf"
HASH_PATH = RAW / "japan_employment_change_pdf_hashes.json"

EXPECTED_SHA = (
    "9eab6a01e10204096ad569adafa70cab06246634000621442b0651c0e730bdb3"
)

print("===== STEP 63-52 재류자격 변경 표 경계 분석 =====")

assert PDF_PATH.is_file(), "PDF 원본 누락"
assert HASH_PATH.is_file(), "해시 기록 누락"

pdf_bytes = PDF_PATH.read_bytes()
actual_sha = hashlib.sha256(pdf_bytes).hexdigest()

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))
record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

assert actual_sha == EXPECTED_SHA
assert actual_sha == record["sha256"]

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 1
    page = pdf[0]

    print("PDF 크기:", page.rect)

    # 1. 제출서류 번호 좌표
    numbers = {}

    for word in page.get_text("words", sort=False):
        x0, y0, x1, y1, text, *_ = word

        if not re.fullmatch(r"\d{1,2}", text.strip()):
            continue

        number = int(text)

        if number not in range(7, 15):
            continue

        # 서류 번호 열만 사용
        if not 95 <= x0 <= 120:
            continue

        assert number not in numbers, (
            f"서류 번호 중복: {number}"
        )

        numbers[number] = {
            "y_top": round(y0, 2),
            "y_center": round((y0 + y1) / 2, 2),
        }

    assert sorted(numbers) == list(range(7, 15))

    print("\n[서류 번호 좌표]")
    for number, position in sorted(numbers.items()):
        print(
            f"No.{number:02d}",
            "Y =", position["y_center"],
        )

    # 2. PDF 도형에서 수평 경계선 추출
    lines = []

    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] != "l":
                continue

            p1, p2 = item[1], item[2]

            if abs(p1.y - p2.y) > 0.8:
                continue

            x_min = min(p1.x, p2.x)
            x_max = max(p1.x, p2.x)

            # 표의 서류 설명 열을 가로지르는 선만 선택
            if x_min > 130 or x_max < 340:
                continue

            if not 100 <= p1.y <= 810:
                continue

            lines.append({
                "y": round((p1.y + p2.y) / 2, 2),
                "x_min": round(x_min, 2),
                "x_max": round(x_max, 2),
            })

    # 동일 Y에 여러 조각이 있을 수 있으므로 중복 제거
    unique_y = sorted(set(line["y"] for line in lines))

    print("\n[수평 경계선 후보]")
    print("후보 개수:", len(unique_y))

    for y in unique_y:
        print("Y =", y)

    # 3. 각 행 번호 주변의 경계선 확인
    print("\n[서류별 인접 경계 후보]")

    for number, position in sorted(numbers.items()):
        center = position["y_center"]

        upper_candidates = [
            y for y in unique_y if y < center
        ]
        lower_candidates = [
            y for y in unique_y if y > center
        ]

        upper = (
            max(upper_candidates)
            if upper_candidates else None
        )
        lower = (
            min(lower_candidates)
            if lower_candidates else None
        )

        print(
            f"No.{number:02d} | "
            f"위쪽={upper} | "
            f"번호Y={center} | "
            f"아래쪽={lower}"
        )

print("\n===== STEP 63-52 최종 결과 =====")
print("서류 번호: 7~14 확인")
print("수평 경계 후보 조사: 완료")
print("경계 좌표 최종 확정: 후속 검토 필요")
print("원본 PDF 및 JSON 수정: 없음")
print("정책 검증 상태: needs_review")