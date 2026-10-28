
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_change_pdfs/001437255.pdf"
HASH_PATH = RAW / "japan_employment_change_pdf_hashes.json"

OUTPUT = (
    PROCESSED
    / "japan_employment_change_category34_structured.json"
)

EXPECTED_PDF_SHA = (
    "9eab6a01e10204096ad569adafa70cab06246634000621442b0651c0e730bdb3"
)

# STEP 63-53~54에서 확인된 실제 표 경계
BOUNDARIES = [
    123.20, 243.08, 428.51, 442.45,
    494.89, 524.77, 554.65, 635.56, 770.34,
]

CATEGORY_X = {
    "3": 378.2,
    "4": 428.2,
}

EXPECTED_SYMBOLS = {
    7: ("○", "○"),
    8: ("○", "○"),
    9: ("○", "○"),
    10: ("○", "○"),
    11: ("○", "○"),
    12: ("○", "○"),
    13: ("△", "△"),
    14: (None, "○"),
}

SYMBOL_STATUS = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
    None: "not_explicitly_marked",
}

# 각 행에 반드시 포함돼야 하는 원문 문구
KEYWORDS = {
    7: ["活動内容", "労働条件", "役員"],
    8: ["学歴", "履歴書", "DOEACC", "在職証明書", "情報処理"],
    9: ["登記事項証明書"],
    10: ["事業内容", "案内書"],
    11: ["決算文書", "事業計画書"],
    12: ["所属機関の代表者", "申告書"],
    13: ["言語能力", "ＣＥＦＲ", "Ｂ２"],
    14: ["法定調書合計表", "源泉徴収", "給与支払事務所"],
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


print("===== STEP 63-55 재류자격 변경 서류 구조화 =====")

# 1. 입력 파일 및 기존 데이터 보호
assert PDF_PATH.is_file(), "원본 PDF 누락"
assert HASH_PATH.is_file(), "SHA-256 기록 누락"
assert not OUTPUT.exists(), (
    "출력 JSON이 이미 존재합니다. 덮어쓰지 않습니다."
)

pdf_bytes = PDF_PATH.read_bytes()
pdf_hash = sha256_bytes(pdf_bytes)

assert pdf_hash == EXPECTED_PDF_SHA, (
    "공식 PDF SHA-256 불일치"
)

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))

assert hash_data["route_id"] == "JP-EM"
assert hash_data["application_type"] == "change"

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

assert record["sha256"] == pdf_hash

# 2. PDF에서 행별 본문·제출 기호 추출
rows = []

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 1
    page = pdf[0]

    words = page.get_text("words", sort=False)

    for index, number in enumerate(range(7, 15)):
        upper = BOUNDARIES[index] + 0.5
        lower = BOUNDARIES[index + 1] - 0.5

        assert upper < lower

        # 본문 열만 추출해 제출 기호 혼입 방지
        body_clip = pymupdf.Rect(
            118, upper, 370, lower
        )

        body = page.get_text(
            "text",
            clip=body_clip,
            sort=True,
        ).strip()

        assert body, f"No.{number} 본문 누락"
        assert not re.search(r"[○●△□]", body), (
            f"No.{number} 본문에 표 기호 혼입"
        )

        normalized = "".join(body.split())

        for keyword in KEYWORDS[number]:
            assert keyword in normalized, (
                f"No.{number} 원문 문구 누락: {keyword}"
            )

        # 서류 번호의 실제 위치 확인
        number_words = [
            w for w in words
            if re.fullmatch(r"\d{1,2}", w[4].strip())
            and int(w[4]) == number
            and 95 <= w[0] <= 120
            and upper <= (w[1] + w[3]) / 2 <= lower
        ]

        assert len(number_words) == 1, (
            f"No.{number} 번호 검증 실패"
        )

        row_y = number_words[0][1]

        # 카테고리 3·4 제출 기호 분리
        requirements = {}
        actual_symbols = []

        for category, center_x in CATEGORY_X.items():
            candidates = [
                w[4].strip()
                for w in words
                if w[4].strip() in {"○", "△", "－"}
                and abs(w[0] - center_x) <= 8
                and upper <= (w[1] + w[3]) / 2 <= lower
            ]

            assert len(candidates) <= 1, (
                f"No.{number} Category {category} 기호 중복"
            )

            symbol = candidates[0] if candidates else None

            requirements[category] = {
                "symbol": symbol,
                "status": SYMBOL_STATUS[symbol],
            }

            actual_symbols.append(symbol)

        assert tuple(actual_symbols) == EXPECTED_SYMBOLS[number], (
            f"No.{number} 제출 기호 불일치"
        )

        rows.append({
            "document_id": f"JP_EM_CHANGE_DOC_{number:03d}",
            "row_number": number,
            "page": 1,
            "raw_row_text_ja": body,
            "category_requirements": requirements,
            "row_position_y": round(row_y, 2),
            "validation_status": "needs_review",
            "text_extraction_method": "pdf_table_boundaries_body_column",
        })

        print(
            f"No.{number:02d}",
            rows[-1]["document_id"],
            {k: v["symbol"] for k, v in requirements.items()},
            f"본문 {len(body)}자",
        )

# 3. 독립된 change 데이터셋 생성
dataset = {
    "route_id": "JP-EM",
    "program_id": "JP-EM-01",
    "application_type": "change",
    "status_of_residence": "技術・人文知識・国際業務",
    "source": {
        "official_agency": "Immigration Services Agency of Japan",
        "pdf_filename": PDF_PATH.name,
        "source_url": record["source_url"],
        "source_sha256": pdf_hash,
    },
    "category_columns": ["3", "4"],
    "document_count": len(rows),
    "validation_status": "needs_review",
    "documents": rows,
}

assert len(rows) == 8
assert [r["row_number"] for r in rows] == list(range(7, 15))
assert len({r["document_id"] for r in rows}) == 8

# 4. 저장 및 검증 — 기존 파일 덮어쓰기 금지
PROCESSED.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("x", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

saved = json.loads(OUTPUT.read_text(encoding="utf-8"))

assert saved == dataset, "저장된 JSON 내용 검증 실패"

output_hash = sha256_bytes(OUTPUT.read_bytes())

print("\n===== STEP 63-55 최종 결과 =====")
print("신청 유형:", dataset["application_type"])
print("구조화 서류:", len(rows))
print("서류 ID 중복: 없음")
print("카테고리별 제출 기호: 8/8 일치")
print("PDF 본문 기호 혼입: 없음")
print("원본 PDF SHA-256: 일치")
print("출력 JSON:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", output_hash)
print("기존 COE JSON: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")