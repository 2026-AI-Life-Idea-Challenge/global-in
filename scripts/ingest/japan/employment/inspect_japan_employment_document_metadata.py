
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

EVIDENCE_FIELDS = {
    "category_evidence",
    "education_evidence",
    "activity_evidence",
    "dispatch_evidence",
    "tax_evidence",
}

print("===== STEP 63-93 문서 메타데이터 점검 =====")

for name, filename in FILES.items():
    path = BASE / filename

    assert path.is_file(), f"파일 없음: {path}"

    data = json.loads(path.read_text(encoding="utf-8"))
    source = data.get("source", {})
    documents = data.get("documents", [])

    print(f"\n===== {name} =====")
    print("파일명:", filename)
    print("신청 유형:", data.get("application_type"))
    print("제출서류 개수:", len(documents))

    print("\n[공식 출처]")
    print("기관:", source.get("official_agency"))
    print("PDF:", source.get("pdf_filename"))
    print("URL:", source.get("source_url"))
    print("SHA-256:", source.get("source_sha256"))

    print("\n[Category 정의]")
    print("category_columns:", data.get("category_columns"))

    print("\n[Category 기호 분포]")
    symbol_counts = {}

    for row in documents:
        requirements = row.get("category_requirements", {})

        for category, requirement in requirements.items():
            symbol = (
                requirement.get("symbol")
                if isinstance(requirement, dict)
                else requirement
            )

            key = str(category)

            if key not in symbol_counts:
                symbol_counts[key] = Counter()

            symbol_counts[key][
                repr(symbol)
            ] += 1

    for category in sorted(symbol_counts):
        print(
            f"Category {category}:",
            dict(symbol_counts[category])
        )

    print("\n[상세 증빙 연결]")
    evidence_count = 0

    for row in documents:
        present = sorted(
            key for key in EVIDENCE_FIELDS
            if key in row
        )

        if present:
            evidence_count += 1
            print(
                row.get("document_id"),
                "->",
                ", ".join(present)
            )

    print("상세 증빙 연결 서류 수:", evidence_count)

    print("\n[검증 상태]")
    statuses = Counter(
        row.get("validation_status", "MISSING")
        for row in documents
    )

    print("문서별 상태:", dict(statuses))
    print("전체 데이터 상태:", data.get("validation_status"))

print("\n===== STEP 63-93 점검 완료 =====")
print("파일 생성·수정: 없음")
print("정책 해석·자동 판정: 수행하지 않음")
print("Git 커밋·푸시: 미실행")