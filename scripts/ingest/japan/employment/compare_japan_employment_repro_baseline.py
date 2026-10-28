
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

BASELINE_DIR = (
    ROOT / "_local_backup/japan_employment_repro_baseline"
)

FINAL_DIR = ROOT / "data/processed/japan/employment"

EXPECTED_FINAL_HASHES = {
    "japan_employment_coe_common_structured.json":
        "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68",
    "japan_employment_coe_category34_structured.json":
        "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


print("===== STEP 63-33 재생성 데이터 비교 =====")

total_rows = 0
total_mismatches = 0
total_extra_fields = 0

for filename, expected_sha in EXPECTED_FINAL_HASHES.items():
    baseline_path = BASELINE_DIR / filename
    final_path = FINAL_DIR / filename

    assert baseline_path.is_file(), (
        f"재생성 파일 누락: {filename}"
    )
    assert final_path.is_file(), (
        f"최종 JSON 누락: {filename}"
    )

    assert sha256(final_path) == expected_sha, (
        f"최종 JSON SHA-256 불일치: {filename}"
    )

    baseline = load_json(baseline_path)
    final = load_json(final_path)

    assert baseline["route_id"] == final["route_id"] == "JP-EM"

    assert baseline["document_count"] == final["document_count"]
    assert len(baseline["documents"]) == len(final["documents"])

    # 상위 필드 비교
    baseline_meta = {
        key: value
        for key, value in baseline.items()
        if key != "documents"
    }
    final_meta = {
        key: value
        for key, value in final.items()
        if key != "documents"
    }

    meta_mismatches = [
        key for key in baseline_meta
        if baseline_meta.get(key) != final_meta.get(key)
    ]

    assert not meta_mismatches, (
        f"{filename} 상위 메타데이터 차이: {meta_mismatches}"
    )

    print("\n파일:", filename)
    print("재생성 서류:", len(baseline["documents"]))

    for basic_row, final_row in zip(
        baseline["documents"],
        final["documents"],
    ):
        assert basic_row["document_id"] == final_row["document_id"]
        assert basic_row["row_number"] == final_row["row_number"]

        total_rows += 1

        # 공통으로 존재하는 필드는 값까지 동일해야 함
        common_keys = set(basic_row) & set(final_row)

        mismatches = [
            key for key in sorted(common_keys)
            if basic_row[key] != final_row[key]
        ]

        # 재생성 결과에서만 존재하는 필드도 별도 확인
        baseline_only = sorted(
            set(basic_row) - set(final_row)
        )

        final_only = sorted(
            set(final_row) - set(basic_row)
        )

        total_mismatches += len(mismatches)
        total_extra_fields += len(final_only)

        print(
            f"  No.{basic_row['row_number']:02d}",
            f"공통 필드 차이={mismatches}",
            f"최종본 추가 필드={final_only}",
            f"재생성본 전용 필드={baseline_only}",
        )

        if mismatches and "raw_row_text_ja" in mismatches:
            old_text = basic_row["raw_row_text_ja"]
            new_text = final_row["raw_row_text_ja"]

            print(
                "    원문 문자 수:",
                f"재생성={len(old_text)}, 최종={len(new_text)}"
            )
            print(
                "    공백 제거 후 일치:",
                "".join(old_text.split()) ==
                "".join(new_text.split())
            )

    print("재생성 SHA-256:", sha256(baseline_path))
    print("최종 SHA-256:", sha256(final_path))

print("\n===== STEP 63-33 비교 결과 =====")
print("비교한 제출서류:", total_rows)
print("공통 필드 불일치 개수:", total_mismatches)
print("최종본 추가 필드 개수:", total_extra_fields)
print("최종 JSON SHA-256: 모두 일치")
print("파일 수정: 없음")
print("재현성 완전 검증: 아직 미완료")
print("Git 커밋·푸시: 미실행")