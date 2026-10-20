
from pathlib import Path
import hashlib
import json

import fitz

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = ROOT / "data/raw/japan/employment"
PDF_DIR = RAW_DIR / "japan_employment_coe_pdfs"
HASH_PATH = RAW_DIR / "japan_employment_coe_pdf_hashes.json"

TARGETS = [
    "001404131.pdf",
    "001437254.pdf",
]

records = {
    item["filename"]: item
    for item in json.loads(
        HASH_PATH.read_text(encoding="utf-8")
    )["files"]
}

print("===== STEP 63-13 COE PDF 실제 행 경계 조사 =====")

for filename in TARGETS:
    path = PDF_DIR / filename

    assert path.is_file(), f"파일 누락: {filename}"
    assert filename in records, f"해시 기록 누락: {filename}"

    data = path.read_bytes()

    assert hashlib.sha256(data).hexdigest() == records[
        filename
    ]["sha256"], f"해시 불일치: {filename}"

    with fitz.open(stream=data, filetype="pdf") as doc:
        page = doc[0]

        print("\n" + "=" * 65)
        print("PDF:", filename)
        print("페이지 높이:", round(page.rect.height, 2))

        print("\n[가로 구분선 후보]")

        horizontal_lines = []

        for drawing in page.get_drawings():
            for item in drawing["items"]:
                if item[0] == "l":
                    start, end = item[1], item[2]

                    if (
                        abs(start.y - end.y) < 1.0
                        and abs(start.x - end.x) > 100
                    ):
                        horizontal_lines.append(round(start.y, 2))

                elif item[0] == "re":
                    rect = item[1]

                    if rect.width > 100:
                        horizontal_lines.extend([
                            round(rect.y0, 2),
                            round(rect.y1, 2),
                        ])

        unique_lines = sorted(set(horizontal_lines))

        print("가로 구분선 개수:", len(unique_lines))
        print("Y 좌표:", unique_lines)

        print("\n[텍스트 줄의 시작 Y 좌표와 내용]")

        info = page.get_text("dict", sort=True)

        for block in info["blocks"]:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                text = "".join(
                    span["text"]
                    for span in line["spans"]
                ).strip()

                if not text:
                    continue

                y = round(line["bbox"][1], 1)
                x = round(line["bbox"][0], 1)

                # 표 헤더를 제외하고 본문 중심으로 조사
                if y < 125:
                    continue

                print(
                    f"Y={y:6.1f} X={x:6.1f} "
                    f"{text[:90]}"
                )

    print("\nSHA-256 검증: 성공")

print("\n===== 검사 완료 =====")
print("파일 변경: 없음")
print("정책 검증 상태: needs_review")