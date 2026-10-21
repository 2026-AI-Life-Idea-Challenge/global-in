
from pathlib import Path
import hashlib
import json
import urllib.request
import urllib.error
import re

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[5]
SHARED = ROOT / "data/processed/usa/shared"
POLICY = SHARED / "review/policy"

SOURCE = POLICY / "usa_policy_scope_review.jsonl"
INDEX = SHARED / "usa_retrieval_index.json"
WEST_PDF = (
    ROOT
    / "data/raw/usa/employment/west"
    / "west_2026_first_half_notice.pdf"
)

REPORT = POLICY / "usa_official_evidence_comparison.json"

SOURCE_SHA = (
    "b1115f49c20e2ee005450c0302a6157"
    "c420e10f17e7ff8c978dbc98e98b647e6"
)
INDEX_SHA = (
    "a5b801fd23d914861f04b51916e035"
    "f82e9c854fe3ad1353542bb80933d01c7a"
)
WEST_SHA = (
    "6f11ae189a6ec58bde63eb52c2e7eba80"
    "b6ec4ffde1f0620f1dca95200542c31"
)

USCIS_MEMO = (
    "https://www.uscis.gov/sites/default/files/"
    "document/memos/H1B_Proc_Memo_FINAL.pdf"
)

MEMO_MARKERS = [
    "September 20, 2025",
    "September 21, 2025",
    "$100,000",
    "currently approved petitions",
    "validly issued H-1B",
]

