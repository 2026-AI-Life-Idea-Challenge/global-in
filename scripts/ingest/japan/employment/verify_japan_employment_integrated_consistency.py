
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

FILES = {
    "change": "japan_employment_change_integrated.json",
    "renewal": "japan_employment_renewal_integrated.json",
}

RENEWAL_SHA = (
    "b6ddc5500f9f5c51f62ea329bd0dfa04"
    "cb7e7a6c5710eb6fa98fd1bd92a94ffc"
)

SOURCE_FILES = {
    "main": (
        "japan_employment_renewal_structured.json",
        "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef",
    ),
    "category": (
        "japan_employment_renewal_category_evidence.json",
        "27db1ad63a15ba5b2c4a0e9946983ffd6656fef7e21b58d5b5152e3240317b7a",
    ),
    "dispatch": (
        "japan_employment_renewal_dispatch_evidence.json",
        "3f735ab9b7c7c9581c38e83e0a176c321cebe6e413575a1b661e75e9c7691df5",
    ),
    "activity": (
        "japan_employment_renewal_activity_evidence.json",
        "67421741ccb63c4a3b5dd105588cba5479353ef9c9c0037d8fedadd981d153db",
    ),
    "tax": (
        "japan_employment_renewal_tax_evidence.json",
        "f48361c0db679f78c276e4a3cf7da0d48ddf8f87d6d83c204ff83ed551036447",
    ),
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def load_json(path):
    assert path.is_file(), f"파일 누락: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


print("===== STEP 63-84 통합 JSON 정합성 검증 =====")

# 1. 전체 검사 대상의 최초 바이트 해시 기록
paths = {
    name: BASE / filename
    for name, filename in FILES.items()
}

paths.update({
    f"source_{key}": BASE / filename
    for key, (filename, _) in SOURCE_FILES.items()
})

baseline = {}

for name, path in paths.items():
    assert path.is_file(), f"파일 누락: {path}"
    baseline[name] = sha256(path.read_bytes())

assert baseline["renewal"] == RENEWAL_SHA
print("[PASS] Renewal 통합 JSON SHA-256")

# 2. 기존 입력 JSON 해시 검증
sources = {}

for key, (filename, expected_sha) in SOURCE_FILES.items():
    assert baseline[f"source_{key}"] == expected_sha, (
        f"입력 해시 불일치: {filename}"
    )
    sources[key] = load_json(BASE / filename)

print("[PASS] Renewal 입력 JSON 5개 SHA-256")

# 3. Change / Renewal 공통 스키마 검증
datasets = {
    name: load_json(path)
    for name, path in (
        (key, paths[key]) for key in FILES
    )
}

COMMON_KEYS = {
    "route_id",
    "program_id",
    "application_type",
    "document_count",
    "documents",
    "integration_sources",
    "validation_status",
    "automatic_eligibility_rules_enabled",
}


EXPECTED = {
    "change": {
        "count": 8,
        "numbers": list(range(7, 15)),
        "prefix": "JP_EM_CHANGE_DOC_",
        "categories": {"3", "4"},
    },
    "renewal": {
        "count": 13,
        "numbers": list(range(1, 14)),
        "prefix": "JP_EM_RENEWAL_DOC_",
        "categories": {"1", "2", "3", "4"},
    },
}

for name, dataset in datasets.items():
    config = EXPECTED[name]

    assert COMMON_KEYS <= set(dataset)
    assert dataset["route_id"] == "JP-EM"
    assert dataset["program_id"] == "JP-EM-01"
    assert dataset["application_type"] == name
    assert dataset["validation_status"] == "needs_review"
    assert dataset["automatic_eligibility_rules_enabled"] is False

    rows = dataset["documents"]

    assert dataset["document_count"] == len(rows)
    assert len(rows) == config["count"]

    assert [r["row_number"] for r in rows] == config["numbers"]

    assert all(
        r["document_id"] ==
        f'{config["prefix"]}{r["row_number"]:03d}'
        for r in rows
    )

    assert len({r["document_id"] for r in rows}) == len(rows)
    # 제출서류별 공통 스키마 상세 진단
    errors = []

    for row in rows:
        doc_id = row.get("document_id", "UNKNOWN")

        if not row.get("raw_row_text_ja"):
            errors.append(
                f"{doc_id}: raw_row_text_ja 누락 또는 빈 값"
            )

        if row.get("validation_status") != "needs_review":
            errors.append(
                f"{doc_id}: validation_status 불일치 "
                f"({row.get('validation_status')!r})"
            )

        categories = row.get("category_requirements")

        if not isinstance(categories, dict):
            errors.append(
                f"{doc_id}: category_requirements 누락 또는 형식 오류"
            )
        elif set(categories) != config["categories"]:
            errors.append(
                f"{doc_id}: Category 키 불일치 "
                f"({list(categories.keys())})"
            )

    if errors:
        print(f"\n[FAIL] {name}: {len(errors)}건의 스키마 불일치")

        for error in errors:
            print(" -", error)

        raise AssertionError(
            f"{name} 공통 스키마 검증 실패"
        )

    assert len(dataset["integration_sources"]) == (
        4 if name == "change" else 5
    )

    print(f"[PASS] {name}: 공통 스키마 및 서류 ID")

# 4. Renewal 통합 출처 확인
renewal = datasets["renewal"]
rows = {
    row["row_number"]: row
    for row in renewal["documents"]
}

expected_sources = [
    {
        "role": key,
        "filename": filename,
        "sha256": expected_sha,
    }
    for key, (filename, expected_sha) in SOURCE_FILES.items()
]

assert renewal["integration_sources"] == expected_sources

# 5. 세부 증빙 데이터가 원본과 일치하는지 확인
category = rows[4]["category_evidence"]
assert category["category_evidence"] == (
    sources["category"]["category_evidence"]
)
assert category["selection_type"] == (
    sources["category"]["selection_type"]
)

dispatch = rows[5]["dispatch_evidence"]
assert dispatch["pledge_documents"] == (
    sources["dispatch"]["pledge_documents"]
)
assert dispatch["dispatch_activity_documents"] == (
    sources["dispatch"]["dispatch_activity_documents"]
)

activity = rows[8]["activity_evidence"]
assert activity["options"] == sources["activity"]["options"]
assert activity["selection_type"] == (
    sources["activity"]["selection_type"]
)

tax = rows[13]["tax_evidence"]
assert tax["branches"] == sources["tax"]["branches"]
assert tax["branch_count"] == 2

print("[PASS] Renewal 증빙 구조 4/4 원본 일치")

# 6. 기존 부모 서류 정보 보존 확인
original = sources["main"]

for original_row, integrated_row in zip(
    original["documents"], renewal["documents"]
):
    assert all(
        integrated_row.get(key) == value
        for key, value in original_row.items()
    ), f'부모 서류 변경: {original_row["document_id"]}'

assert renewal["additional_submission_note_ja"] == (
    original["additional_submission_note_ja"]
)

assert rows[12]["category_requirements"]["3"]["symbol"] == "△"
assert rows[12]["category_requirements"]["4"]["symbol"] == "△"
assert rows[13]["category_requirements"]["3"]["symbol"] is None
assert rows[13]["category_requirements"]["4"]["symbol"] == "○"

print("[PASS] 원본 서류·Category·주석 보존")

# 7. 모든 입력 파일 불변성 최종 확인
for name, path in paths.items():
    assert sha256(path.read_bytes()) == baseline[name], (
        f"검증 중 파일 변경 감지: {path}"
    )

print("[PASS] 전체 검사 대상 파일 불변")

print("\n===== STEP 63-84 최종 결과 =====")
print("Change 제출서류:", len(datasets["change"]["documents"]))
print("Renewal 제출서류:", len(renewal["documents"]))
print("Renewal 증빙 연결 검증: 4/4")
print("Renewal 입력 SHA-256: 5/5")
print("통합 JSON 공통 스키마: PASS")
print("부모 서류 및 원문 보존: PASS")
print("검사 대상 파일 변경: 없음")
print("자동 자격 판정: 비활성화")
print("정책 검증 상태: needs_review")
print("파일 저장·수정: 없음")
print("Git 커밋·푸시: 미실행")