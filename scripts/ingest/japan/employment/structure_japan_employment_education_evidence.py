
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"
REVIEW = ROOT / "_local_backup/japan_employment_education_review"

SOURCE = PROCESSED / "japan_employment_coe_category34_structured.json"
OUTPUT = REVIEW / "japan_employment_coe_category34_structured.json"
HASH_PATH = RAW / "japan_employment_coe_pdf_hashes.json"
PDF_PATH = RAW / "japan_employment_coe_pdfs/001437254.pdf"

print("===== STEP 63-23 학력·경력 증빙 구조화 =====")

assert SOURCE.is_file(), "기존 JSON 누락"
assert PDF_PATH.is_file(), "PDF 원본 누락"
assert HASH_PATH.is_file(), "PDF 해시 기록 누락"
assert not OUTPUT.exists(), "수정 후보가 이미 존재합니다"

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))
record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

pdf_hash = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
assert pdf_hash == record["sha256"], "PDF SHA-256 불일치"

dataset = json.loads(SOURCE.read_text(encoding="utf-8"))
assert dataset["route_id"] == "JP-EM"
assert dataset["document_count"] == 8

row = next(
    item for item in dataset["documents"]
    if item["document_id"] == "JP_EM_COE_DOC_008"
)

assert "education_evidence" not in row

original = row["raw_row_text_ja"]
lines = original.splitlines()

# 공식 PDF의 (1), (2), ア, イ, ウ, エ 구분자를 사용
sections = {
    "resume": [],
    "alternatives_intro": [],
    "a": [],
    "b": [],
    "c": [],
    "d": [],
}

current = None
found_markers = []

for line in lines:
    stripped = line.strip()

    # PDF의 서류 번호 8은 실제 조항이 아니므로 별도 제거
    cleaned = re.sub(r"^8\s+", "", stripped)

    if cleaned.startswith("（１）"):
        current = "resume"
        found_markers.append("1")

    elif cleaned.startswith("（２）"):
        current = "alternatives_intro"
        found_markers.append("2")

    else:
        match = re.match(
            r"^([アイウエ])[\s　]+",
            cleaned,
        )
        if match:
            letter = match.group(1)
            current = {
                "ア": "a",
                "イ": "b",
                "ウ": "c",
                "エ": "d",
            }[letter]
            found_markers.append(letter)

    if current is not None:
        sections[current].append(cleaned)

expected_markers = ["1", "2", "ア", "イ", "ウ", "エ"]
assert found_markers == expected_markers, (
    f"조항 식별 실패: {found_markers}"
)

section_text = {
    key: "\n".join(value).strip()
    for key, value in sections.items()
}

# 각 조항에 올바른 원문이 연결됐는지 검사
checks = {
    "resume": ["履歴書"],
    "alternatives_intro": ["いずれか"],
    "a": ["卒業証明書", "DOEACC"],
    "b": ["在職証明書", "期間"],
    "c": ["情報処理", "５の資料"],
    "d": ["３年以上", "翻訳・通訳"],
}

for key, keywords in checks.items():
    normalized = "".join(section_text[key].split())

    for keyword in keywords:
        assert keyword in normalized, (
            f"{key} 조항의 원문 누락: {keyword}"
        )

# 저장할 증빙자료 구성
evidence = {
    "resume": {
        "evidence_id": "JP_EM_COE_DOC_008_RESUME",
        "original_text_ja": section_text["resume"],
        "role": "separate_document_group",
        "validation_status": "needs_review",
    },
    "alternative_group": {
        "group_id": "JP_EM_COE_DOC_008_ALTERNATIVES",
        "intro_original_ja": section_text["alternatives_intro"],
        "source_relation": "いずれか",
        "application_note": (
            "공식 PDF의 대체 증빙 목록. "
            "각 조항의 적용 조건과 예외는 별도 판단 필요."
        ),
        "options": [
            {
                "evidence_id": "JP_EM_COE_DOC_008_A",
                "clause": "ア",
                "type": "education",
                "original_text_ja": section_text["a"],
            },
            {
                "evidence_id": "JP_EM_COE_DOC_008_B",
                "clause": "イ",
                "type": "work_experience",
                "original_text_ja": section_text["b"],
            },
            {
                "evidence_id": "JP_EM_COE_DOC_008_C",
                "clause": "ウ",
                "type": "designated_it_exam_or_qualification",
                "original_text_ja": section_text["c"],
                "exception_original_ja": (
                    "※５の資料を提出している場合は不要"
                ),
                "exception_target": "document_5",
                "exception_interpretation_status": "needs_review",
            },
            {
                "evidence_id": "JP_EM_COE_DOC_008_D",
                "clause": "エ",
                "type": "international_services_experience",
                "original_text_ja": section_text["d"],
                "exception_original_ja": (
                    "大学を卒業した者が翻訳・通訳又は"
                    "語学の指導に従事する場合を除く"
                ),
                "exception_interpretation_status": "needs_review",
            },
        ],
        "validation_status": "needs_review",
    },
    "source_pdf": PDF_PATH.name,
    "source_sha256": pdf_hash,
    "validation_status": "needs_review",
}

# 예외 문구가 실제 조항의 원문에 포함되는지 검증
for option in evidence["alternative_group"]["options"]:
    exception = option.get("exception_original_ja")
    if exception:
        normalized = "".join(option["original_text_ja"].split())
        assert exception in normalized, (
            f"{option['clause']} 예외 원문 불일치"
        )

row["education_evidence"] = evidence

REVIEW.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("x", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

saved = json.loads(OUTPUT.read_text(encoding="utf-8"))
assert saved == dataset, "저장 검증 실패"

print("서류 ID:", row["document_id"])
print("이력서 조항:", len(section_text["resume"]), "자")
print(
    "대체 증빙:",
    len(evidence["alternative_group"]["options"]),
    "개",
)
print("조항 구분:", found_markers)
print("IT 자격 예외:", "확인")
print("국제업무 경력 예외:", "확인")
print("원본 PDF SHA-256:", "일치")
print("수정 후보:", OUTPUT.relative_to(ROOT))
print("기존 processed JSON:", "변경 없음")
print("정책 검증:", "needs_review")
print("STEP 63-23 완료")