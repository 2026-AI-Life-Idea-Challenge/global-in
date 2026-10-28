
from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[4]

SCRIPT = (
    ROOT
    / "scripts/ingest/japan/employment"
    / "structure_japan_employment_coe_documents.py"
)

PROCESSED = ROOT / "data/processed/japan/employment"

EXPECTED = {
    "japan_employment_coe_common_structured.json":
        "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68",
    "japan_employment_coe_category34_structured.json":
        "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce",
}

KEYWORDS = [
    "horizontal",
    "boundaries",
    "midpoint",
    "raw_row_text_ja",
    "text_extraction_method",
    "category_evidence",
    "education_evidence",
    "clean_text_ja",
    "json.dump",
    "write_text",
    "open(",
    "exists(",
]

print("===== STEP 63-30 재현성 사전 점검 =====")

assert SCRIPT.is_file(), "최초 JSON 생성 스크립트가 없습니다."

source = SCRIPT.read_text(encoding="utf-8")
lines = source.splitlines()

print("\n[최초 생성 스크립트]")
print("파일:", SCRIPT.relative_to(ROOT))
print("전체 줄 수:", len(lines))

print("\n[핵심 기능 포함 여부]")
for keyword in KEYWORDS:
    found = keyword.lower() in source.lower()
    print(
        f"{keyword}:",
        "발견" if found else "미발견"
    )

print("\n[주요 코드 위치]")
matches = []

for index, line in enumerate(lines, start=1):
    if any(
        keyword.lower() in line.lower()
        for keyword in KEYWORDS
    ):
        matches.append(index)

for index in matches[:45]:
    start = max(1, index - 2)
    end = min(len(lines), index + 2)

    print(f"\n--- {index}번 줄 주변 ---")

    for n in range(start, end + 1):
        print(f"{n:04d}: {lines[n - 1]}")

if len(matches) > 45:
    print("\n추가 일치 위치:", len(matches) - 45, "개")

print("\n[현재 최종 JSON SHA-256]")

for filename, expected_sha in EXPECTED.items():
    path = PROCESSED / filename
    assert path.is_file(), f"최종 JSON 누락: {filename}"

    actual_sha = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    assert actual_sha == expected_sha, (
        f"최종 JSON이 예상 버전과 다릅니다: {filename}"
    )

    print(filename)
    print("  SHA-256:", actual_sha)
    print("  상태: 일치")

print("\n===== STEP 63-30 결과 =====")
print("생성 스크립트 구조 조사: 완료")
print("최종 JSON 무결성: 확인")
print("재현성: 아직 미검증")
print("파일 수정: 없음")
print("Git 커밋·푸시: 미실행")