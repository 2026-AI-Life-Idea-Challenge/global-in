
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa"
SHARED = BASE / "shared"

QUEUE = SHARED / "usa_review_queue.jsonl"
INDEX = SHARED / "usa_retrieval_index.json"
MANIFEST = SHARED / "usa_retrieval_review_manifest.json"

OUTPUT = SHARED / "usa_policy_review_queue.jsonl"
REPORT = SHARED / "usa_policy_review_report.json"

EXPECTED = {
    QUEUE: (
        "b2fbb611dd05363060ac099355e7f1c1"
        "1fdcbee602dd0d2130fcb964961b1241"
    ),
    INDEX: (
        "a5b801fd23d914861f04b51916e035"
        "f82e9c854fe3ad1353542bb80933d01c7a"
    ),
    MANIFEST: (
        "e97d8ed6197caf245ac3b1a828db723"
        "23616d0a5a5f1fc18a4f7e14ca4e240d0"
    ),
}

LEGAL_PATTERNS = {
    "obligation": [
        r"\bmust\b",
        r"\brequired\b",
        r"\bshall\b",
        r"반드시",
        r"필수",
        r"의무",
    ],
    "eligibility": [
        r"\beligib(?:le|ility)\b",
        r"\bqualif(?:y|ication|ications)\b",
        r"지원\s*자격",
        r"지원\s*대상",
        r"지원\s*제한",
    ],
    "prohibition": [
        r"\bprohibited\b",
        r"\bnot permitted\b",
        r"\bmay not\b",
        r"금지",
        r"불가",
    ],
    "exception": [
        r"\bexempt\b",
        r"\bexception\b",
        r"\bunless\b",
        r"예외",
        r"면제",
    ],
    "documents": [
        r"\bdocumentation\b",
        r"\bdocuments?\b",
        r"\bevidence\b",
        r"제출\s*서류",
        r"증빙",
    ],
    "fees_or_support": [
        r"\bfees?\b",
        r"\bfunding\b",
        r"정부\s*지원",
        r"참가비",
        r"지원금",
    ],
    "visa_or_status": [
        r"\bvisa\b",
        r"\bstatus\b",
        r"비자",
        r"체류",
    ],
}

SITE_UI_PATTERNS = [
    r"\bskip to main content\b",
    r"\bback to top\b",
    r"\bshare this page\b",
    r"\bcookie preferences?\b",
    r"\baccept all cookies\b",
    r"\bsubscribe to updates\b",
    r"\bfollow us\b",
]

CONTEXT_CHARS = 350


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_verified(path, expected):
    assert path.is_file(), f"파일 없음: {path}"
    raw = path.read_bytes()

    assert sha256(raw) == expected, (
        f"SHA-256 불일치: {path}"
    )

    return raw


def parse_jsonl(raw):
    return [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]


def jsonl_bytes(records):
    return "".join(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
        ) + "\n"
        for record in records
    ).encode("utf-8")


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def reconstruct(parts):
    parts = sorted(
        parts,
        key=lambda item: item["char_start"]
    )

    assert parts
    assert parts[0]["char_start"] == 0

    full_text = ""
    last_end = 0
    expected_hash = parts[0]["unit_text_sha256"]

    for part in parts:
        start = part["char_start"]
        end = part["char_end"]
        text = part["text"]

        assert start <= last_end
        assert end > last_end
        assert end - start == len(text)

        if start < last_end:
            overlap = last_end - start

            assert full_text[start:last_end] == (
                text[:overlap]
            )
            full_text += text[overlap:]
        else:
            full_text += text

        last_end = end

    assert sha256(
        full_text.encode("utf-8")
    ) == expected_hash

    return full_text


print("===== STEP 64-25 정책·법률 청크 검토 준비 =====")

# 1. 기존 데이터 검증
queue_raw = read_verified(
    QUEUE, EXPECTED[QUEUE]
)
index_raw = read_verified(
    INDEX, EXPECTED[INDEX]
)
manifest_raw = read_verified(
    MANIFEST, EXPECTED[MANIFEST]
)

