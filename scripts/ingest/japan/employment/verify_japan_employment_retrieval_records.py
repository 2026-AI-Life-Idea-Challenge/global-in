
from pathlib import Path
from collections import Counter
import json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

FILES = {
    "coe_common": "japan_employment_coe_common_structured.json",
    "coe_category34": "japan_employment_coe_category34_structured.json",
    "change": "japan_employment_change_integrated.json",
    "renewal": "japan_employment_renewal_integrated.json",
}

EVIDENCE_FIELDS = (
    "category_evidence",
    "education_evidence",
    "activity_evidence",
    "dispatch_evidence",
    "tax_evidence",
)

EXPECTED_COUNTS = {
    "coe_common": 6,
    "coe_category34": 8,
    "change": 8,
    "renewal": 13,
}

EXPECTED_CATEGORIES = {
    "coe_common": {"1", "2", "3", "4"},
    "coe_category34": {"3", "4"},
    "change": {"3", "4"},
    "renewal": {"1", "2", "3", "4"},
}

EXPECTED_EVIDENCE_COUNTS = {
    "coe_common": 1,
    "coe_category34": 1,
    "change": 3,
    "renewal": 4,
}

print("===== STEP 63-94 검색 레코드 구조 검증 =====")

records = []
all_ids = set()

for group, filename in FILES.items():
    path = BASE / filename
    assert path.is_file(), f"파일 누락: {filename}"

    dataset = json.loads(path.read_text(encoding="utf-8"))

    source = dataset["source"]
    documents = dataset["documents"]

    assert dataset["route_id"] == "JP-EM"
    assert dataset["validation_status"] == "needs_review"
    assert dataset["document_count"] == EXPECTED_COUNTS[group]
    assert len(documents) == EXPECTED_COUNTS[group]
    assert set(dataset["category_columns"]) == (
        EXPECTED_CATEGORIES[group]
    )

    for key in (
        "official_agency",
        "pdf_filename",
        "source_url",
        "source_sha256",
    ):
        assert source.get(key), f"{group}: 출처 필드 누락 {key}"

    evidence_count = 0

    for row in documents:
        document_id = row["document_id"]

        assert document_id not in all_ids, (
            f"중복 document_id: {document_id}"
        )
        all_ids.add(document_id)

        requirements = row["category_requirements"]
        assert set(requirements) == EXPECTED_CATEGORIES[group]

        for category, requirement in requirements.items():
            assert isinstance(requirement, dict)
            assert requirement.get("symbol") in (
                "○", "△", None
            ), (
                f"{document_id}: 확인되지 않은 제출 기호"
            )

        raw_text = row["raw_row_text_ja"]
        assert isinstance(raw_text, str) and raw_text.strip()

        page = row.get("page")
        assert isinstance(page, int) and page >= 1, (
            f"{document_id}: PDF 페이지 확인 필요"
        )

        evidence = {
            field: row[field]
            for field in EVIDENCE_FIELDS
            if field in row
        }

        if evidence:
            evidence_count += 1

        record = {
            "record_id": document_id,
            "route_id": dataset["route_id"],
            "program_id": dataset["program_id"],
            "application_type": dataset["application_type"],
            "dataset_group": group,
            "document_id": document_id,
            "source_document_filename": filename,
            "source_official_agency": source["official_agency"],
            "source_pdf_filename": source["pdf_filename"],
            "source_url": source["source_url"],
            "source_sha256": source["source_sha256"],
            "source_page": page,
            "category_requirements": requirements,
            "raw_text_ja": raw_text,
            "evidence": evidence,
            "validation_status": row["validation_status"],
            "automatic_eligibility_rules_enabled": False,
        }

        assert record["validation_status"] == "needs_review"

        records.append(record)

    assert evidence_count == EXPECTED_EVIDENCE_COUNTS[group]

    print(
        f"[PASS] {group}: "
        f"{len(documents)}개 문서 / "
        f"{evidence_count}개 상세 증빙"
    )

assert len(records) == 35
assert len(all_ids) == 35

by_group = Counter(
    record["dataset_group"]
    for record in records
)

assert dict(by_group) == EXPECTED_COUNTS

evidence_records = [
    record for record in records
    if record["evidence"]
]

assert len(evidence_records) == 9

assert all(
    record["validation_status"] == "needs_review"
    and record["automatic_eligibility_rules_enabled"] is False
    for record in records
)

print("\n[검색 레코드 필드]")
for key in records[0]:
    print("-", key)

print("\n===== STEP 63-94 최종 결과 =====")
print("검색 레코드:", len(records))
print("고유 문서 ID:", len(all_ids))
print("상세 증빙 연결 레코드:", len(evidence_records))
print("공식 출처 메타데이터: 유지")
print("Category별 원본 기호: 유지")
print("일본어 원문: 유지")
print("정책 검증 상태: needs_review")
print("자동 자격 판정: 비활성화")
print("벡터 임베딩 생성: 미실행")
print("DB 저장: 미실행")
print("기존 JSON 변경: 없음")
print("Git 커밋·푸시: 미실행")