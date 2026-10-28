
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "scripts/ingest/japan/employment"
FINAL = ROOT / "data/processed/japan/employment"

WORK = Path(os.environ["JP_EM_COE_PIPELINE_WORK_DIR"]).resolve() if os.environ.get("JP_EM_COE_PIPELINE_WORK_DIR") else ROOT / "_local_backup/japan_employment_pipeline_run02"
BASELINE = WORK / "baseline"
CATEGORY = WORK / "category"
EDUCATION = WORK / "education"
EXACT = WORK / "exact"

COMMON = "japan_employment_coe_common_structured.json"
CAT34 = "japan_employment_coe_category34_structured.json"

EXPECTED = {
    "baseline_common":
        "fd31b73d9ae74e6d9fc84ed68deb917d45e7e8f3945cdf6bf55dc4b288daa0a1",
    "baseline_cat34":
        "dd0aebe3aed025e83f60e4907e60074eb7bdd37dfa7ceb1f8b6ffd85dcf52e00",
    "category_intermediate":
        "ac7791557493b9eacebeccef7ce87fdef3fb2ba10a979dc0959e57a9dbf04ebb",
    "final_common":
        "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68",
    "final_cat34":
        "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path, expected):
    assert path.is_file(), f"파일 누락: {path}"
    actual = sha256(path)
    assert actual == expected, (
        f"SHA-256 불일치: {path}\n"
        f"예상: {expected}\n실제: {actual}"
    )


def run_script(filename, overrides):
    script = SCRIPTS / filename
    assert script.is_file(), f"스크립트 누락: {script}"

    env = os.environ.copy()

    # 이전 CMD에서 설정된 환경변수의 영향 제거
    for key in [
        "JP_EM_COE_OUTPUT_DIR",
        "JP_EM_COE_BASELINE_DIR",
        "JP_EM_COE_CATEGORY_OUTPUT_DIR",
        "JP_EM_COE_EDUCATION_OUTPUT_DIR",
    ]:
        env.pop(key, None)

    env.update({
        key: str(value.resolve())
        for key, value in overrides.items()
    })

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        env=env,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{filename} 실행 실패: 종료 코드 {result.returncode}"
        )


print("===== STEP 63-45 subprocess 통합 재생성 =====")

# 1. 기존 최종본과 테스트 경로 보호
assert not WORK.exists(), (
    "테스트 폴더가 이미 존재합니다. "
    "기존 결과를 덮어쓰지 않습니다."
)

verify(FINAL / COMMON, EXPECTED["final_common"])
verify(FINAL / CAT34, EXPECTED["final_cat34"])

for name in [
    "structure_japan_employment_coe_documents_v2.py",
    "reproduce_japan_employment_category_evidence.py",
    "reproduce_japan_employment_education_evidence.py",
]:
    assert (SCRIPTS / name).is_file(), f"스크립트 누락: {name}"

print("최종 JSON SHA-256 사전 검증: 성공")
print("기존 테스트 폴더 보호: 확인")

# 2. 원본 PDF에서 기본 데이터 재생성
print("\n[1/4] COE 기본 제출서류 재생성")

run_script(
    "structure_japan_employment_coe_documents_v2.py",
    {
        "JP_EM_COE_OUTPUT_DIR": BASELINE,
    },
)

verify(
    BASELINE / COMMON,
    EXPECTED["baseline_common"],
)
verify(
    BASELINE / CAT34,
    EXPECTED["baseline_cat34"],
)

print("기본 제출서류 14개: SHA-256 검증 성공")

# 3. 카테고리별 증빙 원문 및 선택지 생성
print("\n[2/4] 카테고리별 증빙자료 재생성")

run_script(
    "reproduce_japan_employment_category_evidence.py",
    {
        "JP_EM_COE_BASELINE_DIR": BASELINE,
        "JP_EM_COE_CATEGORY_OUTPUT_DIR": CATEGORY,
    },
)

verify(
    CATEGORY / COMMON,
    EXPECTED["category_intermediate"],
)

print("카테고리별 증빙 중간 산출물: 검증 성공")

# 4. 필드 순서와 Windows CRLF 형식 재현
print("\n[3/4] 공통 COE JSON 최종 형식 재현")

data = json.loads(
    (CATEGORY / COMMON).read_text(encoding="utf-8")
)

for row in data["documents"]:
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
    data,
    ensure_ascii=False,
    indent=2,
).replace("\n", "\r\n").encode("utf-8")

assert hashlib.sha256(encoded).hexdigest() == (
    EXPECTED["final_common"]
)

EXACT.mkdir(parents=True, exist_ok=False)

common_path = EXACT / COMMON

with common_path.open("xb") as f:
    f.write(encoded)

verify(common_path, EXPECTED["final_common"])

assert common_path.read_bytes() == (
    FINAL / COMMON
).read_bytes()

print("공통 COE 최종본과 바이트 단위 일치")

# 5. 학력·경력 증빙 재생성
print("\n[4/4] 학력·경력 증빙 재생성")

run_script(
    "reproduce_japan_employment_education_evidence.py",
    {
        "JP_EM_COE_BASELINE_DIR": BASELINE,
        "JP_EM_COE_EDUCATION_OUTPUT_DIR": EDUCATION,
    },
)

education_path = EDUCATION / CAT34

verify(education_path, EXPECTED["final_cat34"])

assert education_path.read_bytes() == (
    FINAL / CAT34
).read_bytes()

print("카테고리 3·4 COE 최종본과 바이트 단위 일치")

# 6. 전체 제출서류 및 상세 증빙 구조 검증
common_data = json.loads(
    common_path.read_text(encoding="utf-8")
)
education_data = json.loads(
    education_path.read_text(encoding="utf-8")
)

rows = (
    common_data["documents"]
    + education_data["documents"]
)

ids = [row["document_id"] for row in rows]

assert len(rows) == len(set(ids)) == 14

row4 = next(
    row for row in rows
    if row["document_id"] == "JP_EM_COE_DOC_004"
)

row8 = next(
    row for row in rows
    if row["document_id"] == "JP_EM_COE_DOC_008"
)

assert sum(
    item["evidence_count"]
    for item in row4["category_evidence_options"].values()
) == 7

options = row8["education_evidence"][
    "alternative_group"
]["options"]

assert len(options) == 4
assert "clean_text_ja" in next(
    item for item in options
    if item["clause"] == "イ"
)

assert all(
    row["validation_status"] == "needs_review"
    for row in rows
)

# 작업 도중 원본이 변경되지 않았는지 최종 확인
verify(FINAL / COMMON, EXPECTED["final_common"])
verify(FINAL / CAT34, EXPECTED["final_cat34"])

print("\n===== STEP 63-45 최종 결과 =====")
print("전체 제출서류:", len(rows))
print("소속기관 증빙 선택지: 7개")
print("학력·경력 대체 증빙: 4개")
print("최종 JSON 바이트 단위 일치: 2/2")
print("subprocess 실행: 성공")
print("코드 문자열 치환: 없음")
print("exec() 사용: 없음")
print("테스트 폴더:", WORK.relative_to(ROOT))
print("기존 processed JSON: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")