
from pathlib import Path
from collections import Counter
import ast
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
USA_RAW = ROOT / "data/raw/usa"
USA_PROCESSED = ROOT / "data/processed/usa"

PLAN = ROOT / "scripts/usa_organization_plan.json"
BACKUP = ROOT / "_local_backup/usa_scripts_step_64_47"

INDEX = USA_PROCESSED / "shared/usa_retrieval_index.json"

H2_RAW = USA_RAW / "employment/west/2026_second_half"
H2_PROCESSED = (
    USA_PROCESSED / "employment/west/2026_second_half"
)

EXPECTED_PLAN_SHA = (
    "1977b725ba7934e31eb35b8bee2152"
    "deae2388aabc9d9611aed82148a704059d"
)
EXPECTED_INDEX_SHA = (
    "a5b801fd23d914861f04b51916e035"
    "f82e9c854fe3ad1353542bb80933d01c7a"
)
EXPECTED_H2_PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

PROGRAMS = {
    "US-WH-01": "working_holiday/summer_work_travel",
    "US-ST-01": "student/f1_academic_student",
    "US-ST-03": "student/j1_college_university_student",
    "US-EM-01": "employment/h1b_specialty_occupations",
    "US-EM-02": "employment/j1_intern",
    "US-EM-03": "employment/j1_trainee",
    "US-WEST-01": "employment/west",
}

H2_FILES = {
    "raw": [
        "west_2026_second_half_notice.pdf",
        "official_notice_page.html",
        "source_manifest.json",
        "pdf_verification_manifest.json",
    ],
    "processed": [
        "west_2026_second_half_pages.jsonl",
        "west_2026_second_half_blocks.jsonl",
        "west_2026_second_half_extraction_report.json",
        "west_2026_second_half_layout_audit.json",
        "west_2026_second_half_manual_review_queue.jsonl",
        "west_2026_second_half_logical_candidates.jsonl",
        "west_2026_second_half_logical_split_report.json",
    ],
}

errors = []
warnings = []


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def check(condition, message, critical=True):
    if condition:
        print("[PASS]", message)
    else:
        print("[FAIL]" if critical else "[WARN]", message)
        (errors if critical else warnings).append(message)


def require_sha(path, expected, label):
    if not path.is_file():
        check(False, f"{label}: 파일 없음")
        return False

    actual = sha256(path.read_bytes())
    valid = actual == expected
    check(valid, f"{label}: SHA-256")
    return valid


