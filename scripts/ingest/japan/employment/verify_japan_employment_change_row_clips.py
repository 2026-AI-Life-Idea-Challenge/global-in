
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

BOUNDARIES = [
    123.20, 243.08, 428.51, 442.45,
    494.89, 524.77, 554.65, 635.56, 770.34,
]

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

print("===== STEP 63-54 변경 신청 서류 행별 검증 =====")

assert PDF_PATH.is_file()
assert HASH_PATH.is_file()

pdf_bytes = PDF_PATH.read_bytes()
pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))
record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

assert pdf_sha == EXPECTED_SHA == record["sha256"]

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 1
    page = pdf[0]

    words = page.get_text("words", sort=False)

    for index, number in enumerate(range(7, 15)):
        upper = BOUNDARIES[index] + 0.5
        lower = BOUNDARIES[index + 1] - 0.5

        assert upper < lower

        # 본문과 제출 기호를 구분하기 위해
        # 서류 설명 영역만 추출한다.
        body_clip = pymupdf.Rect(
            118, upper, 370, lower
        )

        body = page.get_text(
            "text",
            clip=body_clip,
            sort=True,
        ).strip()

        assert body, f"No.{number} 본문 누락"

        # 실제 서류 번호 단어의 중심이 행 내부에 있는지 확인
        row_numbers = [
            word
            for word in words
            if re.fullmatch(r"\d{1,2}", word[4].strip())
            and int(word[4]) == number
            and 95 <= word[0] <= 120
            and upper <= (word[1] + word[3]) / 2 <= lower
        ]

        assert len(row_numbers) == 1, (
            f"No.{number} 번호 위치 불일치"
        )

        # 카테고리별 제출 표시: ○, △, －
        # □ 체크박스는 의무 기호에서 제외한다.
        category_symbols = []

        for center_x in [378.2, 428.2]:
            candidates = [
                word[4].strip()
                for word in words
                if word[4].strip() in {"○", "△", "－"}
                and abs(word[0] - center_x) <= 8
                and upper <= (word[1] + word[3]) / 2 <= lower
            ]

            assert len(candidates) <= 1, (
                f"No.{number} 제출 기호 중복"
            )

            category_symbols.append(
                candidates[0] if candidates else None
            )

        assert tuple(category_symbols) == EXPECTED_SYMBOLS[number], (
            f"No.{number} 기호 불일치: {category_symbols}"
        )

        assert not re.search(r"[○●△□]", body), (
            f"No.{number} 본문에 표 기호 혼입"
        )

        print("\n" + "=" * 55)
        print(f"No.{number:02d}")
        print(f"Y 경계: {upper:.2f} ~ {lower:.2f}")
        print("Category 3:", category_symbols[0])
        print("Category 4:", category_symbols[1])
        print("본문 문자 수:", len(body))
        print("\n[일본어 본문]")
        print(body)

print("\n===== STEP 63-54 최종 결과 =====")
print("검증 서류: 8개")
print("서류 번호 위치: 8/8 확인")
print("카테고리 제출 기호: 8/8 일치")
print("본문 영역 기호 혼입: 없음")
print("원본 PDF SHA-256: 일치")
print("기존 JSON 수정: 없음")
print("정책 검증 상태: needs_review")