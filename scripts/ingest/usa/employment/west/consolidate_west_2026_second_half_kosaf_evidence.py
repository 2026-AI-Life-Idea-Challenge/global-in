
from pathlib import Path
from collections import Counter
import hashlib
import json


# ============================================================
# STEP 64-75
# WEST 2026 H2 한국장학재단 근거 통합 감사
#
# - STEP 64-68, 64-73, 64-74 연결
# - 기존 파일 수정 금지
# - 이슈 자동 해결 및 정책 승인 금지
# - 임베딩/DB 적재/자동 자격 판정 금지
# ============================================================

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT
    / "data/processed/usa/employment/west/2026_second_half"
)

# 비교 결과는 고정 SHA로 확인. 본문 결과는 v2 감사 파일로 검증.
COMPARISON_FILE = "west_2026_second_half_cross_agency_comparison.json"
COMPARISON_SHA = "8ed7ff07eb016e8277d90a203f80b935c1fe201ea00c429d7571cea444c7b1f6"
BODY_FILE = "west_2026_second_half_kosaf_body_evidence_v2.json"
BODY_AUDIT_FILE = "west_2026_second_half_kosaf_body_evidence_audit_v2.json"

OUTPUT = (
    BASE
    / "west_2026_second_half_kosaf_evidence_consolidated_v2.json"
)

AUDIT = (
    BASE
    / "west_2026_second_half_kosaf_evidence_consolidated_audit_v2.json"
)

EXPECTED_TASK_IDS = {
    f"WEST-H2-CROSS-{i:02d}"
    for i in range(1, 8)
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_verified(path, expected_hash):
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    actual = sha256(raw)

    if actual != expected_hash:
        raise ValueError(
            f"SHA-256 불일치: {path}\n"
            f"예상: {expected_hash}\n"
            f"실제: {actual}"
        )

    return json.loads(raw.decode("utf-8"))


def check_protection(name, obj):
    if obj.get("program_id") != "US-WEST-01":
        raise ValueError(f"{name}: 프로그램 ID 불일치")

    if obj.get("notice_period") != "2026_second_half":
        raise ValueError(f"{name}: 모집 회차 불일치")

    for flag in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
    ):
        if obj.get(flag) is not False:
            raise ValueError(
                f"{name}: 보호 설정 불일치 - {flag}"
            )


