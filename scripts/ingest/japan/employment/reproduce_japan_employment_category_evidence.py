
from pathlib import Path
import hashlib
import json
import os
import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"

DEFAULT_BASELINE = (
    ROOT / "_local_backup/japan_employment_repro_baseline"
)

DEFAULT_OUTPUT = (
    ROOT / "_local_backup/japan_employment_repro_enriched"
)

BASELINE = Path(
    os.environ.get(
        "JP_EM_COE_BASELINE_DIR",
        str(DEFAULT_BASELINE),
    )
).resolve()

OUTPUT_DIR = Path(
    os.environ.get(
        "JP_EM_COE_CATEGORY_OUTPUT_DIR",
        str(DEFAULT_OUTPUT),
    )
).resolve()

# 재현성 테스트는 _local_backup 안에서만 실행
SAFE_ROOT = (ROOT / "_local_backup").resolve()
PROCESSED = (
    ROOT / "data/processed/japan/employment"
).resolve()

assert SAFE_ROOT in BASELINE.parents, (
    "입력 경로는 _local_backup 하위여야 합니다."
)

assert SAFE_ROOT in OUTPUT_DIR.parents, (
    "출력 경로는 _local_backup 하위여야 합니다."
)

assert OUTPUT_DIR != BASELINE, (
    "입력과 출력 폴더가 같을 수 없습니다."
)

assert PROCESSED not in OUTPUT_DIR.parents, (
    "기존 processed 폴더에 출력할 수 없습니다."
)

FILENAME = "japan_employment_coe_common_structured.json"

SOURCE = BASELINE / FILENAME
OUTPUT = OUTPUT_DIR / FILENAME
PDF = RAW / "japan_employment_coe_pdfs/001404131.pdf"
HASHES = RAW / "japan_employment_coe_pdf_hashes.json"

EXPECTED_BASELINE_SHA = (
    "fd31b73d9ae74e6d9fc84ed68deb917d45e7e8f3945cdf6bf55dc4b288daa0a1"
)

EXPECTED_INTERMEDIATE_SHA = (
    "ac7791557493b9eacebeccef7ce87fdef3fb2ba10a979dc0959e57a9dbf04ebb"
)

COLUMNS = {
    "1": (216.5, 291.4),
    "2": (291.4, 366.3),
    "3": (366.3, 441.2),
    "4": (441.2, 516.1),
}

# 공식 PDF 원문에서 검증한 증빙자료 유형
EVIDENCE = {
    "1": [
        ("JP_EM_CAT1_E01", "상장기업 증빙",
         ["四季報", "証券取引所", "証明する文書"]),
        ("JP_EM_CAT1_E02", "주무관청 설립허가 증빙",
         ["主務官庁", "設立", "許可"]),
        ("JP_EM_CAT1_E03", "혁신창출기업 해당 증빙",
         ["高度専門職省令", "イノベーショ", "補助金交付"]),
        ("JP_EM_CAT1_E04", "일정 조건을 충족하는 기업 등의 증빙",
         ["一定の条件", "企業等", "認定証"]),
    ],
    "2": [
        ("JP_EM_CAT2_E01", "전년도 법정조서합계표 사본",
         ["前年分", "法定", "調書合計表"]),
        ("JP_EM_CAT2_E02", "재류신청 온라인 시스템 이용승인 증빙",
         ["在留申請オンライン", "利用申出", "承認"]),
    ],
    "3": [
        ("JP_EM_CAT3_E01", "전년도 법정조서합계표 사본",
         ["前年分", "法定", "調書合計表"]),
    ],
    "4": [],
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


print("===== STEP 63-35 카테고리 증빙 재현성 검증 =====")

for path in [SOURCE, PDF, HASHES]:
    assert path.is_file(), f"파일 누락: {path}"

assert not OUTPUT.exists(), "테스트 출력 파일이 이미 존재합니다"
assert sha256(SOURCE) == EXPECTED_BASELINE_SHA, (
    "기본 재생성 JSON SHA-256 불일치"
)

hash_data = json.loads(HASHES.read_text(encoding="utf-8"))
pdf_record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF.name
)

