
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = ROOT / "scripts/ingest/japan/employment"

WORK = ROOT / "_local_backup/japan_employment_pipeline_run01"
FINAL = ROOT / "data/processed/japan/employment"

BASELINE = WORK / "baseline"
CATEGORY = WORK / "category"
EDUCATION = WORK / "education"
EXACT = WORK / "exact"

COMMON = "japan_employment_coe_common_structured.json"
CAT34 = "japan_employment_coe_category34_structured.json"

EXPECTED = {
    COMMON: (
        "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68"
    ),
    CAT34: (
        "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce"
    ),
}

# STEP 63-35에서 검증한 1차 증빙 구조화 산출물
CATEGORY_INTERMEDIATE_SHA = (
    "ac7791557493b9eacebeccef7ce87fdef3fb2ba10a979dc0959e57a9dbf04ebb"
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(path.read_bytes())


def replace_once(source, old, new):
    count = source.count(old)
    assert count == 1, (
        f"스크립트 변경 위치 불일치: {old!r}, 발견={count}"
    )
    return source.replace(old, new, 1)


def load_script(filename):
    path = SCRIPT_DIR / filename
    assert path.is_file(), f"스크립트 누락: {path}"
    return path, path.read_text(encoding="utf-8")


def execute_script(path, source):
    # 기존 스크립트 파일은 수정하지 않는다.
    # 실행 시에만 출력 경로를 별도 작업 폴더로 변경한다.
    namespace = {
        "__file__": str(path),
        "__name__": "__main__",
    }
    exec(compile(source, str(path), "exec"), namespace)


def final_check(path, name):
    assert path.is_file(), f"재생성 파일 누락: {path}"
    assert sha256_file(path) == EXPECTED[name], (
        f"재생성 SHA-256 불일치: {name}"
    )
    assert path.read_bytes() == (FINAL / name).read_bytes(), (
        f"최종본과 바이트 불일치: {name}"
    )


print("===== STEP 63-40 일본 취업 COE 통합 재생성 =====")

# 1. 전체 사전 검사: 기존 파일 보호
assert not WORK.exists(), (
    "테스트 폴더가 이미 존재합니다. 기존 결과는 덮어쓰지 않습니다."
)

for name, expected in EXPECTED.items():
    path = FINAL / name
    assert path.is_file(), f"최종 JSON 누락: {name}"
    assert sha256_file(path) == expected, (
        f"최종 JSON SHA-256 불일치: {name}"
    )

# 실행에 필요한 스크립트 전부 먼저 읽기
base_path, base_src = load_script(
    "structure_japan_employment_coe_documents_v2.py"
)
cat_path, cat_src = load_script(
    "reproduce_japan_employment_category_evidence.py"
)
edu_path, edu_src = load_script(
    "reproduce_japan_employment_education_evidence.py"
)

# 2. 출력 경로를 이번 테스트 폴더로만 변경
base_src = replace_once(
    base_src,
    '"_local_backup/japan_employment_repro_baseline"',
    f'"{BASELINE.relative_to(ROOT).as_posix()}"',
)

cat_src = replace_once(
    cat_src,
    '"_local_backup/japan_employment_repro_baseline"',
    f'"{BASELINE.relative_to(ROOT).as_posix()}"',
)
cat_src = replace_once(
    cat_src,
    '"_local_backup/japan_employment_repro_enriched"',
    f'"{CATEGORY.relative_to(ROOT).as_posix()}"',
)

# 1차 구조화 결과의 SHA를 검사한다.
# 최종본과의 차이(필드 순서·CRLF)는 마지막 단계에서 보정.
cat_src = replace_once(
    cat_src,
    EXPECTED[COMMON],
    CATEGORY_INTERMEDIATE_SHA,
)
cat_src = replace_once(
    cat_src,
    '"기존 최종 SHA-256:"',
    '"1차 산출물 기대 SHA-256:"',
)

edu_src = replace_once(
    edu_src,
    '"_local_backup/japan_employment_repro_baseline"',
    f'"{BASELINE.relative_to(ROOT).as_posix()}"',
)
edu_src = replace_once(
    edu_src,
    '"_local_backup/japan_employment_repro_education"',
    f'"{EDUCATION.relative_to(ROOT).as_posix()}"',
)

# 변경된 소스의 Python 문법 사전 검사
for path, source in [
    (base_path, base_src),
    (cat_path, cat_src),
    (edu_path, edu_src),
]:
    compile(source, str(path), "exec")

print("기존 최종 JSON 무결성: 성공")
print("출력 경로 분리: 성공")
print("실행 스크립트 문법 검사: 성공")

# 3. PDF -> 기본 JSON
print("\n[1/4] PDF 기본 제출서류 재생성")
execute_script(base_path, base_src)

assert sha256_file(BASELINE / COMMON) == (
    "fd31b73d9ae74e6d9fc84ed68deb917d45e7e8f3945cdf6bf55dc4b288daa0a1"
)
assert sha256_file(BASELINE / CAT34) == (
    "dd0aebe3aed025e83f60e4907e60074eb7bdd37dfa7ceb1f8b6ffd85dcf52e00"
)

# 4. 공통 COE 증빙 구조화
print("\n[2/4] 소속기관 카테고리별 증빙 재생성")
execute_script(cat_path, cat_src)

assert sha256_file(CATEGORY / COMMON) == CATEGORY_INTERMEDIATE_SHA

# 5. 공통 COE JSON 필드 순서 및 CRLF 복원
print("\n[3/4] 공통 COE 파일 형식 재현")

dataset = json.loads(
    (CATEGORY / COMMON).read_text(encoding="utf-8")
)

for row in dataset["documents"]:
    method = row.pop("text_extraction_method")
    assert method == "pdf_table_horizontal_boundaries"

    reordered = {}
    for key, value in row.items():
        reordered[key] = value
        if key == "validation_status":
            reordered["text_extraction_method"] = method

    assert "text_extraction_method" in reordered
    row.clear()
    row.update(reordered)

encoded = json.dumps(
    dataset, ensure_ascii=False, indent=2
).replace("\n", "\r\n").encode("utf-8")

assert sha256_bytes(encoded) == EXPECTED[COMMON]

EXACT.mkdir(parents=True, exist_ok=False)
common_exact_path = EXACT / COMMON

with common_exact_path.open("xb") as f:
    f.write(encoded)

final_check(common_exact_path, COMMON)
print("공통 COE 최종본과 일치: 성공")

# 6. 학력·경력 증빙 재생성
print("\n[4/4] 학력·경력 증빙 재생성")
execute_script(edu_path, edu_src)

final_check(EDUCATION / CAT34, CAT34)
print("카테고리 3·4 COE 최종본과 일치: 성공")

# 7. 전체 통합 검증
common_data = json.loads(common_exact_path.read_text(encoding="utf-8"))
cat34_data = json.loads(
    (EDUCATION / CAT34).read_text(encoding="utf-8")
)

all_rows = common_data["documents"] + cat34_data["documents"]
ids = [row["document_id"] for row in all_rows]

assert len(all_rows) == 14
assert len(set(ids)) == 14
assert all(
    row["validation_status"] == "needs_review"
    for row in all_rows
)

print("\n===== STEP 63-40 최종 결과 =====")
print("전체 제출서류:", len(all_rows))
print("서류 ID 중복: 없음")
print("공통 COE SHA-256:", sha256_file(common_exact_path))
print("카테고리 3·4 SHA-256:", sha256_file(EDUCATION / CAT34))
print("최종 JSON과 바이트 단위 일치: 2/2")
print("통합 재생성 검증: 성공")
print("테스트 폴더:", WORK.relative_to(ROOT))
print("기존 processed JSON: 변경 없음")
print("기존 생성 스크립트: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")