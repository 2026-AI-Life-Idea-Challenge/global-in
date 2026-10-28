
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
POLICY = ROOT / "data/processed/usa/shared/review/policy"

SOURCE = POLICY / "usa_policy_freshness_priority.jsonl"
OUTPUT = POLICY / "usa_policy_scope_review.jsonl"
REPORT = POLICY / "usa_policy_scope_review_report.json"

EXPECTED_SHA = (
    "00c45a9eb12a3b110b227a32530cb0fd"
    "03a50e12391c6996544e4dc13c151d25"
)

# 청크별 실제 본문을 검토하여 지정한 검토 범주.
# 여기의 분류는 현행 법률 검증 또는 자격 판정이 아님.
REVIEW_SCOPE = {
    "US-EM-01-S01-B0002-C001":
        ("filing_fee", "effective_date_and_fee_schedule"),
    "US-EM-01-S01-B0005-C001":
        ("presidential_proclamation", "filing_date_and_exceptions"),
    "US-EM-01-S01-B0008-C001":
        ("presidential_proclamation", "status_change_exception"),
    "US-EM-01-S01-B0012-C001":
        ("presidential_proclamation", "payment_process_and_scope"),
    "US-EM-01-S01-B0014-C001":
        ("presidential_proclamation", "payment_exception_and_evidence"),
    "US-EM-01-S01-B0050-C001":
        ("h1b_filing", "petition_type_and_proclamation"),
    "US-EM-01-S02-B0003-C001":
        ("h1b_cap", "cap_exempt_employer_and_date"),
    "US-EM-01-S02-B0006-C001":
        ("h1b_cap", "fy2027_weighted_selection"),
    "US-EM-01-S02-B0052-C001":
        ("premium_processing_fee", "effective_date_and_form_i907"),
    "US-EM-01-S02-B0074-C001":
        ("h1b_cap", "fy2027_employment_start_date"),
    "US-WEST-01-P01-L-C001":
        ("historical_west", "2026_first_half_notice"),
    "US-WEST-01-P06-L-C001":
        ("historical_west", "2026_first_half_faq"),
    "US-WEST-01-P07-R-C001":
        ("historical_west", "2026_first_half_loan_guidance"),
}

REFERENCE_LINKS = {
    "US-EM-01": [
        "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations/h-1b-cap-season",
        "https://www.uscis.gov/sites/default/files/document/memos/H1B_Proc_Memo_FINAL.pdf",
    ],
    "US-WEST-01": [
        "https://www.niied.go.kr/web/main/nid/niied_board/5570",
    ],
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def jsonl_bytes(rows):
    return "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
        for r in rows
    ).encode("utf-8")


def json_bytes(obj):
    return (
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def save_or_verify(path, data):
    if path.exists():
        assert path.read_bytes() == data, (
            f"기존 파일과 내용 충돌: {path}"
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as f:
        f.write(data)

    assert path.read_bytes() == data
    return "CREATED"


print("===== STEP 64-32 정책 적용 범위 검토 =====")

assert SOURCE.is_file()

source_raw = SOURCE.read_bytes()
assert sha256(source_raw) == EXPECTED_SHA

rows = [
    json.loads(line)
    for line in source_raw.decode("utf-8").splitlines()
    if line.strip()
]

assert len(rows) == 13
assert {r["chunk_id"] for r in rows} == set(REVIEW_SCOPE)

print("[PASS] 우선 검증 13개 원본·ID 확인")

results = []

for record in rows:
    cid = record["chunk_id"]
    program = record["program_id"]

    category, focus = REVIEW_SCOPE[cid]

    assert program in REFERENCE_LINKS
    assert record["approved_for_user_answers"] is False
    assert record["approved_for_embedding"] is False

    review = {
        **record,
        "policy_category": category,
        "verification_focus": focus,
        "official_reference_urls": REFERENCE_LINKS[program],
        "official_reference_urls_are_verification_targets": True,
        "original_evidence_reproduced": True,
        "live_official_page_verified": False,
        "current_legal_effect_verified": False,
        "all_exceptions_verified": False,
        "interpretation_review_status": "pending",
        "historical_only": program == "US-WEST-01",
        "must_not_generalize_to_all_applicants": True,
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
    }

    results.append(review)

results.sort(key=lambda r: r["chunk_id"])

assert len(results) == 13

categories = Counter(
    r["policy_category"] for r in results
)

output_raw = jsonl_bytes(results)

report = {
    "dataset_type": "usa_policy_scope_review",
    "total_records": 13,
    "h1b_records": 10,
    "west_historical_records": 3,
    "category_counts": dict(sorted(categories.items())),
    "source_sha256": EXPECTED_SHA,
    "review_records_sha256": sha256(output_raw),
    "note": (
        "Review focus and official source targets are recorded. "
        "This is not a completed current-law verification."
    ),
    "live_official_page_verified": False,
    "current_legal_effect_verified": False,
    "human_review_completed": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

report_raw = json_bytes(report)

for path, data in (
    (OUTPUT, output_raw),
    (REPORT, report_raw),
):
    state = save_or_verify(path, data)

    print(f"[PASS] {state}: {path.relative_to(ROOT)}")
    print("SHA-256:", sha256(data))

assert [
    json.loads(line)
    for line in OUTPUT.read_text(
        encoding="utf-8"
    ).splitlines()
] == results

assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == report

assert sha256(SOURCE.read_bytes()) == EXPECTED_SHA

print("[PASS] 저장·재읽기·기존 파일 불변")

print("\n===== STEP 64-32 최종 결과 =====")
print("정책 검토 대상:", len(results))
print("H-1B:", 10)
print("WEST 과거 공고:", 3)
print("검토 유형:", dict(sorted(categories.items())))
print("현행 규정 대조 완료: False")
print("답변 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("기존 파일 변경: 없음")
print("Git 커밋·푸시: 미실행")