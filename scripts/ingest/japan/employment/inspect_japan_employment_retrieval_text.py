
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
INPUT = (
    ROOT
    / "data/processed/japan/employment"
    / "japan_employment_retrieval_records.jsonl"
)

EXPECTED_SHA = (
    "d782f3618d46c951f21a305f40ef72e9"
    "825ee14d77084cad59fb22689c8d8be8"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def inspect_shape(value, prefix="", depth=0):
    """실제 값은 변경하지 않고 키·자료형 구조만 출력."""
    if depth > 5:
        print(f"    {prefix}: [최대 깊이 도달]")
        return

    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key

            if isinstance(child, dict):
                print(f"    {path}: dict ({len(child)} keys)")
                inspect_shape(child, path, depth + 1)

            elif isinstance(child, list):
                print(f"    {path}: list ({len(child)} items)")

                if child:
                    inspect_shape(
                        child[0],
                        path + "[0]",
                        depth + 1,
                    )

            else:
                print(
                    f"    {path}: "
                    f"{type(child).__name__}"
                )


print("===== STEP 63-97 검색 텍스트 구조 점검 =====")

assert INPUT.is_file(), "검색 레코드 JSONL 누락"

original_bytes = INPUT.read_bytes()
assert sha256(original_bytes) == EXPECTED_SHA

records = [
    json.loads(line)
    for line in original_bytes.decode("utf-8").splitlines()
]

assert len(records) == 35
print("[PASS] JSONL SHA-256 및 35개 레코드")

print("\n[전체 텍스트 길이 분포]")

for group in (
    "coe_common",
    "coe_category34",
    "change",
    "renewal",
):
    items = [
        row for row in records
        if row["dataset_group"] == group
    ]

    lengths = [
        len(row["raw_text_ja"])
        for row in items
    ]

    print(
        f"{group}: {len(items)}개 | "
        f"최소 {min(lengths)}자 | "
        f"최대 {max(lengths)}자 | "
        f"평균 {sum(lengths) / len(lengths):.1f}자"
    )

print("\n[상세 증빙 중첩 구조]")

evidence_records = [
    row for row in records
    if row["evidence"]
]

assert len(evidence_records) == 9

for row in evidence_records:
    print(f"\n문서 ID: {row['document_id']}")
    print("신청 유형:", row["application_type"])
    print("증빙 필드:", list(row["evidence"]))

    inspect_shape(row["evidence"])

print("\n[Category 기호 분포]")

counts = Counter()

for row in records:
    for category, value in (
        row["category_requirements"].items()
    ):
        counts[(row["dataset_group"], category,
                str(value["symbol"]))] += 1

for (group, category, symbol), count in sorted(
    counts.items()
):
    print(
        f"{group} / Category {category} / "
        f"{symbol}: {count}"
    )

assert sha256(INPUT.read_bytes()) == EXPECTED_SHA
print("\n[PASS] 기존 JSONL 불변성")

print("\n===== STEP 63-97 최종 결과 =====")
print("전체 레코드: 35개")
print("상세 증빙 구조 확인 대상: 9개")
print("텍스트 길이 분포: 확인")
print("Category 기호 분포: 확인")
print("기존 JSONL 변경: 없음")
print("검색 텍스트 생성: 미실행")
print("임베딩·DB 적재: 미실행")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")