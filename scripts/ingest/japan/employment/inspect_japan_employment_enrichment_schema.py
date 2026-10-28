
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
PROCESSED = ROOT / "data/processed/japan/employment"

FILES = {
    "common": {
        "filename": "japan_employment_coe_common_structured.json",
        "sha256": "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68",
        "document_id": "JP_EM_COE_DOC_004",
    },
    "category34": {
        "filename": "japan_employment_coe_category34_structured.json",
        "sha256": "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce",
        "document_id": "JP_EM_COE_DOC_008",
    },
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(value, indent=0, max_depth=5):
    prefix = " " * indent

    if indent // 2 >= max_depth:
        print(prefix + "...")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            print(f"{prefix}{key}: {type(item).__name__}")
            describe(item, indent + 2, max_depth)

    elif isinstance(value, list):
        print(f"{prefix}항목 수: {len(value)}")
        if value:
            print(prefix + "첫 번째 항목:")
            describe(value[0], indent + 2, max_depth)


print("===== STEP 63-34 상세 증빙 스키마 확인 =====")

for name, config in FILES.items():
    path = PROCESSED / config["filename"]

    assert path.is_file(), f"파일 누락: {path}"
    assert sha256(path) == config["sha256"], (
        f"SHA-256 불일치: {path.name}"
    )

    dataset = json.loads(path.read_text(encoding="utf-8"))

    row = next(
        item for item in dataset["documents"]
        if item["document_id"] == config["document_id"]
    )

    print("\n" + "=" * 65)
    print("대상:", config["document_id"])
    print("파일:", config["filename"])
    print("SHA-256: 일치")

    if name == "common":
        fields = [
            "category_evidence",
            "category_evidence_source",
            "category_evidence_notes",
            "category_evidence_options",
            "category_evidence_interpretation_status",
        ]

        for field in fields:
            assert field in row, f"필드 누락: {field}"

            print(f"\n[{field}]")
            describe(row[field])

        print("\n[카테고리별 증빙 선택지 전체]")
        for category, data in row["category_evidence_options"].items():
            print(f"Category {category}")
            for option in data["evidence_options"]:
                print(json.dumps(
                    option,
                    ensure_ascii=False,
                    indent=2,
                ))

    else:
        evidence = row["education_evidence"]

        print("\n[education_evidence 전체 필드 구조]")
        describe(evidence)

        print("\n[이력서]")
        print(json.dumps(
            evidence["resume"],
            ensure_ascii=False,
            indent=2,
        ))

        print("\n[대체 증빙 그룹 메타데이터]")
        group = evidence["alternative_group"]

        for key, value in group.items():
            if key != "options":
                print(
                    key,
                    json.dumps(value, ensure_ascii=False),
                )

        print("\n[대체 증빙 선택지별 메타데이터]")
        for option in group["options"]:
            summary = {
                key: value
                for key, value in option.items()
                if key not in {
                    "original_text_ja",
                    "clean_text_ja",
                }
            }

            print(json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
            ))

        print("\n[정제된 본문 및 기존 원문 길이]")
        for option in group["options"]:
            print(
                option["clause"],
                "원문:",
                len(option["original_text_ja"]),
                "정제:",
                len(option.get("clean_text_ja", "")),
            )

print("\n===== STEP 63-34 결과 =====")
print("상세 증빙 필드 구조 확인: 완료")
print("최종 JSON 변경: 없음")
print("재생성 스크립트 변경: 없음")
print("Git 커밋·푸시: 미실행")