queue = parse_jsonl(queue_raw)
index = json.loads(index_raw.decode("utf-8"))
manifest = json.loads(manifest_raw.decode("utf-8"))

assert len(queue) == 201
assert index["total_chunks"] == 334
assert manifest["flagged_review_count"] == 201
assert manifest["unflagged_candidate_count"] == 133

assert (
    manifest["source_index_sha256"]
    == EXPECTED[INDEX]
)
assert manifest[
    "automatic_eligibility_rules_enabled"
] is False

print("[PASS] 기존 인덱스·대기열·Manifest 무결성")

# 2. 전체 원본 청크를 근거 단위별로 복원
unit_parts = defaultdict(list)
original_hashes = dict(EXPECTED)
all_chunk_ids = set()

for entry in index["programs"]:
    path = ROOT / entry["retrieval_path"]

    assert path.resolve().is_relative_to(
        BASE.resolve()
    )

    raw = read_verified(
        path, entry["retrieval_sha256"]
    )
    original_hashes[path] = entry["retrieval_sha256"]

    rows = parse_jsonl(raw)

    assert len(rows) == entry["chunk_count"]

    for row in rows:
        cid = row["chunk_id"]

        assert cid not in all_chunk_ids
        assert row["program_id"] == entry["program_id"]

        all_chunk_ids.add(cid)

        unit_key = (
            row["program_id"],
            row["evidence_unit_id"],
        )
        unit_parts[unit_key].append(row)

assert len(all_chunk_ids) == 334

unit_texts = {
    key: reconstruct(parts)
    for key, parts in unit_parts.items()
}

print(
    "[PASS] 공식 근거 단위",
    len(unit_texts),
    "개 원문 복원"
)

# 3. P1 청크 103개 추출
p1 = [
    item for item in queue
    if item["review_priority"]
    == "P1_policy_or_legal"
]

assert len(p1) == 103, (
    f"P1 청크 예상 103개, 실제 {len(p1)}개"
)

review_records = []

for item in p1:
    cid = item["chunk_id"]

    assert cid in all_chunk_ids
    assert "potential_eligibility_or_legal_claim" in (
        item["audit_flags"]
    )

    unit_key = (
        item["program_id"],
        item["evidence_unit_id"],
    )

    full_text = unit_texts[unit_key]

    start = item["char_start"]
    end = item["char_end"]

    assert full_text[start:end] == item["text"]

    matched_categories = {}

    for category, patterns in LEGAL_PATTERNS.items():
        matches = []

        for pattern in patterns:
            if re.search(
                pattern, item["text"],
                re.IGNORECASE,
            ):
                matches.append(pattern)

        if matches:
            matched_categories[category] = matches

    ui_matches = [
        pattern for pattern in SITE_UI_PATTERNS
        if re.search(
            pattern, item["text"],
            re.IGNORECASE,
        )
    ]

    context_start = max(
        0, start - CONTEXT_CHARS
    )
    context_end = min(
        len(full_text), end + CONTEXT_CHARS
    )

    # 유형은 자동 승인 결과가 아니라 검토 순서용 후보
    if ui_matches:
        review_candidate = "site_ui_candidate"
    elif item["source_kind"] == "official_pdf":
        review_candidate = "pdf_policy_context_review"
    else:
        review_candidate = "official_html_policy_review"

    record = {
        "chunk_id": cid,
        "program_id": item["program_id"],
        "source_kind": item["source_kind"],
        "source_url": item["source_url"],
        "source_sha256": item["source_sha256"],
        "heading": item["heading"],
        "category_candidate": item["category_candidate"],
        "review_candidate_type": review_candidate,
        "matched_policy_categories": matched_categories,
        "site_ui_pattern_matches": ui_matches,
        "duplicate_info": item["duplicate_info"],
        "text": item["text"],
        "text_sha256": item["text_sha256"],
        "context_before": full_text[
            context_start:start
        ],
        "context_after": full_text[
            end:context_end
        ],
        "source_unit_sha256": (
            item["unit_text_sha256"]
        ),
        "physical_pdf_page": (
            item["physical_pdf_page"]
        ),
        "printed_page_candidate": (
            item["printed_page_candidate"]
        ),
        "review_questions": [
            "실제 프로그램별 공식 본문인가?",
            "사이트 공통 UI 또는 관련 링크인가?",
            "조건의 주체와 적용 범위가 명확한가?",
            "예외·시점·변경 가능성의 확인이 필요한가?",
            "해당 문장을 사용자에게 안내해도 되는가?",
        ],
        "human_review_status": "pending",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
    }

    assert sha256(
        record["text"].encode("utf-8")
    ) == record["text_sha256"]

    review_records.append(record)

