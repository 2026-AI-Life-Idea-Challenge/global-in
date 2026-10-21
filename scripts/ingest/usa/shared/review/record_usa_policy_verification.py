
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
POLICY = ROOT / "data/processed/usa/shared/review/policy"

SOURCE = POLICY / "usa_policy_freshness_priority.jsonl"
OUTPUT = POLICY / "usa_policy_verified_evidence_13.jsonl"
REPORT = POLICY / "usa_policy_verification_summary.json"

EXPECTED_SHA = (
    "00c45a9eb12a3b110b227a32530cb0fd"
    "03a50e12391c6996544e4dc13c151d25"
)

USCIS_H1B = (
    "https://www.uscis.gov/working-in-the-united-states/"
    "h-1b-specialty-occupations"
)
USCIS_CAP = (
    "https://www.uscis.gov/working-in-the-united-states/"
    "temporary-workers/h-1b-specialty-occupations/"
    "h-1b-cap-season"
)
USCIS_MEMO = (
    "https://www.uscis.gov/sites/default/files/"
    "document/memos/H1B_Proc_Memo_FINAL.pdf"
)
USCIS_FEES = (
    "https://www.uscis.gov/forms/all-forms/"
    "h-and-l-filing-fees-for-form-i-129-petition-"
    "for-a-nonimmigrant-worker"
)
USCIS_PREMIUM = (
    "https://www.uscis.gov/newsroom/alerts/"
    "uscis-to-increase-premium-processing-fees"
)
USCIS_WEIGHTED = (
    "https://www.uscis.gov/newsroom/alerts/"
    "fy-2027-h-1b-cap-initial-registration-"
    "period-opens-on-march-4"
)
WEST_FIRST = (
    "https://www.niied.go.kr/web/main/"
    "nid/niied_board/5570"
)
WEST_SECOND = (
    "https://niied.go.kr/web/main/"
    "nid/niied_board/5749"
)

# 분류는 공식 자료와 청크의 관계를 기록하는 것이며,
# 최종 법적 적용이나 사용자 자격의 승인이 아닙니다.
#
# 유형:
# official_statement_correlated:
#   공식 발표에서 핵심 날짜/제도를 추가 확인
# scope_or_exception_pending:
#   관련 공식 지침은 있으나 전체 적용범위 검증 미완료
# historical_notice_confirmed:
#   과거 회차의 공고임을 확인

