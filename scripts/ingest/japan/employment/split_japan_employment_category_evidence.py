
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[4]

REVIEW_DIR = (
    ROOT / "_local_backup/japan_employment_category_evidence_review"
)

SOURCE_PATH = (
    REVIEW_DIR / "japan_employment_coe_common_structured.json"
)

OUTPUT_PATH = (
    REVIEW_DIR / "japan_employment_coe_common_evidence_split.json"
)

# STEP 63-17에서 확인한 공식 PDF의 카테고리별 문구
# 항목은 PDF 열 순서대로 기록한다.
EVIDENCE = {
    "1": [
        {
            "id": "JP_EM_CAT1_E01",
            "name_ko": "상장기업 증빙",
            "keywords_ja": ["四季報", "証券取引所", "証明する文書"],
        },
        {
            "id": "JP_EM_CAT1_E02",
            "name_ko": "주무관청 설립허가 증빙",
            "keywords_ja": ["主務官庁", "設立", "許可"],
        },
        {
            "id": "JP_EM_CAT1_E03",
            "name_ko": "혁신창출기업 해당 증빙",
            "keywords_ja": ["高度専門職省令", "イノベーショ", "補助金交付"],
        },
        {
            "id": "JP_EM_CAT1_E04",
            "name_ko": "일정 조건을 충족하는 기업 등의 증빙",
            "keywords_ja": ["一定の条件", "企業等", "認定証"],
        },
    ],
    "2": [
        {
            "id": "JP_EM_CAT2_E01",
            "name_ko": "전년도 법정조서합계표 사본",
            "keywords_ja": ["前年分", "法定", "調書合計表"],
        },
        {
            "id": "JP_EM_CAT2_E02",
            "name_ko": "재류신청 온라인 시스템 이용승인 증빙",
            "keywords_ja": ["在留申請オンライン", "利用申出", "承認"],
        },
    ],
    "3": [
        {
            "id": "JP_EM_CAT3_E01",
            "name_ko": "전년도 법정조서합계표 사본",
            "keywords_ja": ["前年分", "法定", "調書合計表"],
        },
    ],
    "4": [],
}

print("===== STEP 63-19 카테고리별 증빙 선택지 분리 =====")

assert SOURCE_PATH.is_file(), "STEP 63-18 수정 후보가 없습니다."
assert not OUTPUT_PATH.exists(), "출력 파일이 이미 존재합니다."

dataset = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

assert dataset["route_id"] == "JP-EM"
assert dataset["document_count"] == 6

row = next(
    item for item in dataset["documents"]
    if item["document_id"] == "JP_EM_COE_DOC_004"
)

assert "category_evidence" in row
assert "category_evidence_options" not in row

options = {}
all_ids = []

for category in ["1", "2", "3", "4"]:
    source = row["category_evidence"][category]
    normalized = re.sub(r"\s+", "", source["original_text_ja"])

    category_options = []

    for item in EVIDENCE[category]:
        missing = [
            keyword
            for keyword in item["keywords_ja"]
            if keyword not in normalized
        ]

        assert not missing, (
            f"Category {category}, {item['id']} "
            f"근거 문구 누락: {missing}"
        )

        category_options.append({
            "evidence_id": item["id"],
            "name_ko": item["name_ko"],
            "source_keywords_ja": item["keywords_ja"],
            "source_pdf": "001404131.pdf",
            "validation_status": "needs_review",
        })

        all_ids.append(item["id"])

    if category == "4":
        assert source["original_text_ja"] == ""

    options[category] = {
        "evidence_count": len(category_options),
        "evidence_options": category_options,
        "validation_status": "needs_review",
    }

    print(
        f"Category {category}:",
        len(category_options),
        "개"
    )

row["category_evidence_options"] = options
row["category_evidence_interpretation_status"] = "needs_review"

assert len(all_ids) == 7
assert len(set(all_ids)) == 7

# 기존 후보는 변경하지 않고 별도 파일에 저장
with OUTPUT_PATH.open("x", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

saved = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
assert saved == dataset

print("\n===== 최종 검증 =====")
print("증빙 선택지 총합:", len(all_ids))
print("고유 증빙 ID:", len(set(all_ids)))
print("근거 키워드 검사: 성공")
print("출력 파일:", OUTPUT_PATH.relative_to(ROOT))
print("기존 processed JSON: 변경 없음")
print("기존 수정 후보 JSON: 변경 없음")
print("정책 검증 상태: needs_review")