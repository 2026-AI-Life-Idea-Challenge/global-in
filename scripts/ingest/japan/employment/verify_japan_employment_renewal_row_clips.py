
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/raw/japan/employment"

PDF_PATH = RAW / "japan_employment_renewal_pdfs/001367009.pdf"
HASH_PATH = RAW / "japan_employment_renewal_pdf_hashes.json"

EXPECTED_SHA = (
    "472a27d772b1649e61fb99a2ec569e8eb48ee8cc6811789160cf1160a17fa622"
)

# STEP 63-73에서 확인한 사각형 표 경계의 중앙 Y 좌표
ROW_BOUNDARIES = {
    1: {
        "numbers": list(range(1, 8)),
        "y": [
            126.58, 158.62, 238.30, 270.34,
            521.38, 666.82, 728.02, 818.86,
        ],
    },
    2: {
        "numbers": list(range(8, 14)),
        "y": [
            70.66, 208.78, 299.62, 390.46,
            481.30, 575.74, 716.62,
        ],
    },
}

CATEGORY_X = {
    "1": 294.9,
    "2": 360.5,
    "3": 426.0,
    "4": 491.5,
}

EXPECTED_SYMBOLS = {
    1: ("○", "○", "○", "○"),
    2: ("○", "○", "○", "○"),
    3: ("○", "○", "○", "○"),
    4: (None, None, None, None),
    5: ("△", "△", "△", "△"),
    6: (None, None, "○", "○"),
    7: (None, None, "○", "○"),
    8: (None, None, "○", "○"),
    9: (None, None, "○", "○"),
    10: (None, None, "○", "○"),
    11: (None, None, "○", "○"),
    12: (None, None, "△", "△"),
    13: (None, None, None, "○"),
}

KEYWORDS = {
    1: ["在留期間更新許可申請書"],
    2: ["写真", "６か月以内"],
    3: ["パスポート", "在留カード"],
    4: ["カテゴリー", "証明する文書"],
    5: ["派遣契約", "派遣先", "労働条件通知書"],
    6: ["所属機関の代表者", "申告書"],
    7: ["住民税", "納税証明書"],
    8: ["活動内容", "労働契約", "役員報酬"],
    9: ["登記事項証明書"],
    10: ["事業内容", "案内書"],
    11: ["決算文書", "事業計画書"],
    12: ["言語能力", "ＣＥＦＲ", "Ｂ２"],
    13: ["法定調書合計表", "源泉徴収"],
}


def compact(value):
    return "".join(value.split())


print("===== STEP 63-74 갱신 신청 행별 구조 검증 =====")

assert PDF_PATH.is_file()
assert HASH_PATH.is_file()

pdf_bytes = PDF_PATH.read_bytes()
actual_sha = hashlib.sha256(pdf_bytes).hexdigest()

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))
record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

assert actual_sha == EXPECTED_SHA == record["sha256"]
assert hash_data["application_type"] == "renewal"

validated = []

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 2

    # 페이지 2 상단의 중요한 추가 제출 조건 확인
    page2 = pdf[1]
    note_clip = pymupdf.Rect(0, 0, 595, 70.5)
    note_text = page2.get_text(
        "text",
        clip=note_clip,
        sort=True,
    )

    note_compact = compact(note_text)

    assert "転職後の初回の更新許可申請" in note_compact
    assert "提出資料１３は不要" in note_compact
    assert "提出書類１２" in note_compact

    print("\n[페이지 2 상단 조건]")
    print(note_text.strip())

    for page_number, config in ROW_BOUNDARIES.items():
        page = pdf[page_number - 1]
        boundaries = config["y"]
        numbers = config["numbers"]

        assert len(boundaries) == len(numbers) + 1

        words = page.get_text("words", sort=False)

        for index, number in enumerate(numbers):
            upper = boundaries[index] + 0.6
            lower = boundaries[index + 1] - 0.6

            # 전체 행 원문: 카테고리별 증빙이
            # 설명 열에 포함된 No.4도 보존
            row_clip = pymupdf.Rect(
                55, upper, 535, lower
            )

            row_text = page.get_text(
                "text",
                clip=row_clip,
                sort=True,
            ).strip()

            normalized = compact(row_text)

            assert row_text, f"No.{number} 원문 누락"

            for keyword in KEYWORDS[number]:
                assert keyword in normalized, (
                    f"No.{number} 핵심 문구 누락: {keyword}"
                )

            # 번호 열 좌표 확인
            number_words = [
                w for w in words
                if re.fullmatch(r"\d{1,2}", w[4].strip())
                and int(w[4]) == number
                and 35 <= w[0] <= 55
                and upper <= (w[1] + w[3]) / 2 <= lower
            ]

            assert len(number_words) == 1, (
                f"No.{number} 서류 번호 위치 이상"
            )

            symbols = []

            for category, center_x in CATEGORY_X.items():
                candidates = [
                    w[4].strip()
                    for w in words
                    if w[4].strip() in {"○", "△", "－"}
                    and abs(w[0] - center_x) <= 8
                    and upper <= (w[1] + w[3]) / 2 <= lower
                ]

                # No.4는 카테고리 증빙 문구 자체에
                # ○가 포함되므로 제출 기호를 판정하지 않음
                if number == 4:
                    symbol = None
                else:
                    assert len(candidates) <= 1, (
                        f"No.{number} Category {category} 기호 중복"
                    )
                    symbol = (
                        candidates[0] if candidates else None
                    )

                symbols.append(symbol)

            # No.4의 None은 제출 요건 없음이 아니라
            # 일반 기호 대신 별도 증빙 문구가 있는 상태
            assert tuple(symbols) == EXPECTED_SYMBOLS[number], (
                f"No.{number} 카테고리 기호 불일치: {symbols}"
            )

            validated.append(number)

            print("\n" + "=" * 55)
            print(f"Page {page_number} | No.{number:02d}")
            print(f"Y: {upper:.2f} ~ {lower:.2f}")

            if number == 4:
                print("제출 표시: 카테고리별 개별 증빙 문구")
            else:
                print(
                    "제출 표시:",
                    dict(zip(CATEGORY_X, symbols)),
                )

            print("추출 문자 수:", len(row_text))
            print("\n[행 원문]")
            print(row_text)

assert validated == list(range(1, 14))

print("\n===== STEP 63-74 최종 결과 =====")
print("검증 서류: 13개")
print("페이지별 서류 번호: 정상")
print("제출 기호: 검증 성공")
print("No.4 개별 카테고리 증빙: 별도 처리 유지")
print("페이지 2 추가 제출 조건: 확인")
print("PDF SHA-256: 일치")
print("파일 생성·수정: 없음")
print("정책 검증 상태: needs_review")