WEST_NOTICE_URL = (
    "https://www.niied.go.kr/web/main/"
    "nid/niied_board/5570"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verified_read(path, expected):
    assert path.is_file(), f"파일 없음: {path}"
    data = path.read_bytes()
    assert sha256(data) == expected, (
        f"SHA-256 불일치: {path}"
    )
    return data


def read_jsonl(data):
    return [
        json.loads(line)
        for line in data.decode("utf-8").splitlines()
        if line.strip()
    ]


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def json_bytes(obj):
    return (
        json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


print("===== STEP 64-33 공식 근거 대조 =====")

# 1. 입력 검증
priority_raw = verified_read(SOURCE, SOURCE_SHA)
index_raw = verified_read(INDEX, INDEX_SHA)
west_raw = verified_read(WEST_PDF, WEST_SHA)

priority = read_jsonl(priority_raw)
index = json.loads(index_raw)

assert len(priority) == 13
assert index["total_chunks"] == 334

print("[PASS] 정책 13개·통합 인덱스·WEST PDF 무결성")

# 2. 전체 원본 검색 청크와 대조
all_chunks = {}
original_hashes = {
    SOURCE: SOURCE_SHA,
    INDEX: INDEX_SHA,
    WEST_PDF: WEST_SHA,
}

for entry in index["programs"]:
    path = ROOT / entry["retrieval_path"]
    raw = verified_read(path, entry["retrieval_sha256"])
    original_hashes[path] = entry["retrieval_sha256"]

    chunks = read_jsonl(raw)
    assert len(chunks) == entry["chunk_count"]

    for chunk in chunks:
        cid = chunk["chunk_id"]
        assert cid not in all_chunks
        all_chunks[cid] = chunk

assert len(all_chunks) == 334

for item in priority:
    cid = item["chunk_id"]
    assert cid in all_chunks

    original = all_chunks[cid]
    assert item["program_id"] == original["program_id"]
    assert item["source_url"] == original["source_url"]
    assert (
        item["source_text_sha256"]
        == original["text_sha256"]
    )

print("[PASS] 13개 청크와 보존된 공식 원문 대조")

# 3. WEST PDF 자체 확인
with fitz.open(stream=west_raw, filetype="pdf") as doc:
    assert len(doc) == 11

    west_text = normalize(
        " ".join(page.get_text() for page in doc)
    )

    assert "WEST" in west_text
    assert "2026" in west_text

print("[PASS] WEST 원본 PDF 구조·내용 확인")

# 4. USCIS 공식 메모 접근 시도
memo_result = {
    "url": USCIS_MEMO,
    "download_status": "unavailable",
    "pdf_sha256": None,
    "required_markers_found": [],
    "required_markers_missing": MEMO_MARKERS,
    "document_corrobation": False,
    "error": None,
}

try:
    request = urllib.request.Request(
        USCIS_MEMO,
        headers={
            "User-Agent": "Mozilla/5.0 "
                          "(compatible; GlobalInResearch/1.0)"
        },
    )

    with urllib.request.urlopen(
        request, timeout=20
    ) as response:
        memo_data = response.read(5_000_001)

    assert len(memo_data) <= 5_000_000

    with fitz.open(
        stream=memo_data,
        filetype="pdf"
    ) as doc:
        memo_text = normalize(
            " ".join(page.get_text() for page in doc)
        )

    found = [
        value for value in MEMO_MARKERS
        if normalize(value).lower()
        in memo_text.lower()
    ]

    missing = [
        value for value in MEMO_MARKERS
        if value not in found
    ]

    memo_result.update({
        "download_status": "downloaded",
        "pdf_sha256": sha256(memo_data),
        "required_markers_found": found,
        "required_markers_missing": missing,
        "document_corrobation": len(missing) == 0,
    })

    if missing:
        print("[REVIEW] USCIS 메모 일부 표시 항목 미확인")
    else:
        print("[PASS] USCIS 공식 메모 적용일·예외 문구 확인")

except Exception as exc:
    memo_result["error"] = (
        f"{type(exc).__name__}: {str(exc)[:200]}"
    )
    print("[REVIEW] USCIS 메모 다운로드 실패")
    print("사유:", memo_result["error"])

# 5. 청크별 검증 결과 작성
results = []

for item in priority:
    cid = item["chunk_id"]
    program = item["program_id"]

    is_west = program == "US-WEST-01"

    is_proclamation = (
        item["policy_category"]
        == "presidential_proclamation"
    )

    if is_west:
        status = "historical_source_confirmed"
        checked_reference = WEST_NOTICE_URL

    elif (
        is_proclamation
        and memo_result["document_corrobation"]
    ):
        status = "related_official_memo_confirmed"
        checked_reference = USCIS_MEMO

    else:
        status = "original_snapshot_only"
        checked_reference = None

    result = {
        "chunk_id": cid,
        "program_id": program,
        "policy_category": item["policy_category"],
        "verification_focus": item["verification_focus"],
        "source_url": item["source_url"],
        "source_text_sha256": (
            item["source_text_sha256"]
        ),
        "original_snapshot_match": True,
        "official_evidence_status": status,
        "corroborating_reference_url": checked_reference,
        "historical_only": is_west,
        "legal_application_scope_verified": False,
        "all_exceptions_verified": False,
        "current_policy_verified": False,
        "human_review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
    }

    results.append(result)

assert len(results) == 13

# 6. 보고서 작성
report = {
    "dataset_type": "usa_official_evidence_comparison",
    "country": "US",
    "total_reviewed": 13,
    "h1b_records": 10,
    "west_historical_records": 3,
    "input_scope_review_sha256": SOURCE_SHA,
    "original_snapshot_comparison": "pass",
    "west_pdf_sha256": WEST_SHA,
    "uscis_memo": memo_result,
    "records": results,
    "note": (
        "Document corroboration is not proof that "
        "a complete legal rule is currently applicable. "
        "All eligibility and answer approvals remain disabled."
    ),
    "legal_application_scope_verified": False,
    "current_policy_verified": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

payload = json_bytes(report)

# 7. 기존 결과 덮어쓰기 방지
assert REPORT.parent.is_dir()

if REPORT.exists():
    assert REPORT.read_bytes() == payload, (
        "기존 결과와 충돌합니다. "
        "보고서를 덮어쓰지 않았습니다."
    )
    state = "EXISTS_VERIFIED"
else:
    with REPORT.open("xb") as file:
        file.write(payload)
    state = "CREATED"

assert REPORT.read_bytes() == payload
assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == report

# 8. 원본 불변 확인
for path, expected_hash in original_hashes.items():
    assert sha256(path.read_bytes()) == expected_hash

print("[PASS] 보고서 저장·재읽기·기존 원본 불변")
print(f"[PASS] {state}: {REPORT.relative_to(ROOT)}")

print("\n===== STEP 64-33 최종 결과 =====")
print("공식 원본 청크 대조:", len(results))
print("WEST 원본 PDF: PASS")
print(
    "USCIS 메모:",
    memo_result["download_status"]
)
print(
    "USCIS 메모 주요 항목:",
    len(memo_result["required_markers_found"]),
    "/",
    len(MEMO_MARKERS),
)
print("보고서:", REPORT.relative_to(ROOT))
print("SHA-256:", sha256(payload))
print("정책의 전체 현행성 검증: 미완료")
print("답변 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")