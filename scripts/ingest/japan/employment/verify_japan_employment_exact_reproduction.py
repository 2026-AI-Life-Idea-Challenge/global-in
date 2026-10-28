
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

FILENAME = "japan_employment_coe_common_structured.json"

REPRO = (
    ROOT / "_local_backup/japan_employment_repro_enriched" / FILENAME
)

FINAL = (
    ROOT / "data/processed/japan/employment" / FILENAME
)

OUTPUT = (
    ROOT
    / "_local_backup/japan_employment_repro_exact_crlf"
    / FILENAME
)

EXPECTED_REPRO_SHA = (
    "ac7791557493b9eacebeccef7ce87fdef3fb2ba10a979dc0959e57a9dbf04ebb"
)

EXPECTED_FINAL_SHA = (
    "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


print("===== STEP 63-37 JSON 완전 재현 검증 =====")

assert REPRO.is_file(), "재생성 JSON 누락"
assert FINAL.is_file(), "최종 JSON 누락"
assert not OUTPUT.exists(), "검증 출력 파일이 이미 존재합니다"

assert sha256(REPRO) == EXPECTED_REPRO_SHA
assert sha256(FINAL) == EXPECTED_FINAL_SHA

repro = json.loads(REPRO.read_text(encoding="utf-8"))
final = json.loads(FINAL.read_text(encoding="utf-8"))

# 1. 원본과 재생성본의 데이터 내용 확인
assert repro == final, "데이터 내용이 일치하지 않습니다"

# 2. 재생성 파이프라인의 필드 순서 보정
for row in repro["documents"]:
    assert "text_extraction_method" in row

    method = row.pop("text_extraction_method")

    assert method == "pdf_table_horizontal_boundaries"

    # 기본 제출서류 필드 다음, 상세 증빙자료 필드 이전에 배치
    reordered = {}

    for key, value in row.items():
        reordered[key] = value

        if key == "validation_status":
            reordered["text_extraction_method"] = method

    assert "text_extraction_method" in reordered

    row.clear()
    row.update(reordered)

# 3. 기존 최종본의 필드 순서와 비교
assert list(repro) == list(final)

for new_row, final_row in zip(
    repro["documents"],
    final["documents"],
):
    assert new_row["document_id"] == final_row["document_id"]
    assert list(new_row) == list(final_row)

# 4. 출력 형식도 기존 JSON과 동일하게 유지
# 기존 최종 JSON의 Windows CRLF 줄바꿈 형식 재현
json_text = json.dumps(
    repro,
    ensure_ascii=False,
    indent=2,
)

encoded = json_text.replace(
    "\n", "\r\n"
).encode("utf-8")

reproduced_sha = hashlib.sha256(encoded).hexdigest()

print("데이터 내용 일치: 성공")
print("전체 제출서류:", len(repro["documents"]))
print("필드 순서 일치: 성공")
print("재생성 SHA-256:", reproduced_sha)
print("최종본 SHA-256:", EXPECTED_FINAL_SHA)

# STEP 63-37-2: 바이트 및 중첩 필드 순서 진단
final_bytes = FINAL.read_bytes()

print("\n[바이트 비교 진단]")
print("재생성 바이트 수:", len(encoded))
print("최종본 바이트 수:", len(final_bytes))
print("바이트 길이 차이:", len(encoded) - len(final_bytes))

first_diff = next(
    (
        i
        for i, (a, b) in enumerate(zip(encoded, final_bytes))
        if a != b
    ),
    None,
)

if first_diff is None and len(encoded) != len(final_bytes):
    first_diff = min(len(encoded), len(final_bytes))

print("첫 번째 차이 위치:", first_diff)

if first_diff is not None:
    start = max(0, first_diff - 100)
    end = first_diff + 180

    print(
        "재생성 내용:",
        repr(encoded[start:end].decode("utf-8", errors="replace"))
    )
    print(
        "최종본 내용:",
        repr(final_bytes[start:end].decode("utf-8", errors="replace"))
    )

print("\n[중첩 딕셔너리 필드 순서 비교]")

def inspect_key_order(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a) != list(b):
            print("필드 순서 차이:", path)
            print("  재생성:", list(a))
            print("  최종본:", list(b))

        for key in a.keys() & b.keys():
            inspect_key_order(a[key], b[key], f"{path}.{key}")

    elif isinstance(a, list) and isinstance(b, list):
        for index, (left, right) in enumerate(zip(a, b)):
            inspect_key_order(left, right, f"{path}[{index}]")

inspect_key_order(repro, final)

print("\n[줄 끝 형식]")
print("재생성 CRLF:", encoded.count(b"\r\n"))
print("최종본 CRLF:", final_bytes.count(b"\r\n"))
print("재생성 마지막 개행:", encoded.endswith(b"\n"))
print("최종본 마지막 개행:", final_bytes.endswith(b"\n"))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("xb") as f:
    f.write(encoded)

assert sha256(OUTPUT) == EXPECTED_FINAL_SHA
assert OUTPUT.read_bytes() == FINAL.read_bytes()

print("\n===== STEP 63-37 최종 결과 =====")
print("재생성 데이터와 최종본: 바이트 단위 일치")
print("완전 재현성 검증: 성공")
print("검증 출력:", OUTPUT.relative_to(ROOT))
print("기존 processed JSON: 변경 없음")
print("기존 v2 스크립트: 변경 없음")
print("Git 커밋·푸시: 미실행")