
from pathlib import Path
import hashlib
import json
import re

import fitz

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = ROOT / "data/raw/japan/employment"
PDF_DIR = RAW_DIR / "japan_employment_coe_pdfs"
PROCESSED_DIR = ROOT / "data/processed/japan/employment"
HASH_PATH = RAW_DIR / "japan_employment_coe_pdf_hashes.json"

CONFIGS = [
    {
        "filename": "001404131.pdf",
        "output": "japan_employment_coe_common_structured.json",
        "numbers": list(range(1, 7)),
        "columns": {
            "1": 249.0,
            "2": 323.9,
            "3": 398.8,
            "4": 473.6,
        },
        "expected_symbols": {
            1: ["○", "○", "○", "○"],
            2: ["○", "○", "○", "○"],
            3: ["○", "○", "○", "○"],
            4: [None, None, None, None],
            5: ["△", "△", "△", "△"],
            6: ["△", "△", "△", "△"],
        },
    },
    {
        "filename": "001437254.pdf",
        "output": "japan_employment_coe_category34_structured.json",
        "numbers": list(range(7, 15)),
        "columns": {
            "3": 384.1,
            "4": 438.9,
        },
        "expected_symbols": {
            7: ["○", "○"],
            8: ["○", "○"],
            9: ["○", "○"],
            10: ["○", "○"],
            11: ["○", "○"],
            12: ["○", "○"],
            13: ["△", "△"],
            14: [None, "○"],
        },
    },
]

SYMBOL_STATUS = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
    None: "not_explicitly_marked",
}

print("===== STEP 63-11 COE 제출서류 1차 구조화 =====")

assert HASH_PATH.is_file(), "PDF 해시 기록이 없습니다."

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))
assert hash_data["route_id"] == "JP-EM"

hash_records = {
    record["filename"]: record
    for record in hash_data["files"]
}

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# 기존 결과 파일을 하나라도 덮어쓰지 않도록 사전 검사
for config in CONFIGS:
    output_path = PROCESSED_DIR / config["output"]
    assert not output_path.exists(), (
        f"기존 JSON이 존재합니다: {output_path}"
    )

outputs = []

for config in CONFIGS:
    filename = config["filename"]
    path = PDF_DIR / filename

    assert path.is_file(), f"PDF 누락: {filename}"
    assert filename in hash_records, f"해시 기록 누락: {filename}"

    pdf_bytes = path.read_bytes()
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    assert sha256 == hash_records[filename]["sha256"], (
        f"원본 SHA-256 불일치: {filename}"
    )

    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        assert len(pdf) == 1, "예상과 다른 페이지 수"
        page = pdf[0]
        words = page.get_text("words", sort=False)

        # 서류 번호와 실제 좌표 추출
        row_positions = {}

        for word in words:
            x0, y0, x1, y1, text, *_ = word

            if not re.fullmatch(r"\d{1,2}", text.strip()):
                continue

            number = int(text.strip())

            if number not in config["numbers"]:
                continue

            assert number not in row_positions, (
                f"서류 번호 중복: {number}"
            )

            row_positions[number] = {
                "x": x0,
                "y": y0,
            }

        assert sorted(row_positions) == config["numbers"], (
            f"서류 번호 누락 또는 불일치: {filename}"
        )

        # 카테고리별 제출 기호 좌표
        symbols = []

        for word in words:
            x0, y0, x1, y1, text, *_ = word
            symbol = text.strip()

            if symbol in {"○", "△", "－"}:
                symbols.append({
                    "x": x0,
                    "y": y0,
                    "symbol": symbol,
                })

        numbers = config["numbers"]
        rows = []

        for index, number in enumerate(numbers):
            row_y = row_positions[number]["y"]

            # 각 행의 구간은 인접한 서류 번호의
            # 중간 좌표를 사용해 구분한다.
            if index == 0:
                upper = max(0, row_y - 55)
            else:
                prev_y = row_positions[numbers[index - 1]]["y"]
                upper = (prev_y + row_y) / 2

            if index == len(numbers) - 1:
                lower = page.rect.height
            else:
                next_y = row_positions[numbers[index + 1]]["y"]
                lower = (row_y + next_y) / 2

            clip = fitz.Rect(
                0, upper,
                page.rect.width, lower,
            )

            row_text = page.get_text(
                "text",
                clip=clip,
                sort=True,
            ).strip()

            requirements = {}

            for category, column_x in config["columns"].items():
                candidates = [
                    symbol
                    for symbol in symbols
                    if abs(symbol["y"] - row_y) < 8
                    and abs(symbol["x"] - column_x) < 12
                ]

                assert len(candidates) <= 1, (
                    f"제출 기호 중복: {number}, {category}"
                )

                symbol = (
                    candidates[0]["symbol"]
                    if candidates else None
                )

                requirements[category] = {
                    "symbol": symbol,
                    "status": SYMBOL_STATUS[symbol],
                }

            actual = [
                requirements[category]["symbol"]
                for category in config["columns"]
            ]

            expected = config["expected_symbols"][number]

            assert actual == expected, (
                f"기호 불일치: {filename} "
                f"No.{number}: {actual} != {expected}"
            )

            rows.append({
                "document_id": f"JP_EM_COE_DOC_{number:03d}",
                "row_number": number,
                "page": 1,
                "raw_row_text_ja": row_text,
                "category_requirements": requirements,
                "row_position_y": round(row_y, 2),
                "validation_status": "needs_review",
            })

    dataset = {
        "route_id": "JP-EM",
        "program_id": "JP-EM-01",
        "application_type": "coe",
        "status_of_residence": "技術・人文知識・国際業務",
        "source": {
            "official_agency": "Immigration Services Agency of Japan",
            "pdf_filename": filename,
            "source_url": hash_records[filename]["source_url"],
            "source_sha256": sha256,
        },
        "category_columns": list(config["columns"]),
        "document_count": len(rows),
        "validation_status": "needs_review",
        "documents": rows,
    }

    outputs.append((config["output"], dataset))

# 모든 PDF 분석이 성공한 후에만 JSON 저장
for output_name, dataset in outputs:
    output_path = PROCESSED_DIR / output_name

    with output_path.open("x", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved == dataset, f"저장 검증 실패: {output_name}"

    print("\n저장 파일:", output_path.relative_to(ROOT))
    print("서류 개수:", dataset["document_count"])

    for row in dataset["documents"]:
        symbols = {
            category: item["symbol"]
            for category, item
            in row["category_requirements"].items()
        }

        print(
            f"  No.{row['row_number']:02d}",
            row["document_id"],
            symbols,
        )

all_ids = [
    row["document_id"]
    for _, dataset in outputs
    for row in dataset["documents"]
]

assert len(all_ids) == 14
assert len(set(all_ids)) == 14

print("\n===== 최종 결과 =====")
print("구조화 JSON:", len(outputs))
print("전체 서류:", len(all_ids))
print("서류 ID 중복: 없음")
print("카테고리별 제출 기호 검증: 성공")
print("원본 PDF SHA-256 검증: 성공")
print("정책 검증 상태: needs_review")
print("조건부 규칙 해석: 후속 작업")