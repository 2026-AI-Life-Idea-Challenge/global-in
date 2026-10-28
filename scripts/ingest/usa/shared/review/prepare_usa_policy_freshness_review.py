
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa/shared/review"
CLEANED = BASE / "cleaned"
POLICY = BASE / "policy"

SOURCE = CLEANED / "usa_p1_ui_cleaned_final.jsonl"

PRIORITY_OUT = POLICY / "usa_policy_freshness_priority.jsonl"
REGISTER_OUT = POLICY / "usa_policy_freshness_register.jsonl"
REPORT_OUT = POLICY / "usa_policy_freshness_report.json"

EXPECTED_SHA = (
    "1cf77cfa6b0c14e6da3c08eb5501bc"
    "751c50d6dbd9b19b79a37f674da0817275"
)

DATE_PATTERN = re.compile(
    r"\b(?:20\d{2}|FY\s*20\d{2})\b",
    re.IGNORECASE,
)

SENSITIVE_PATTERNS = {
    "payment": r"\$100,000|fee|payment|수수료|참가비",
    "selection": r"cap season|selection|registration|선발",
    "exception": r"exception|exempt|unless|예외|면제",
    "deadline": r"deadline|effective|starting|마감|부터",
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(raw):
    return [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]


def jsonl_bytes(records):
    return "".join(
        json.dumps(
            record, ensure_ascii=False, sort_keys=True
        ) + "\n"
        for record in records
    ).encode("utf-8")


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def write_or_verify(path, content):
    if path.exists():
        assert path.read_bytes() == content, (
            f"기존 파일 충돌: {path}"
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as file:
        file.write(content)

    assert path.read_bytes() == content
    return "CREATED"


print("===== STEP 64-31 미국 정책 현행성 검토 준비 =====")

# 1. 입력 파일 검증
assert SOURCE.is_file()

raw = SOURCE.read_bytes()
assert sha256(raw) == EXPECTED_SHA

records = read_jsonl(raw)
assert len(records) == 103

assert len({
    r["chunk_id"] for r in records
}) == 103

print("[PASS] STEP 64-29 정제 후보 103개 무결성")

# 2. 모든 P1 청크의 검증 등록부 생성
register = []

for record in records:
    text = record["cleaned_candidate_text"]
    issues = record["review_issues"]

    priority = (
        "P0_freshness_check"
        if "time_sensitive_policy" in issues
        else "P1_policy_check_pending"
    )

    subject = "undetermined"

    category = record["classification_candidate"]

    if category == "sponsor_or_host_obligations":
        subject = "sponsor_or_host"
    elif category == "historical_west_notice":
        subject = "historical_west_applicant_or_operator"
    elif category == "f1_school_or_i20_guidance":
        subject = "student_or_school"
    elif category == "h1b_policy_or_procedure":
        subject = "petitioner_or_beneficiary"

    detected = [
        name
        for name, pattern in SENSITIVE_PATTERNS.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]

    entry = {
        "chunk_id": record["chunk_id"],
        "program_id": record["program_id"],
        "source_url": record["source_url"],
        "source_text_sha256": (
            record["original_text_sha256"]
        ),
        "review_text_sha256": (
            record["cleaned_candidate_sha256"]
        ),
        "review_text": text,
        "review_priority": priority,
        "claim_subject_candidate": subject,
        "detected_years": sorted(set(
            DATE_PATTERN.findall(text)
        )),
        "sensitive_topics": detected,
        "historical_notice": (
            record["program_id"] == "US-WEST-01"
        ),
        "source_currentness_checked": False,
        "current_official_text_compared": False,
        "application_scope_verified": False,
        "exceptions_verified": False,
        "policy_review_status": "pending",
        "human_review_status": "pending",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
    }

    assert sha256(
        text.encode("utf-8")
    ) == entry["review_text_sha256"]

    register.append(entry)

assert len(register) == 103

priority_records = [
    item for item in register
    if item["review_priority"] == "P0_freshness_check"
]

assert len(priority_records) == 13, (
    f"시점 검토 후보: 예상 13개, "
    f"실제 {len(priority_records)}개"
)

print("[PASS] 전체 103개 정책 현행성 검토 등록")
print("[PASS] 최우선 검증 대상 13개 분리")

# 3. 검증 보고서
program_counts = Counter(
    item["program_id"]
    for item in priority_records
)

report = {
    "dataset_type": "usa_policy_freshness_review",
    "country": "US",
    "total_policy_chunks": 103,
    "priority_freshness_chunks": 13,
    "remaining_policy_chunks": 90,
    "priority_program_counts": dict(
        sorted(program_counts.items())
    ),
    "source_cleaned_sha256": EXPECTED_SHA,
    "official_comparison_status": "not_started",
    "note": (
        "These records are review queues only. "
        "No current legal claim is automatically approved."
    ),
    "currentness_verified": False,
    "application_scope_verified": False,
    "approved_for_embedding": False,
    "approved_for_user_answers": False,
    "automatic_eligibility_rules_enabled": False,
}

register_raw = jsonl_bytes(register)
priority_raw = jsonl_bytes(priority_records)

report["register_sha256"] = sha256(register_raw)
report["priority_sha256"] = sha256(priority_raw)

report_raw = json_bytes(report)

# 4. 저장 전 검증
planned = [
    (REGISTER_OUT, register_raw),
    (PRIORITY_OUT, priority_raw),
    (REPORT_OUT, report_raw),
]

for path, content in planned:
    assert path.parent.is_dir()

    if path.exists():
        assert path.read_bytes() == content, (
            f"기존 결과와 충돌: {path}"
        )

# 5. 저장 및 재검증
for path, content in planned:
    state = write_or_verify(path, content)
    print(
        f"[PASS] {state}:",
        path.relative_to(ROOT),
    )
    print("SHA-256:", sha256(content))

assert read_jsonl(REGISTER_OUT.read_bytes()) == register
assert read_jsonl(PRIORITY_OUT.read_bytes()) == (
    priority_records
)

assert json.loads(
    REPORT_OUT.read_text(encoding="utf-8")
) == report

assert sha256(SOURCE.read_bytes()) == EXPECTED_SHA

print("[PASS] 저장·재읽기·원본 불변")

print("\n===== STEP 64-31 최종 결과 =====")
print("전체 검토 등록:", len(register))
print("현행성 우선 검증:", len(priority_records))
print("나머지 검증 대기:", 90)
print("프로그램별 우선 검증:", dict(
    sorted(program_counts.items())
))
print("공식 현행 규정 대조: 미실행")
print("정책 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")