assert len(review_records) == 103
assert len({
    item["chunk_id"] for item in review_records
}) == 103

print("[PASS] P1 청크 103개 원본·맥락 대조")

# 4. 검토 패키지와 통계 생성
review_records.sort(
    key=lambda item: (
        item["program_id"],
        item["chunk_id"],
    )
)

category_counts = Counter()
program_counts = Counter()
candidate_counts = Counter()

for item in review_records:
    program_counts[item["program_id"]] += 1
    candidate_counts[
        item["review_candidate_type"]
    ] += 1

    for category in item["matched_policy_categories"]:
        category_counts[category] += 1

review_raw = jsonl_bytes(review_records)

report = {
    "dataset_type": "usa_policy_review_report",
    "country": "US",
    "review_scope": "P1_policy_or_legal",
    "input_review_queue_sha256": EXPECTED[QUEUE],
    "input_index_sha256": EXPECTED[INDEX],
    "input_manifest_sha256": EXPECTED[MANIFEST],
    "total_review_records": len(review_records),
    "program_counts": dict(sorted(
        program_counts.items()
    )),
    "candidate_type_counts": dict(sorted(
        candidate_counts.items()
    )),
    "matched_policy_category_counts": dict(sorted(
        category_counts.items()
    )),
    "review_queue_path": (
        OUTPUT.relative_to(ROOT).as_posix()
    ),
    "review_queue_sha256": sha256(review_raw),
    "review_method": (
        "keyword_candidate_classification_"
        "with_original_text_context"
    ),
    "automated_semantic_approval": False,
    "human_review_completed": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "database_loaded": False,
}

report_raw = json_bytes(report)

planned = [
    (OUTPUT, review_raw),
    (REPORT, report_raw),
]

# 5. 저장 전 충돌·재현성 검사
for path, raw in planned:
    assert path.parent.is_dir()
    assert not path.exists(), (
        f"기존 출력 파일이 존재합니다: {path}"
    )

assert review_raw == jsonl_bytes(review_records)
assert report_raw == json_bytes(report)

print("[PASS] 검토 패키지 재현성·충돌 검사")

# 6. 저장 및 재읽기
for path, raw in planned:
    with path.open("xb") as file:
        file.write(raw)

    assert path.read_bytes() == raw

assert parse_jsonl(
    OUTPUT.read_bytes()
) == review_records

assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == report

print("[PASS] 검토 패키지·통계 보고서 저장")

# 7. 원본 불변 확인
for path, expected_hash in original_hashes.items():
    assert sha256(path.read_bytes()) == expected_hash, (
        f"원본 변경 감지: {path}"
    )

print("[PASS] 기존 데이터 불변")

print("\n===== STEP 64-25 최종 결과 =====")
print("P1 검토 패키지:", len(review_records))
print("프로그램별:", dict(sorted(program_counts.items())))
print("후보 유형별:", dict(sorted(candidate_counts.items())))
print("정책 표현별:", dict(sorted(category_counts.items())))
print("검토 파일:", OUTPUT.relative_to(ROOT))
print("검토 파일 SHA-256:", sha256(review_raw))
print("통계 파일:", REPORT.relative_to(ROOT))
print("통계 파일 SHA-256:", sha256(report_raw))
print("원본·맥락 연결: PASS")
print("기존 파일 변경: 없음")
print("자동 의미 승인: False")
print("답변용 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")