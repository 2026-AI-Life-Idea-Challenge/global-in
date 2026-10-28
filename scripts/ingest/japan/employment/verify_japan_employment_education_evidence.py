
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"
REVIEW = ROOT / "_local_backup/japan_employment_education_review"

FILENAME = "japan_employment_coe_category34_structured.json"

CURRENT_PATH = PROCESSED / FILENAME
CANDIDATE_PATH = REVIEW / FILENAME
PDF_PATH = RAW / "japan_employment_coe_pdfs/001437254.pdf"
HASH_PATH = RAW / "japan_employment_coe_pdf_hashes.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text):
    return "".join(text.split())


print("===== STEP 63-24 학력·경력 증빙 최종 후보 검증 =====")

# 1. 파일 존재 확인
for path in [
    CURRENT_PATH,
    CANDIDATE_PATH,
    PDF_PATH,
    HASH_PATH,
]:
    assert path.is_file(), f"파일 누락: {path}"

current = json.loads(
    CURRENT_PATH.read_text(encoding="utf-8")
)

candidate = json.loads(
    CANDIDATE_PATH.read_text(encoding="utf-8")
)

# 2. 상위 메타데이터 불변 확인
current_meta = {
    k: v for k, v in current.items()
    if k != "documents"
}

candidate_meta = {
    k: v for k, v in candidate.items()
    if k != "documents"
}

assert current_meta == candidate_meta, (
    "상위 메타데이터 변경 발견"
)

assert current["route_id"] == "JP-EM"
assert current["application_type"] == "coe"
assert current["document_count"] == 8
assert len(current["documents"]) == 8
assert len(candidate["documents"]) == 8

# 3. 8번 이외의 서류는 완전히 동일해야 함
for old, new in zip(
    current["documents"],
    candidate["documents"],
):
    assert old["row_number"] == new["row_number"]
    assert old["document_id"] == new["document_id"]

    if old["row_number"] != 8:
        assert old == new, (
            f"No.{old['row_number']:02d} 변경 발견"
        )
    else:
        assert "education_evidence" not in old

        new_without_added = {
            k: v for k, v in new.items()
            if k != "education_evidence"
        }

        assert new_without_added == old, (
            "8번 서류의 기존 데이터가 변경됨"
        )

old_row8 = next(
    row for row in current["documents"]
    if row["row_number"] == 8
)

new_row8 = next(
    row for row in candidate["documents"]
    if row["row_number"] == 8
)

assert set(new_row8) - set(old_row8) == {
    "education_evidence"
}

# 4. 증빙 구조 검증
evidence = new_row8["education_evidence"]
resume = evidence["resume"]
group = evidence["alternative_group"]
options = group["options"]

assert resume["evidence_id"] == (
    "JP_EM_COE_DOC_008_RESUME"
)

assert group["group_id"] == (
    "JP_EM_COE_DOC_008_ALTERNATIVES"
)

assert group["source_relation"] == "いずれか"
assert len(options) == 4

expected_clauses = ["ア", "イ", "ウ", "エ"]

assert [
    item["clause"] for item in options
] == expected_clauses

all_ids = [resume["evidence_id"]] + [
    item["evidence_id"] for item in options
]

assert len(set(all_ids)) == 5, (
    "증빙자료 ID 중복"
)

# 5. 일본어 원문 포함 여부
original_normalized = normalize(
    old_row8["raw_row_text_ja"]
)

# PDF 표의 행 번호 '8'이 경력 증빙 문장에 혼입된 현상
# 원본 JSON은 수정하지 않고 검증용 문자열에서만 제거
assert original_normalized.count("高等8専門学校") == 1, (
    "예상한 PDF 행 번호 혼입 위치가 달라졌습니다."
)

original_normalized = original_normalized.replace(
    "高等8専門学校",
    "高等専門学校",
    1,
)

texts = [
    resume["original_text_ja"],
    group["intro_original_ja"],
] + [
    item["original_text_ja"] for item in options
]

labels = [
    "이력서 (1)",
    "대체 증빙 안내 (2)",
    "학력 증빙 ア",
    "경력 증빙 イ",
    "IT 자격 ウ",
    "국제업무 경력 エ",
]

mismatches = []

for label, text in zip(labels, texts):
    assert text.strip(), f"{label}: 원문이 비어 있습니다."

    normalized_text = normalize(text)
    matched = normalized_text in original_normalized

    print(f"{label}: {'일치' if matched else '불일치'}")

    if not matched:
        mismatches.append(label)
        print("  구조화 원문:", repr(normalized_text[:250]))

        # 차이가 단순히 행 번호 8 때문인지 확인
        without_row_number = original_normalized.replace(
            "高等8専門学校",
            "高等専門学校",
        )

        print(
            "  PDF 행 번호 제거 시:",
            "일치" if normalized_text in without_row_number
            else "불일치",
        )

assert not mismatches, (
    f"원문 불일치 조항: {mismatches}"
)

# 6. 예외 조항 검사
exceptions = [
    item for item in options
    if "exception_original_ja" in item
]

assert len(exceptions) == 2
assert {item["clause"] for item in exceptions} == {
    "ウ", "エ"
}

for item in exceptions:
    exception = normalize(
        item["exception_original_ja"]
    )

    assert exception in normalize(
        item["original_text_ja"]
    ), f"{item['clause']} 예외 문구 불일치"

    assert item["exception_interpretation_status"] == (
        "needs_review"
    )

# 7. PDF 원본 SHA-256 검증
hash_data = json.loads(
    HASH_PATH.read_text(encoding="utf-8")
)

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

pdf_hash = sha256(PDF_PATH)

assert pdf_hash == record["sha256"]
assert pdf_hash == evidence["source_sha256"]
assert pdf_hash == candidate["source"]["source_sha256"]

# 8. 최종 출력
print("기존 제출서류:", len(current["documents"]))
print("8번 외 변경된 서류: 없음")
print("기존 제출 기호 및 메타데이터: 동일")
print("이력서 조항:", 1)
print("대체 증빙:", len(options))
print("명시적 예외:", len(exceptions))
print("증빙 ID 중복: 없음")
print("일본어 원문 연결: 성공")
print("PDF SHA-256: 일치")

print("\n[JSON SHA-256]")
print("현재 JSON:", sha256(CURRENT_PATH))
print("후보 JSON:", sha256(CANDIDATE_PATH))

print("\n최종 후보 검증: 성공")
print("기존 파일 수정: 없음")
print("정책 검증 상태: needs_review")