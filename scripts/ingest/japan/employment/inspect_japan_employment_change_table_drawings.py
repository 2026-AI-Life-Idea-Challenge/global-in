
from pathlib import Path
from collections import Counter
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/raw/japan/employment"

PDF_PATH = RAW / "japan_employment_change_pdfs/001437255.pdf"
HASH_PATH = RAW / "japan_employment_change_pdf_hashes.json"

EXPECTED_SHA = (
    "9eab6a01e10204096ad569adafa70cab06246634000621442b0651c0e730bdb3"
)

print("===== STEP 63-53 PDF 표 도형 분석 =====")

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

    drawings = page.get_drawings()
    types = Counter()
    horizontal_candidates = []

    print("전체 drawing 객체:", len(drawings))

    for drawing in drawings:
        for item in drawing["items"]:
            kind = item[0]
            types[kind] += 1

            if kind == "l":
                p1, p2 = item[1], item[2]

                if abs(p1.y - p2.y) <= 0.8:
                    x0 = min(p1.x, p2.x)
                    x1 = max(p1.x, p2.x)

                    if x1 - x0 >= 100:
                        horizontal_candidates.append(
                            (round(p1.y, 2), round(x0, 1),
                             round(x1, 1), "line")
                        )

            elif kind == "re":
                rect = item[1]

                if rect.width >= 100:
                    horizontal_candidates.extend([
                        (
                            round(rect.y0, 2),
                            round(rect.x0, 1),
                            round(rect.x1, 1),
                            "rect_top",
                        ),
                        (
                            round(rect.y1, 2),
                            round(rect.x0, 1),
                            round(rect.x1, 1),
                            "rect_bottom",
                        ),
                    ])

    print("\n[도형 명령 유형별 개수]")
    for kind, count in sorted(types.items()):
        print(f"{kind}: {count}")

    print("\n[수평 경계 후보]")
    candidates = sorted(set(horizontal_candidates))

    for y, x0, x1, kind in candidates:
        if 100 <= y <= 810:
            print(
                f"Y={y:7.2f} | "
                f"X={x0:6.1f}~{x1:6.1f} | "
                f"{kind}"
            )

    print("\n수평 경계 후보 총개수:", len(candidates))

    # drawing 자체가 없는 경우 PDF 렌더링 구조 추가 확인
    if not drawings:
        print(
            "참고: 추출 가능한 도형이 없습니다. "
            "표가 이미지 또는 다른 방식으로 표현됐을 수 있습니다."
        )

print("\n===== STEP 63-53 결과 =====")
print("PDF SHA-256: 일치")
print("도형 유형 및 경계 후보 분석: 완료")
print("행 경계 좌표 확정: 아직 미실행")
print("기존 PDF 및 JSON 수정: 없음")
print("정책 검증 상태: needs_review")