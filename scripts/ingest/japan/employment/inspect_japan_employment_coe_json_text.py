
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[4]

PROCESSED_DIR = ROOT / "data/processed/japan/employment"

FILES = [
    "japan_employment_coe_common_structured.json",
    "japan_employment_coe_category34_structured.json",
]

# 원문에 존재해야 하는 대표 문구
EXPECTED_KEYWORDS = {
    1: ["在留資格認定証明書交付申請書"],
    2: ["写真"],
    3: ["返信用封筒"],
    4: ["所属機関", "カテゴリー"],
    5: ["専門士"],
    6: ["派遣"],
    7: ["活動内容"],
    8: ["学歴", "職歴", "情報処理"],
    9: ["登記事項証明書"],
    10: ["事業内容"],
    11: ["決算文書"],
    12: ["代表者"],
    13: ["ＣＥＦＲ", "Ｂ２"],
    14: ["法定調書合計表"],
}

print("===== STEP 63-12 COE JSON 원문 검증 =====")

all_numbers = []
issues = []

for filename in FILES:
    path = PROCESSED_DIR / filename

    assert path.is_file(), f"JSON 누락: {filename}"

    dataset = json.loads(path.read_text(encoding="utf-8"))

    assert dataset["route_id"] == "JP-EM"
    assert dataset["application_type"] == "coe"

    print("\n" + "=" * 70)
    print("파일:", filename)
    print("서류 수:", len(dataset["documents"]))

    for row in dataset["documents"]:
        number = row["row_number"]
        text = row["raw_row_text_ja"]

        all_numbers.append(number)

        print("\n" + "-" * 60)
        print(f"No.{number:02d} / {row['document_id']}")
        print("원문 길이:", len(text))

        print("\n[저장된 일본어 원문]")
        print(text if text else "(비어 있음)")

        missing = [
            keyword
            for keyword in EXPECTED_KEYWORDS[number]
            if keyword not in text
        ]

        if missing:
            issues.append({
                "row_number": number,
                "missing_keywords": missing,
            })

            print("\n[검토 필요]")
            print("확인되지 않은 문구:", missing)
        else:
            print("\n대표 문구 검사: 통과")

print("\n" + "=" * 70)
print("===== 최종 검증 결과 =====")

assert sorted(all_numbers) == list(range(1, 15)), (
    "서류 번호 1~14 불일치"
)

print("서류 번호:", sorted(all_numbers))
print("전체 서류:", len(all_numbers))
print("대표 문구 검토 필요 항목:", len(issues))

for issue in issues:
    print(
        f"No.{issue['row_number']:02d}:",
        issue["missing_keywords"],
    )

print("\n참고: 대표 문구 검사는 원문 완전성을 보장하지 않습니다.")
print("파일 변경: 없음")
print("정책 검증 상태: needs_review")