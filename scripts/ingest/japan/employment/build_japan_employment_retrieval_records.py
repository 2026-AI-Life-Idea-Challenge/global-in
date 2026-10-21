
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

OUTPUT = BASE / "japan_employment_retrieval_records.jsonl"

FILES = [
    (
        "coe_common",
        "japan_employment_coe_common_structured.json",
        6,
        {"1", "2", "3", "4"},
        1,
    ),
    (
        "coe_category34",
        "japan_employment_coe_category34_structured.json",
        8,
        {"3", "4"},
        1,
    ),
    (
        "change",
        "japan_employment_change_integrated.json",
        8,
        {"3", "4"},
        3,
    ),
    (
        "renewal",
        "japan_employment_renewal_integrated.json",
        13,
        {"1", "2", "3", "4"},
        4,
    ),
]

EVIDENCE_FIELDS = (
    "category_evidence",
    "education_evidence",
    "activity_evidence",
    "dispatch_evidence",
    "tax_evidence",
)

SOURCE_FIELDS = (
    "official_agency",
    "pdf_filename",
    "source_url",
    "source_sha256",
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


print("===== STEP 63-95 검색 레코드 생성 =====")

# 기존 결과물 덮어쓰기 방지
assert not OUTPUT.exists(), (
    f"출력 파일이 이미 존재합니다: {OUTPUT}"
)

records = []
source_hashes = {}
seen_ids = set()

for group, filename, expected_count, categories, expected_evidence in FILES:
    path = BASE / filename
    assert path.is_file(), f"입력 파일 누락: {filename}"

    raw = path.read_bytes()
    source_hashes[filename] = sha256_bytes(raw)

    dataset = json.loads(raw.decode("utf-8"))

    assert dataset["route_id"] == "JP-EM"
    assert dataset["program_id"] == "JP-EM-01"
    assert dataset["validation_status"] == "needs_review"
    assert set(dataset["category_columns"]) == categories

    documents = dataset["documents"]
    assert dataset["document_count"] == len(documents)
    assert len(documents) == expected_count

    source = dataset["source"]
    assert all(source.get(k) for k in SOURCE_FIELDS)

    evidence_count = 0

    for row in documents:
        document_id = row["document_id"]

        assert document_id not in seen_ids, (
            f"중복 문서 ID: {document_id}"
        )
        seen_ids.add(document_id)

        requirements = row["category_requirements"]
        assert set(requirements) == categories

        for requirement in requirements.values():
            assert isinstance(requirement, dict)
            assert requirement.get("symbol") in ("○", "△", None)

        raw_text = row["raw_row_text_ja"]
        assert isinstance(raw_text, str) and raw_text.strip()

        page = row["page"]
        assert isinstance(page, int) and page >= 1

        assert row["validation_status"] == "needs_review"

        evidence = {
            key: row[key]
            for key in EVIDENCE_FIELDS
            if key in row
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
            "source_document_sha256": source_hashes[filename],
            "source_official_agency": source["official_agency"],
            "source_pdf_filename": source["pdf_filename"],
            "source_url": source["source_url"],
            "source_sha256": source["source_sha256"],
            "source_page": page,
            "category_requirements": requirements,
            "raw_text_ja": raw_text,
            "evidence": evidence,
            "validation_status": "needs_review",
            "automatic_eligibility_rules_enabled": False,
        }

        records.append(record)

    assert evidence_count == expected_evidence

    print(
        f"[PASS] {group}: {len(documents)}개 / "
        f"상세 증빙 {evidence_count}개"
    )

# 저장 전 최종 구조 검증
assert len(records) == 35
assert len(seen_ids) == 35

counts = Counter(r["dataset_group"] for r in records)
assert dict(counts) == {
    "coe_common": 6,
    "coe_category34": 8,
    "change": 8,
    "renewal": 13,
}

assert sum(bool(r["evidence"]) for r in records) == 9

assert all(
    r["validation_status"] == "needs_review"
    and r["automatic_eligibility_rules_enabled"] is False
    for r in records
)

# JSONL: UTF-8, 줄바꿈 LF 고정
lines = [
    json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    for record in records
]

output_bytes = (
    "\n".join(lines) + "\n"
).encode("utf-8")

# 기존 파일이 있으면 저장하지 않음
with OUTPUT.open("xb") as f:
    f.write(output_bytes)

# 저장 결과 확인
saved_bytes = OUTPUT.read_bytes()

assert saved_bytes == output_bytes
assert saved_bytes.count(b"\n") == 35

saved_records = [
    json.loads(line)
    for line in saved_bytes.decode("utf-8").splitlines()
]

assert saved_records == records

# 입력 불변성 확인
for filename, original_sha in source_hashes.items():
    assert sha256_bytes((BASE / filename).read_bytes()) == original_sha

print("\n===== STEP 63-95 최종 결과 =====")
print("신청 유형: COE / Change / Renewal")
print("전체 검색 레코드:", len(saved_records))
print("고유 문서 ID:", len(seen_ids))
print("상세 증빙 연결 레코드: 9")
print("원본 JSON 입력: 4개")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", sha256_bytes(saved_bytes))
print("UTF-8 / LF 형식: PASS")
print("입력 JSON 변경: 없음")
print("정책 검증 상태: needs_review")
print("자동 자격 판정: 비활성화")
print("임베딩 생성·DB 저장: 미실행")
print("Git 커밋·푸시: 미실행")