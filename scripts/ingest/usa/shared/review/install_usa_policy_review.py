
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]

SHARED = ROOT / "data/processed/usa/shared"
REVIEW = SHARED / "review"
POLICY = REVIEW / "policy"
CLEANED = REVIEW / "cleaned"
APPROVED = REVIEW / "approved"

SOURCE = SHARED / "usa_policy_review_queue.jsonl"

OUTPUT_JSONL = POLICY / "usa_p1_content_triage_103.jsonl"
OUTPUT_CSV = POLICY / "usa_p1_content_triage_103.csv"
OUTPUT_SUMMARY = POLICY / "usa_p1_content_triage_summary.json"

EXPECTED_SOURCE_SHA = (
    "d755e3f6d7f6506b999ccbd31f20cc2a"
    "89c787eaf7b5a617ecbf9c8d8be464b4"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def serialize_json(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def serialize_jsonl(records):
    return "".join(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True
        ) + "\n"
        for record in records
    ).encode("utf-8")


def classify(record):
    """
    1차 자동 분류 후보만 생성한다.
    실제 법령·조건 승인으로 취급하지 않는다.
    """
    program = record["program_id"]
    text = record["text"]
    heading = record.get("heading", "")
    combined = (heading + " " + text).lower()

    issues = []

    if program == "US-WEST-01":
        category = "historical_west_notice"
        issues.append("historical_2026_first_half")

    elif program == "US-EM-01":
        category = "h1b_policy_or_procedure"

    elif program == "US-ST-01":
        category = "f1_school_or_i20_guidance"

    elif re.search(
        r"sponsors? (must|are required)|"
        r"hosts? (must|are required)|"
        r"host organizations? are required",
        combined,
    ):
        category = "sponsor_or_host_obligations"

    elif record.get("category_candidate") == (
        "participants_and_eligibility"
    ):
        category = "participant_eligibility_candidate"

    else:
        category = "program_policy_or_procedure"

    if re.search(
        r"\b(?:must|required|shall|prohibited|"
        r"eligible|ineligible)\b|반드시|의무|금지|불가",
        text,
        re.IGNORECASE,
    ):
        issues.append("obligation_or_eligibility_language")

    if re.search(
        r"202[5-9]|\$100,000|fee schedule|"
        r"final rule|proclamation|cap season",
        text,
        re.IGNORECASE,
    ):
        issues.append("time_sensitive_policy")

    if re.search(
        r"program resources|common questions|"
        r"sevis information|end tab|"
        r"<a\s|class=\"button",
        text,
        re.IGNORECASE,
    ):
        issues.append("possible_site_ui_contamination")

    if record.get("duplicate_info"):
        issues.append("duplicate_candidate")

    if len(text.strip()) < 80:
        issues.append("short_text")

    return category, sorted(set(issues))


def save_new_or_verify(path, content):
    """
    재실행해도 같은 내용이면 PASS.
    내용이 다르면 기존 파일을 덮어쓰지 않는다.
    """
    if path.exists():
        assert path.read_bytes() == content, (
            f"기존 파일 내용이 다릅니다: {path}"
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as file:
        file.write(content)

    assert path.read_bytes() == content
    return "CREATED"


print("===== STEP 64-27 정책 검토 폴더 및 데이터 배치 =====")

# 1. 기존 검토 원본 SHA-256 검증
assert SOURCE.is_file(), (
    f"STEP 64-25 원본이 없습니다: {SOURCE}"
)

source_raw = SOURCE.read_bytes()
source_sha = sha256(source_raw)

assert source_sha == EXPECTED_SOURCE_SHA, (
    "STEP 64-25 원본 SHA-256 불일치"
)

records = [
    json.loads(line)
    for line in source_raw.decode("utf-8").splitlines()
    if line.strip()
]

assert len(records) == 103
assert len({
    item["chunk_id"] for item in records
}) == 103

print("[PASS] STEP 64-25 원본 103개 검증")

# 2. 분류 결과 생성
triage = []

for record in records:
    category, issues = classify(record)

    triage.append({
        "chunk_id": record["chunk_id"],
        "program_id": record["program_id"],
        "source_url": record["source_url"],
        "source_kind": record["source_kind"],
        "heading": record.get("heading"),
        "source_text": record["text"],
        "source_text_sha256": record["text_sha256"],
        "classification_candidate": category,
        "review_issues": issues,
        "duplicate_info": record.get("duplicate_info"),
        "review_method": "automated_first_pass",
        "human_review_status": "pending",
        "official_live_rule_verified": False,
        "approved_for_embedding": False,
        "approved_for_user_answers": False,
        "automatic_eligibility_rules_enabled": False,
    })

    assert sha256(
        record["text"].encode("utf-8")
    ) == record["text_sha256"]

triage.sort(key=lambda item: item["chunk_id"])

print("[PASS] 정책 청크 103개 자동 1차 분류")

# 3. JSONL 생성
jsonl_raw = serialize_jsonl(triage)

# 4. CSV 생성
# CSV는 utf-8-sig로 저장하여 Excel 한글 깨짐 방지
import io

csv_buffer = io.StringIO(newline="")

fieldnames = [
    "chunk_id",
    "program_id",
    "source_url",
    "source_kind",
    "heading",
    "classification_candidate",
    "review_issues",
    "source_text",
    "source_text_sha256",
    "human_review_status",
    "approved_for_embedding",
    "approved_for_user_answers",
]

writer = csv.DictWriter(
    csv_buffer,
    fieldnames=fieldnames,
    extrasaction="ignore",
    lineterminator="\n",
)

writer.writeheader()

for item in triage:
    row = dict(item)
    row["review_issues"] = json.dumps(
        item["review_issues"],
        ensure_ascii=False
    )
    writer.writerow(row)

csv_raw = (
    b"\xef\xbb\xbf"
    + csv_buffer.getvalue().encode("utf-8")
)

# 5. 통계 JSON 생성
categories = Counter(
    item["classification_candidate"]
    for item in triage
)

programs = Counter(
    item["program_id"]
    for item in triage
)

issues = Counter(
    issue
    for item in triage
    for issue in item["review_issues"]
)

summary = {
    "dataset_type": "usa_policy_triage_summary",
    "country": "US",
    "source_file": SOURCE.relative_to(ROOT).as_posix(),
    "source_sha256": source_sha,
    "total_chunks": len(triage),
    "program_counts": dict(sorted(programs.items())),
    "classification_candidate_counts": dict(
        sorted(categories.items())
    ),
    "issue_counts": dict(sorted(issues.items())),
    "triage_method": "automated_first_pass",
    "note": (
        "This is an automated classification, "
        "not final human semantic or legal approval."
    ),
    "human_review_completed": False,
    "approved_for_embedding": False,
    "approved_for_user_answers": False,
    "automatic_eligibility_rules_enabled": False,
}

summary_raw = serialize_json(summary)

# 6. 폴더 자동 생성
for folder in (POLICY, CLEANED, APPROVED):
    folder.mkdir(parents=True, exist_ok=True)

print("[PASS] review/policy, cleaned, approved 폴더 확인")

# 7. 저장 전 전체 충돌 검사
planned = [
    (OUTPUT_JSONL, jsonl_raw),
    (OUTPUT_CSV, csv_raw),
    (OUTPUT_SUMMARY, summary_raw),
]

for path, content in planned:
    if path.exists():
        assert path.read_bytes() == content, (
            f"동일 이름의 다른 파일 존재: {path}"
        )

# 8. 저장 및 검증
for path, content in planned:
    result = save_new_or_verify(path, content)
    print(f"[PASS] {result}: {path.relative_to(ROOT)}")
    print("SHA-256:", sha256(content))

saved_records = [
    json.loads(line)
    for line in OUTPUT_JSONL.read_text(
        encoding="utf-8"
    ).splitlines()
]

assert saved_records == triage
assert len(saved_records) == 103

assert json.loads(
    OUTPUT_SUMMARY.read_text(encoding="utf-8")
) == summary

# 9. 기존 원본 불변 확인
assert sha256(SOURCE.read_bytes()) == source_sha

print("[PASS] 결과 파일 재읽기")
print("[PASS] STEP 64-25 원본 불변")

print("\n===== STEP 64-27 최종 결과 =====")
print("정책 청크:", len(triage))
print("프로그램별:", dict(sorted(programs.items())))
print("분류 후보별:", dict(sorted(categories.items())))
print("검토 사유별:", dict(sorted(issues.items())))
print("생성·검증 결과 파일:", len(planned))
print("원본 파일 변경: 없음")
print("사람에 의한 최종 의미 검수: pending")
print("답변용 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")