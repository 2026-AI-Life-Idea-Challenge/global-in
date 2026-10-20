
from pathlib import Path
import hashlib
import json
import re

import fitz

ROOT = Path(__file__).resolve().parents[4]
RAW_DIR = ROOT / "data/raw/japan/employment"
PDF_DIR = RAW_DIR / "japan_employment_coe_pdfs"
HASH_PATH = RAW_DIR / "japan_employment_coe_pdf_hashes.json"

TARGETS = {
    "001404131.pdf": list(range(1, 7)),
    "001437254.pdf": list(range(7, 15)),
}

print("===== STEP 63-10 COE PDF 표 좌표 분석 =====")

records = {
    item["filename"]: item
    for item in json.loads(
        HASH_PATH.read_text(encoding="utf-8")
    )["files"]
}

for filename, expected_numbers in TARGETS.items():
    path = PDF_DIR / filename
    assert path.is_file()
    data = path.read_bytes()

    assert (
        hashlib.sha256(data).hexdigest()
        == records[filename]["sha256"]
    ), f"해시 불일치: {filename}"

    with fitz.open(stream=data, filetype="pdf") as doc:
        assert len(doc) == 1, "예상과 다른 페이지 수"
        page = doc[0]

        print("\n" + "=" * 65)
        print("파일:", filename)
        print("페이지 크기:", tuple(round(v, 1) for v in page.rect))

        words = page.get_text("words", sort=False)

        # 단어의 실제 좌표를 이용한 행 번호 추출
        row_candidates = []

        for word in words:
            x0, y0, x1, y1, text, *_ = word

            if re.fullmatch(r"\d{1,2}", text.strip()):
                number = int(text.strip())

                if number in expected_numbers:
                    row_candidates.append({
                        "number": number,
                        "x": round(x0, 1),
                        "y": round(y0, 1),
                    })

        print("\n[행 번호 후보]")
        for item in sorted(
            row_candidates,
            key=lambda x: (x["number"], x["x"]),
        ):
            print(
                f"No.{item['number']:02d} "
                f"x={item['x']} y={item['y']}"
            )

        print("\n[제출 기호의 좌표 분포]")

        symbols = []
        for word in words:
            x0, y0, _, _, text, *_ = word
            if text.strip() in {"○", "△", "－", "□"}:
                symbols.append((
                    round(x0, 1),
                    round(y0, 1),
                    text.strip(),
                ))

        print("기호 개수:", len(symbols))

        for x, y, symbol in sorted(
            symbols,
            key=lambda item: (item[1], item[0]),
        ):
            print(f"y={y:6.1f} x={x:6.1f} {symbol}")

        detected = sorted({
            item["number"] for item in row_candidates
        })

        print("\n확인된 서류 번호:", detected)
        print("예상 번호:", expected_numbers)

        if detected != expected_numbers:
            print(
                "주의: 일부 번호는 텍스트 블록에 "
                "결합되어 있을 수 있음"
            )

    print("SHA-256 검증: 성공")

print("\n분석 완료")
print("기존 PDF/JSON 수정: 없음")
print("정책 검증 상태: needs_review")