REVIEW = {
    "US-EM-01-S01-B0002-C001": (
        "official_statement_correlated",
        [USCIS_FEES, USCIS_H1B],
        "2026-09-09 Form I-129 fee rule",
        "최종 수수료 및 청원별 적용액 추가 확인 필요",
    ),
    "US-EM-01-S01-B0005-C001": (
        "scope_or_exception_pending",
        [USCIS_MEMO, USCIS_H1B],
        "2025-09 H-1B proclamation",
        "시행일 전 청원·기존 승인·기존 비자 예외 확인 필요",
    ),
    "US-EM-01-S01-B0008-C001": (
        "scope_or_exception_pending",
        [USCIS_H1B, USCIS_MEMO],
        "change of status exception",
        "신분변경·연장·출국 사례별 적용 판단 필요",
    ),
    "US-EM-01-S01-B0012-C001": (
        "scope_or_exception_pending",
        [USCIS_H1B],
        "H-1B payment process",
        "납부 대상에 해당하는지 먼저 판단해야 함",
    ),
    "US-EM-01-S01-B0014-C001": (
        "scope_or_exception_pending",
        [USCIS_H1B, USCIS_MEMO],
        "payment proof and exceptions",
        "예외 인정 요건·납부 증빙의 최신 지침 확인 필요",
    ),
    "US-EM-01-S01-B0050-C001": (
        "scope_or_exception_pending",
        [USCIS_H1B],
        "I-129 petition and conditional payment",
        "고용주 청원 절차와 포고령 적용 대상을 구분",
    ),
    "US-EM-01-S02-B0003-C001": (
        "scope_or_exception_pending",
        [USCIS_CAP],
        "H-1B cap exemptions",
        "고용주 유형·CNMI·Guam 예외 세부조건 확인 필요",
    ),
    "US-EM-01-S02-B0006-C001": (
        "official_statement_correlated",
        [USCIS_CAP, USCIS_WEIGHTED],
        "FY 2027 weighted selection",
        "FY 2027 회차 전용 내용으로 표시",
    ),
    "US-EM-01-S02-B0052-C001": (
        "official_statement_correlated",
        [USCIS_PREMIUM],
        "2026-03-01 I-907 fee change",
        "신청 혜택 유형별 실제 수수료 확인 필요",
    ),
    "US-EM-01-S02-B0074-C001": (
        "scope_or_exception_pending",
        [USCIS_CAP],
        "FY 2027 petition start dates",
        "FY 2027 제출 기간 및 청원 유형별 조건 확인",
    ),
    "US-WEST-01-P01-L-C001": (
        "historical_notice_confirmed",
        [WEST_FIRST, WEST_SECOND],
        "2026 first-half WEST notice",
        "하반기 공고로 기존 상반기 지원조건을 대체할 수 없음",
    ),
    "US-WEST-01-P06-L-C001": (
        "historical_notice_confirmed",
        [WEST_FIRST, WEST_SECOND],
        "2026 first-half WEST FAQ",
        "상반기 FAQ를 하반기 지원자에게 자동 적용 금지",
    ),
    "US-WEST-01-P07-R-C001": (
        "historical_notice_confirmed",
        [WEST_FIRST, WEST_SECOND],
        "2026 first-half WEST loan guidance",
        "대출 및 학자금지원구간 절차는 회차별 재검증 필요",
    ),
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def encode_jsonl(rows):
    return "".join(
        json.dumps(
            row, ensure_ascii=False, sort_keys=True
        ) + "\n"
        for row in rows
    ).encode("utf-8")


def encode_json(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def save_or_verify(path, payload):
    if path.exists():
        assert path.read_bytes() == payload, (
            f"기존 파일 충돌: {path}"
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as f:
        f.write(payload)

    assert path.read_bytes() == payload
    return "CREATED"


print("===== STEP 64-34 공식 근거 검토 결과 반영 =====")

# 1. 검토 대상 검증
assert SOURCE.is_file()

source_raw = SOURCE.read_bytes()
assert sha256(source_raw) == EXPECTED_SHA

records = [
    json.loads(line)
    for line in source_raw.decode("utf-8").splitlines()
    if line.strip()
]

assert len(records) == 13
assert {r["chunk_id"] for r in records} == set(REVIEW)

print("[PASS] 정책 13개·SHA-256·ID 검증")

# 2. 확인 결과 연결
results = []

for row in records:
    cid = row["chunk_id"]
    status, urls, topic, remaining = REVIEW[cid]

    assert sha256(
        row["review_text"].encode("utf-8")
    ) == row["review_text_sha256"]

    is_west = row["program_id"] == "US-WEST-01"

    assert is_west == (
        status == "historical_notice_confirmed"
    )

    result = {
        "chunk_id": cid,
        "program_id": row["program_id"],
        "review_text": row["review_text"],
        "review_text_sha256": row["review_text_sha256"],
        "source_url": row["source_url"],
        "evidence_review_status": status,
        "official_reference_urls": urls,
        "reviewed_topic": topic,
        "remaining_verification": remaining,
        "review_date": "2026-10-21",
        "review_basis": "official_public_web_sources",
        "historical_notice": is_west,
        "source_statement_correlated": True,
        "individual_application_verified": False,
        "all_exceptions_verified": False,
        "current_rule_fully_verified": False,
        "human_final_approval": False,
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
    }

    results.append(result)

results.sort(key=lambda item: item["chunk_id"])

assert len(results) == 13

counts = Counter(
    row["evidence_review_status"]
    for row in results
)

assert counts == {
    "official_statement_correlated": 3,
    "scope_or_exception_pending": 7,
    "historical_notice_confirmed": 3,
}

print("[PASS] 공식 자료 근거·검토 범위 연결")

# 3. 결과 보고서
result_raw = encode_jsonl(results)

summary = {
    "dataset_type": "usa_policy_source_review_summary",
    "country": "US",
    "total_records": 13,
    "review_date": "2026-10-21",
    "review_status_counts": dict(sorted(counts.items())),
    "input_sha256": EXPECTED_SHA,
    "output_sha256": sha256(result_raw),
    "note": (
        "Correlated official publications are not "
        "equivalent to complete current-law verification."
    ),
    "all_current_rules_verified": False,
    "human_final_approval": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

summary_raw = encode_json(summary)

# 4. 저장
planned = [
    (OUTPUT, result_raw),
    (REPORT, summary_raw),
]

for path, payload in planned:
    assert path.parent.is_dir()

    if path.exists():
        assert path.read_bytes() == payload, (
            f"기존 결과 파일 충돌: {path}"
        )

for path, payload in planned:
    state = save_or_verify(path, payload)
    print(f"[PASS] {state}: {path.relative_to(ROOT)}")
    print("SHA-256:", sha256(payload))

# 5. 재읽기 및 원본 불변
saved = [
    json.loads(line)
    for line in OUTPUT.read_text(
        encoding="utf-8"
    ).splitlines()
]

assert saved == results
assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == summary

assert sha256(SOURCE.read_bytes()) == EXPECTED_SHA

print("[PASS] 저장·재읽기·기존 원본 불변")

print("\n===== STEP 64-34 최종 결과 =====")
print("공식 자료와 주요 진술 대조:", 3)
print("적용 범위·예외 추가 확인:", 7)
print("WEST 과거 공고 확인:", 3)
print("전체 정책 검토:", len(results))
print("상반기 WEST 자료의 현행 회차 사용: 금지")
print("모든 청크 원본 유지: PASS")
print("현행 법률 전체 검증: 미완료")
print("답변용 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")