def encode(obj):
    return (
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def save_once(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 결과와 충돌: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"

    return status, sha256(raw)


print("===== STEP 64-75 KOSAF 근거 통합 감사 =====")

# ------------------------------------------------------------
# 1. 이전 결과 무결성 확인
# ------------------------------------------------------------

comparison = read_verified(BASE / COMPARISON_FILE, COMPARISON_SHA)
check_protection("comparison", comparison)

# 본문 감사 파일 자체와 본문 파일을 연계 검증.
body_audit_path = BASE / BODY_AUDIT_FILE
body_audit_raw = body_audit_path.read_bytes()
body_audit = json.loads(body_audit_raw.decode("utf-8"))
check_protection("body_audit", body_audit)
body_hash = body_audit.get("result_sha256")
if not isinstance(body_hash, str) or len(body_hash) != 64:
    raise ValueError("본문 감사 SHA 누락")
body = read_verified(BASE / BODY_FILE, body_hash)
check_protection("body", body)
if body.get("cross01_boundary_fix_integrated") is not True:
    raise ValueError("CROSS-01 본문 경계 수정이 반영되지 않음")
if body_audit.get("body_phrases_found") != 14:
    raise ValueError("본문 감사 기록 14개 근거 확인 실패")
if body_audit.get("cross_agency_tasks") != 7:
    raise ValueError("본문 감사 기록 7개 항목 불일치")
if body_audit.get("input_sha256") != body.get("input_candidate_sha256"):
    raise ValueError("본문과 감사 입력 SHA 불일치")

comparison_items = {item["task_id"]: item for item in comparison["results"]}
body_items = {item["task_id"]: item for item in body["notice_evidence_results"]}
if set(comparison_items) != EXPECTED_TASK_IDS or len(comparison["results"]) != 7:
    raise ValueError("비교 작업 7개 ID 불일치")
if set(body_items) != EXPECTED_TASK_IDS or len(body["notice_evidence_results"]) != 7:
    raise ValueError("본문 작업 7개 ID 불일치")
print("[PASS] STEP 64-68 + 수정된 STEP 64-73 근거 무결성")

# ------------------------------------------------------------
# 2. 항목별 근거 상태 통합
# ------------------------------------------------------------

consolidated = []

for task_id in sorted(EXPECTED_TASK_IDS):
    old = body_items[task_id]
    compare = comparison_items[task_id]

    expected_count = old["expected_phrase_count"]
    found_count = old["found_phrase_count"]

    evidence = []

    for item in old["evidence"]:
        evidence.append({
            "phrase": item["searched_phrase"],
            "found": item["found_in_notice_body"],
            "text_offset": item["source_text_offset"],
            "excerpt": item["excerpt"],
            "evidence_origin": "refactored_body_v2",
        })

    # CROSS-01을 포함한 7개 항목을 동일한 본문 검증 결과에서 취득.
    # 별도 64-74 보정 산출물은 실행 의존성에서 제거.
    if found_count > expected_count:
        raise ValueError(
            f"{task_id}: 발견 문구 수 오류"
        )

    if found_count == expected_count:
        evidence_status = "all_required_phrases_located"
    elif found_count > 0:
        evidence_status = "some_required_phrases_located"
    else:
        evidence_status = "no_required_phrases_located"

    consolidated.append({
        "task_id": task_id,
        "topic": compare["topic"],
        "previous_comparison_status": (
            compare["comparison_status"]
        ),
        "source_id": "kosaf_2026_h2_notice",
        "required_phrase_count": expected_count,
        "located_phrase_count": found_count,
        "evidence_location_status": evidence_status,
        "evidence": evidence,
        "source_document_text_matches_checked": True,
        "agency_to_agency_policy_consistency_approved": False,
        "individual_eligibility_verified": False,
        "manual_semantic_review_completed": False,
        "review_status": "needs_review",
    })

    print(
        f"[PASS] {task_id}: "
        f"{found_count}/{expected_count} "
        f"({evidence_status})"
    )


# ------------------------------------------------------------
# 3. 집계 및 보호 상태 확인
# ------------------------------------------------------------

counts = Counter(
    item["evidence_location_status"]
    for item in consolidated
)

located_tasks = sum(
    item["evidence_location_status"]
    == "all_required_phrases_located"
    for item in consolidated
)

required_total = sum(
    item["required_phrase_count"]
    for item in consolidated
)

located_total = sum(
    item["located_phrase_count"]
    for item in consolidated
)

if required_total != 14:
    raise ValueError(
        f"요구 문구 수 불일치: {required_total}"
    )

if located_total != 14:
    raise ValueError(
        f"확인 문구 수 불일치: {located_total}"
    )

if located_tasks != 7:
    raise ValueError(
        f"문구 확인 완료 작업 수 불일치: {located_tasks}"
    )

print("[PASS] 전체 7개 항목 / 14개 문구 위치 확인")


# ------------------------------------------------------------
# 4. 결과 생성
# ------------------------------------------------------------

result = {
    "dataset_type": "west_kosaf_evidence_consolidated",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,

    "input_sha256": {
        "comparison": COMPARISON_SHA,
        "body": body_hash,
        "body_audit": sha256(body_audit_raw),
    },

    "source_id": "kosaf_2026_h2_notice",

    "task_count": len(consolidated),
    "tasks_with_all_phrases_located": located_tasks,
    "required_phrase_total": required_total,
    "located_phrase_total": located_total,

    "evidence_location_status_counts": dict(counts),
    "results": consolidated,

    "scope": (
        "Archived KOSAF 2026 H2 notice phrase-level "
        "evidence location only"
    ),

    "common_navigation_false_positives_addressed": True,
    "cross01_extraction_boundary_issue_addressed": True,
    "correction_dependency_removed": True,

    "manual_semantic_review_completed": False,
    "cross_agency_final_consistency_verified": False,
    "financial_table_verified": False,
    "individual_eligibility_verified": False,
    "current_policy_verified": False,

    "issues_automatically_resolved": 0,

    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_kosaf_evidence_consolidated_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",

    "input_sha256": result["input_sha256"],
    "task_count": len(consolidated),
    "tasks_with_all_phrases_located": located_tasks,
    "required_phrase_total": required_total,
    "located_phrase_total": located_total,

    "policy_claims_finally_approved": 0,
    "issues_automatically_resolved": 0,
    "input_files_modified": False,

    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

result_raw = encode(result)
result_hash = sha256(result_raw)

audit["result_sha256"] = result_hash
audit_raw = encode(audit)

# 두 파일 모두 먼저 충돌 검사
for path, raw in (
    (OUTPUT, result_raw),
    (AUDIT, audit_raw),
):
    if path.exists() and path.read_bytes() != raw:
        raise FileExistsError(
            f"기존 출력 파일과 내용 불일치: {path}"
        )

status, result_hash = save_once(
    OUTPUT, result_raw
)

audit_status, audit_hash = save_once(
    AUDIT, audit_raw
)


# ------------------------------------------------------------
# 5. 입력 무결성 재확인
# ------------------------------------------------------------

read_verified(BASE / COMPARISON_FILE, COMPARISON_SHA)
read_verified(BASE / BODY_FILE, body_hash)
if sha256(body_audit_path.read_bytes()) != sha256(body_audit_raw):
    raise ValueError("본문 감사 파일 변경 감지")

print("\n===== STEP 64-75 최종 결과 =====")
print("교차 검토 항목:", len(consolidated))
print("근거 문구 전부 발견:", located_tasks)
print(
    "근거 문구 위치 확인:",
    located_total, "/", required_total
)

print(f"[PASS] {status}: {OUTPUT.name}")
print("SHA-256:", result_hash)

print(f"[PASS] {audit_status}: {AUDIT.name}")
print("SHA-256:", audit_hash)

print("정책 의미 최종 검수: 미완료")
print("기관 간 최종 일치 승인: 미완료")
print("이슈 자동 해결: 0")
print("입력 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")