def safe_repo_path(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError(f"프로젝트 외부 경로: {relative}")
    return path


def load_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


print("===== STEP 64-48 미국 프로젝트 통합 검사 =====")
print("검사 모드: READ_ONLY")
print("프로젝트:", ROOT)

# 1. 미국 7개 프로그램 폴더
print("\n[1] 프로그램별 데이터 폴더")

for program_id, relative in PROGRAMS.items():
    raw_dir = USA_RAW / relative
    processed_dir = USA_PROCESSED / relative

    check(
        raw_dir.is_dir(),
        f"{program_id}: raw 폴더"
    )
    check(
        processed_dir.is_dir(),
        f"{program_id}: processed 폴더"
    )

# 2. 이동 계획 검증
print("\n[2] 이동된 Python 스크립트")

if require_sha(PLAN, EXPECTED_PLAN_SHA, "정리 계획"):
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    entries = plan["files"]

    check(len(entries) == 40, "정리 대상 40개")

    moved_count = 0
    backup_count = 0

    root_pattern = re.compile(
        r"Path\(\s*__file__\s*\)"
        r"\.resolve\(\)\.parents\[(\d+)\]"
    )

    for entry in entries:
        old = safe_repo_path(entry["source"])
        new = safe_repo_path(entry["destination"])
        backup = safe_repo_path(
            "_local_backup/usa_scripts_step_64_47/"
            + entry["source"]
        )

        # STEP 64-47에서 이동했으므로 예전 위치는 비어야 함
        if old.exists():
            errors.append(f"기존 위치에 파일 남음: {entry['source']}")

        if not new.is_file():
            errors.append(
                f"이동된 파일 없음: {entry['destination']}"
            )
            continue

        moved_count += 1

        if not backup.is_file():
            errors.append(
                f"백업 없음: {entry['source']}"
            )
            continue

        backup_count += 1

        original = backup.read_bytes()

        if sha256(original) != entry["source_sha256"]:
            errors.append(
                f"백업 해시 불일치: {entry['source']}"
            )
            continue

        # STEP 64-47의 실제 변환 결과를 재구성
        code = original.decode("utf-8-sig")
        matches = list(root_pattern.finditer(code))

        if len(matches) != 1:
            errors.append(
                f"루트 계산식 확인 필요: {entry['source']}"
            )
            continue

        match = matches[0]
        old_depth = int(match.group(1))
        new_depth = len(new.relative_to(ROOT).parts) - 1

        if old_depth != 3:
            errors.append(
                f"예상 밖의 이전 경로 깊이: {entry['source']}"
            )
            continue

        replacement = (
            f"Path(__file__).resolve().parents[{new_depth}]"
        )

        modified = (
            code[:match.start()]
            + replacement
            + code[match.end():]
        )

        expected_bytes = modified.encode("utf-8")

        if new.read_bytes() != expected_bytes:
            errors.append(
                f"이동 후 코드 변경 감지: {entry['destination']}"
            )
            continue

        try:
            ast.parse(modified, filename=str(new))
        except SyntaxError:
            errors.append(
                f"문법 오류: {entry['destination']}"
            )

        if new.resolve().parents[new_depth] != ROOT.resolve():
            errors.append(
                f"루트 경로 오류: {entry['destination']}"
            )

    check(moved_count == 40, "이동된 스크립트 40개")
    check(backup_count == 40, "원본 백업 40개")
    check(
        len(errors) == 0,
        "스크립트 변환·백업·문법·경로 대조"
    )

# 3. 기존 미국 검색 데이터 확인
print("\n[3] 미국 검색 인덱스 및 데이터")

if require_sha(INDEX, EXPECTED_INDEX_SHA, "USA 검색 인덱스"):
    index = json.loads(INDEX.read_text(encoding="utf-8"))

    check(
        index["program_count"] == 7,
        "검색 인덱스 프로그램 7개"
    )
    check(
        index["total_chunks"] == 334,
        "검색 인덱스 청크 334개"
    )

    indexed_ids = set()
    actual_total = 0

    for item in index["programs"]:
        program_id = item["program_id"]
        indexed_ids.add(program_id)

        retrieval = safe_repo_path(item["retrieval_path"])

        if not require_sha(
            retrieval,
            item["retrieval_sha256"],
            f"{program_id}: 검색 데이터"
        ):
            continue

        rows = load_jsonl(retrieval)
        actual_total += len(rows)

        check(
            len(rows) == item["chunk_count"],
            f"{program_id}: 청크 수"
        )

        check(
            all(r["program_id"] == program_id for r in rows),
            f"{program_id}: 청크 소속"
        )

        check(
            all(
                sha256(r["text"].encode("utf-8"))
                == r["text_sha256"]
                for r in rows
            ),
            f"{program_id}: 청크 원문 해시"
        )

        source = safe_repo_path(item["source_data_path"])
        require_sha(
            source,
            item["source_data_sha256"],
            f"{program_id}: 근거 데이터"
        )

    check(
        indexed_ids == set(PROGRAMS),
        "검색 인덱스의 7개 프로그램 ID"
    )
    check(
        actual_total == 334,
        "실제 청크 합계 334개"
    )

    check(
        index.get("automatic_eligibility_rules_enabled")
        is False,
        "자동 자격 판정 비활성화"
    )

# 4. 하반기 WEST 원본 및 검토 자료
print("\n[4] WEST 2026년 하반기")

for name in H2_FILES["raw"]:
    check(
        (H2_RAW / name).is_file(),
        f"하반기 원본: {name}"
    )

for name in H2_FILES["processed"]:
    check(
        (H2_PROCESSED / name).is_file(),
        f"하반기 처리 데이터: {name}"
    )

require_sha(
    H2_RAW / "west_2026_second_half_notice.pdf",
    EXPECTED_H2_PDF_SHA,
    "하반기 WEST PDF"
)

preview_dir = H2_PROCESSED / "logical_page_previews"

preview_files = (
    list(preview_dir.glob("page_*.png"))
    if preview_dir.is_dir()
    else []
)

check(
    len(preview_files) == 22,
    "하반기 논리 페이지 미리보기 22장"
)

candidates = (
    H2_PROCESSED
    / "west_2026_second_half_logical_candidates.jsonl"
)

if candidates.is_file():
    rows = load_jsonl(candidates)

    check(len(rows) == 22, "하반기 논리 페이지 후보 22개")

    block_ids = [
        bid
        for row in rows
        for bid in row["block_ids"]
    ]

    check(
        len(block_ids) == 578
        and len(set(block_ids)) == 578,
        "하반기 텍스트 블록 578개 중복·누락 없음"
    )

    check(
        all(
            row["approved_for_user_answers"] is False
            and row["approved_for_embedding"] is False
            for row in rows
        ),
        "하반기 WEST 답변·임베딩 미승인"
    )

# 5. 검토 자료 확인
print("\n[5] 정책 검토 데이터")

POLICY = USA_PROCESSED / "shared/review/policy"
CLEANED = USA_PROCESSED / "shared/review/cleaned"
APPROVED = USA_PROCESSED / "shared/review/approved"

required_review = [
    POLICY / "usa_policy_verified_evidence_13.jsonl",
    POLICY / "usa_policy_verification_summary.json",
    CLEANED / "usa_p1_ui_cleaned_final.jsonl",
    CLEANED / "usa_duplicate_review.json",
]

for path in required_review:
    check(
        path.is_file(),
        f"검토 파일: {path.name}"
    )

check(
    APPROVED.is_dir(),
    "승인 전용 폴더 존재"
)

if APPROVED.is_dir():
    approved_files = [
        p for p in APPROVED.rglob("*") if p.is_file()
    ]

    check(
        len(approved_files) == 0,
        "승인되지 않은 정책 데이터 배포 방지"
    )

# 6. Git 변경 사항 확인 — 읽기 전용
print("\n[6] Git 상태")

try:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=True,
    )

    changed_lines = [
        line for line in result.stdout.splitlines()
        if line.strip()
    ]

    print("Git 변경 항목 수:", len(changed_lines))

    for line in changed_lines[:30]:
        print(" ", line)

    if len(changed_lines) > 30:
        print(
            f" ... 추가 {len(changed_lines) - 30}개 항목"
        )

except Exception as exc:
    warnings.append(
        f"Git 상태 확인 실패: {type(exc).__name__}"
    )
    print("[WARN] Git 상태를 확인하지 못했습니다.")

# 7. 최종 결과
print("\n===== STEP 64-48 최종 결과 =====")
print("치명적 검사 오류:", len(errors))
print("주의사항:", len(warnings))

for error in errors:
    print("[ERROR]", error)

for warning in warnings:
    print("[WARN]", warning)

if errors:
    print("검사 결론: FAIL — 오류 수정 후 재검사")
else:
    print("검사 결론: PASS — 구조·무결성 점검 통과")
    print("실제 전체 파이프라인 실행 검증: 별도 필요")

print("파일 생성·수정·삭제: 없음")
print("Git add·commit·push: 미실행")

if errors:
    raise SystemExit(1)