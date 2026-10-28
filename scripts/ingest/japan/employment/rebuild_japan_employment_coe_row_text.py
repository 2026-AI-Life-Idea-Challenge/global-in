
from pathlib import Path
import hashlib
import json

import fitz

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = ROOT / "data/raw/japan/employment"
PDF_DIR = RAW_DIR / "japan_employment_coe_pdfs"
PROCESSED_DIR = ROOT / "data/processed/japan/employment"

# 검토용 파일은 Git 관리 대상인 processed 폴더 밖에 저장
REVIEW_DIR = ROOT / "_local_backup/japan_employment_review"

HASH_PATH = RAW_DIR / "japan_employment_coe_pdf_hashes.json"

# STEP 63-13에서 확인한 실제 표의 가로 구분선
# 각 행의 시작과 끝을 순서대로 지정
CONFIGS = [
    {
        "pdf": "001404131.pdf",
        "json": "japan_employment_coe_common_structured.json",
        "row_numbers": list(range(1, 7)),
        "boundaries": [
            153.0, 178.2, 256.68, 330.6,
            572.04, 632.76, 778.44,
        ],
    },
    {
        "pdf": "001437254.pdf",
        "json": "japan_employment_coe_category34_structured.json",
        "row_numbers": list(range(7, 15)),
        "boundaries": [
            141.5, 271.1, 459.31, 474.43,
            531.07, 563.35, 595.66,
            627.94, 773.64,
        ],
    },
]

EXPECTED_KEYWORDS = {
    1: ["在留資格認定証明書交付申請書"],
    2: ["写真"],
    3: ["返信用封筒"],
    4: ["所属機関", "カテゴリー", "定証等の写し"],
    5: ["専門士"],
    6: ["派遣", "労働者派遣個別契約書"],
    7: ["活動内容", "団体の文書"],
    8: ["学歴", "職歴", "情報処理", "３年以上"],
    9: ["登記事項証明書"],
    10: ["事業内容"],
    11: ["決算文書"],
    12: ["代表者"],
    13: ["ＣＥＦＲ", "Ｂ２"],
    14: ["法定調書合計表", "納期の特例"],
}

print("===== STEP 63-14 실제 행 경계 기반 원문 재추출 =====")

hash_data = json.loads(
    HASH_PATH.read_text(encoding="utf-8")
)

hash_records = {
    record["filename"]: record
    for record in hash_data["files"]
}

candidates = []

for config in CONFIGS:
    pdf_path = PDF_DIR / config["pdf"]
    json_path = PROCESSED_DIR / config["json"]
    candidate_path = REVIEW_DIR / config["json"]

    assert pdf_path.is_file(), f"PDF 누락: {pdf_path}"
    assert json_path.is_file(), f"JSON 누락: {json_path}"
    assert not candidate_path.exists(), (
        f"수정 후보가 이미 존재합니다: {candidate_path}"
    )

    pdf_bytes = pdf_path.read_bytes()
    actual_hash = hashlib.sha256(pdf_bytes).hexdigest()

    assert actual_hash == hash_records[config["pdf"]]["sha256"], (
        f"PDF 해시 불일치: {config['pdf']}"
    )

    # 기존 JSON 데이터 복사: 원본 수정하지 않음
    dataset = json.loads(json_path.read_text(encoding="utf-8"))

    assert [row["row_number"] for row in dataset["documents"]] == (
        config["row_numbers"]
    )

    boundaries = config["boundaries"]
    assert len(boundaries) == len(config["row_numbers"]) + 1
    assert boundaries == sorted(boundaries)

    print("\n" + "=" * 65)
    print("PDF:", config["pdf"])

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        assert len(doc) == 1
        page = doc[0]

        for index, row in enumerate(dataset["documents"]):
            number = row["row_number"]

            # 표 경계선을 피해서 행 내부만 추출
            upper = boundaries[index] + 0.6
            lower = boundaries[index + 1] - 0.6

            clip = fitz.Rect(
                0,
                upper,
                page.rect.width,
                lower,
            )

            text = page.get_text(
                "text",
                clip=clip,
                sort=True,
            ).strip()

            assert text, f"No.{number:02d} 원문이 비어 있습니다."

            missing = [
                keyword
                for keyword in EXPECTED_KEYWORDS[number]
                if keyword not in text
            ]

            assert not missing, (
                f"No.{number:02d} 누락 문구: {missing}"
            )

            row["raw_row_text_ja"] = text
            row["text_extraction_method"] = (
                "pdf_table_horizontal_boundaries"
            )

            print(
                f"No.{number:02d} | "
                f"문자 수: {len(text):4d} | "
                "대표 문구: 통과"
            )

            # 문제가 있었던 행은 전체 원문 출력
            if number in {3, 4, 8, 9, 13, 14}:
                print("----- 재추출 원문 -----")
                print(text)
                print("---------------------")

    candidates.append((candidate_path, dataset))

# 두 PDF 모두 검사에 통과한 경우에만 후보 파일 저장
REVIEW_DIR.mkdir(parents=True, exist_ok=True)

for path, dataset in candidates:
    with path.open("x", encoding="utf-8") as f:
        json.dump(
            dataset,
            f,
            ensure_ascii=False,
            indent=2,
        )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == dataset, "후보 JSON 저장 검증 실패"

    print("\n수정 후보 저장:", path.relative_to(ROOT))

print("\n===== STEP 63-14 결과 =====")
print("수정 후보 JSON:", len(candidates))
print("총 제출서류:", sum(
    len(dataset["documents"])
    for _, dataset in candidates
))
print("원본 PDF SHA-256: 검증 성공")
print("기존 processed JSON: 변경 없음")
print("정책 검증 상태: needs_review")