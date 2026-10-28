
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

CONFIGS = [
    {
        "name": "공통 COE 제출서류",
        "filename": "japan_employment_coe_common_structured.json",
        "reproduced_dir": (
            "_local_backup/japan_employment_repro_exact_crlf"
        ),
        "expected_sha256": (
            "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68"
        ),
        "expected_count": 6,
        "enriched_document_id": "JP_EM_COE_DOC_004",
    },
    {
        "name": "카테고리 3·4 COE 제출서류",
        "filename": "japan_employment_coe_category34_structured.json",
        "reproduced_dir": (
            "_local_backup/japan_employment_repro_education"
        ),
        "expected_sha256": (
            "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce"
        ),
        "expected_count": 8,
        "enriched_document_id": "JP_EM_COE_DOC_008",
    },
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


print("===== STEP 63-39 COE 전체 재현성 통합 검증 =====")

all_ids = []
total_documents = 0

for config in CONFIGS:
    final_path = (
        ROOT
        / "data/processed/japan/employment"
        / config["filename"]
    )

    reproduced_path = (
        ROOT
        / config["reproduced_dir"]
        / config["filename"]
    )

    assert final_path.is_file(), (
        f"최종 JSON 누락: {final_path}"
    )
    assert reproduced_path.is_file(), (
        f"재생성 JSON 누락: {reproduced_path}"
    )

    expected = config["expected_sha256"]

    assert sha256(final_path) == expected, (
        f"최종 JSON SHA-256 불일치: {config['filename']}"
    )
    assert sha256(reproduced_path) == expected, (
        f"재생성 JSON SHA-256 불일치: {config['filename']}"
    )

    assert final_path.read_bytes() == reproduced_path.read_bytes(), (
        f"바이트 단위 불일치: {config['filename']}"
    )

    dataset = json.loads(final_path.read_text(encoding="utf-8"))

    assert dataset["route_id"] == "JP-EM"
    assert dataset["application_type"] == "coe"
    assert dataset["validation_status"] == "needs_review"

    documents = dataset["documents"]

    assert len(documents) == config["expected_count"]
    assert dataset["document_count"] == len(documents)

    ids = [row["document_id"] for row in documents]
    all_ids.extend(ids)
    total_documents += len(documents)

    enriched = next(
        row for row in documents
        if row["document_id"] == config["enriched_document_id"]
    )

    if config["expected_count"] == 6:
        assert "category_evidence" in enriched

        options = enriched["category_evidence_options"]
        assert {
            key: value["evidence_count"]
            for key, value in options.items()
        } == {"1": 4, "2": 2, "3": 1, "4": 0}

    else:
        assert "education_evidence" in enriched

        evidence = enriched["education_evidence"]
        options = evidence["alternative_group"]["options"]

        assert len(options) == 4

        work = next(
            item for item in options
            if item["clause"] == "イ"
        )

        assert "clean_text_ja" in work
        assert all(
            symbol not in work["clean_text_ja"]
            for symbol in ["○", "●", "△", "□"]
        )

    print(f"\n[{config['name']}]")
    print("제출서류:", len(documents))
    print("재생성 SHA-256:", sha256(reproduced_path))
    print("최종본 SHA-256:", sha256(final_path))
    print("바이트 단위 비교: 일치")

assert len(all_ids) == total_documents == 14
assert len(set(all_ids)) == 14

print("\n===== STEP 63-39 최종 결과 =====")
print("전체 제출서류:", total_documents)
print("중복 서류 ID: 없음")
print("상세 증빙 구조: 확인")
print("최종본과 재생성본: 2/2 완전 일치")
print("재현성 통합 검증: 성공")
print("기존 JSON 및 PDF 수정: 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")