pdf_hash = sha256(PDF)
assert pdf_hash == pdf_record["sha256"], "PDF SHA-256 불일치"

dataset = json.loads(SOURCE.read_text(encoding="utf-8"))
assert dataset["route_id"] == "JP-EM"
assert dataset["document_count"] == 6

row = next(
    item for item in dataset["documents"]
    if item["document_id"] == "JP_EM_COE_DOC_004"
)

assert "category_evidence" not in row

# 1. PDF의 카테고리별 열에서 원문 재추출
category_evidence = {}

with pymupdf.open(PDF) as pdf:
    assert len(pdf) == 1
    page = pdf[0]

    for category, (left, right) in COLUMNS.items():
        clip = pymupdf.Rect(
            left, 330.96 + 0.5,
            right, 572.04 - 0.5,
        )

        original_text = page.get_text(
            "text",
            clip=clip,
            sort=True,
        ).strip()

        category_evidence[category] = {
            "original_text_ja": original_text,
            "source_cell_status": (
                "text_present" if original_text else "empty"
            ),
            "validation_status": "needs_review",
        }

assert "四季報" in category_evidence["1"]["original_text_ja"]
assert "在留申請オンライン" in category_evidence["2"]["original_text_ja"]
assert "法定調書合計表" in "".join(
    category_evidence["3"]["original_text_ja"].split()
)
assert category_evidence["4"]["original_text_ja"] == ""

# 2. 기존 STEP 63-18과 동일한 필드 순서로 구축
row["category_evidence"] = category_evidence

row["category_evidence_source"] = {
    "pdf_filename": PDF.name,
    "page": 1,
    "extraction_method": "pdf_column_coordinates",
    "source_sha256": pdf_hash,
}

row["category_evidence_notes"] = (
    "카테고리 4의 원문 공란은 제출서류 면제를 뜻하지 않음. "
    "카테고리 분류 및 제출 조건은 별도 검토 필요."
)

# 3. PDF 원문에 근거한 증빙 선택지 구축
options = {}
ids = []

for category in ["1", "2", "3", "4"]:
    source_text = "".join(
        category_evidence[category]["original_text_ja"].split()
    )

    category_options = []

    for evidence_id, name_ko, keywords in EVIDENCE[category]:
        for keyword in keywords:
            assert keyword in source_text, (
                f"근거 문구 누락: {category} / {keyword}"
            )

        category_options.append({
            "evidence_id": evidence_id,
            "name_ko": name_ko,
            "source_keywords_ja": keywords,
            "source_pdf": PDF.name,
            "validation_status": "needs_review",
        })
        ids.append(evidence_id)

    options[category] = {
        "evidence_count": len(category_options),
        "evidence_options": category_options,
        "validation_status": "needs_review",
    }

row["category_evidence_options"] = options
row["category_evidence_interpretation_status"] = "needs_review"

assert len(ids) == len(set(ids)) == 7

# 4. 테스트 폴더에만 저장
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("x", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

assert json.loads(OUTPUT.read_text(encoding="utf-8")) == dataset

actual_sha = sha256(OUTPUT)

print("입력:", SOURCE.relative_to(ROOT))
print("출력:", OUTPUT.relative_to(ROOT))
print("제출서류:", dataset["document_count"])
print("증빙 선택지:", len(ids))
print("PDF SHA-256: 일치")

print("\n[재현성 비교]")
print("재생성 SHA-256:", actual_sha)
print("중간 산출물 기대 SHA-256:", EXPECTED_INTERMEDIATE_SHA)
print(
    "중간 산출물 검증:",
    "성공" if actual_sha == EXPECTED_INTERMEDIATE_SHA else "불일치"
)
print("기존 processed JSON: 변경 없음")
print("정책 검증: needs_review")

# 결과가 다른 경우에는 후속 비교가 가능하도록 테스트 파일 유지
assert actual_sha == EXPECTED_INTERMEDIATE_SHA, (
    "중간 산출물 SHA-256이 예상 값과 다릅니다."
)

print("STEP 63-35 완료")