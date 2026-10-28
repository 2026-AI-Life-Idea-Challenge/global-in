
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

FILENAME = "japan_employment_coe_common_structured.json"

REPRO = (
    ROOT
    / "_local_backup/japan_employment_repro_enriched"
    / FILENAME
)

FINAL = (
    ROOT
    / "data/processed/japan/employment"
    / FILENAME
)

EXPECTED_REPRO = (
    "ac7791557493b9eacebeccef7ce87fdef3fb2ba10a979dc0959e57a9dbf04ebb"
)

EXPECTED_FINAL = (
    "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_values(a, b, path="$", differences=None):
    if differences is None:
        differences = []

    if type(a) is not type(b):
        differences.append(
            (path, f"자료형 차이: {type(a).__name__} / {type(b).__name__}")
        )
        return differences

    if isinstance(a, dict):
        a_keys = set(a)
        b_keys = set(b)

        for key in sorted(a_keys - b_keys):
            differences.append((f"{path}.{key}", "재생성본에만 존재"))

        for key in sorted(b_keys - a_keys):
            differences.append((f"{path}.{key}", "최종본에만 존재"))

        for key in sorted(a_keys & b_keys):
            compare_values(
                a[key],
                b[key],
                f"{path}.{key}",
                differences,
            )

    elif isinstance(a, list):
        if len(a) != len(b):
            differences.append(
                (path, f"배열 길이: {len(a)} / {len(b)}")
            )

        for index, (left, right) in enumerate(zip(a, b)):
            compare_values(
                left,
                right,
                f"{path}[{index}]",
                differences,
            )

    elif a != b:
        differences.append(
            (path, f"값 차이: {a!r} / {b!r}")
        )

    return differences


print("===== STEP 63-36 재생성 JSON 불일치 원인 분석 =====")

assert REPRO.is_file(), "재생성 JSON 누락"
assert FINAL.is_file(), "최종 JSON 누락"

assert sha256(REPRO) == EXPECTED_REPRO, (
    "재생성 JSON SHA-256이 예상과 다릅니다"
)

assert sha256(FINAL) == EXPECTED_FINAL, (
    "최종 JSON SHA-256이 예상과 다릅니다"
)

repro = json.loads(REPRO.read_text(encoding="utf-8"))
final = json.loads(FINAL.read_text(encoding="utf-8"))

# 1. 실제 데이터 값 비교
differences = compare_values(repro, final)

print("\n[1. JSON 데이터 내용 비교]")
print("데이터 전체 동일:", repro == final)
print("값 또는 구조 차이:", len(differences), "개")

for path, detail in differences[:30]:
    print("경로:", path)
    print("차이:", detail)

if len(differences) > 30:
    print("추가 차이:", len(differences) - 30, "개")

# 2. 최상위 필드 순서 비교
print("\n[2. 최상위 필드 순서]")
print("재생성:", list(repro))
print("최종본:", list(final))

# 3. 각 제출서류 필드 순서 비교
print("\n[3. 서류별 필드 순서 비교]")

order_differences = []

for repro_row, final_row in zip(
    repro["documents"],
    final["documents"],
):
    assert repro_row["document_id"] == final_row["document_id"]

    if list(repro_row) != list(final_row):
        document_id = repro_row["document_id"]
        order_differences.append(document_id)

        print("\n서류:", document_id)
        print("재생성 필드 순서:", list(repro_row))
        print("최종본 필드 순서:", list(final_row))

print("\n필드 순서가 다른 서류:", len(order_differences))

# 4. 순서를 정규화했을 때 직렬화 결과 비교
# 주의: 실제 파일 내용은 변경하지 않는다.
normalized_repro = json.dumps(
    repro,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)

normalized_final = json.dumps(
    final,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)

semantic_hash_match = (
    hashlib.sha256(
        normalized_repro.encode("utf-8")
    ).hexdigest()
    ==
    hashlib.sha256(
        normalized_final.encode("utf-8")
    ).hexdigest()
)

print("\n[4. 순서 정규화 비교]")
print(
    "정규화 후 SHA-256 일치:",
    semantic_hash_match
)

print("\n===== STEP 63-36 최종 결과 =====")
print("재생성 파일 SHA-256: 검증 성공")
print("최종 파일 SHA-256: 검증 성공")
print("데이터 내용 일치:", repro == final)
print("값 또는 구조 차이:", len(differences))
print("필드 순서 차이 서류:", len(order_differences))
print("JSON 및 PDF 수정: 없음")
print("Git 커밋·푸시: 미실행")