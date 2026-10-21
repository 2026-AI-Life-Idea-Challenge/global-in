
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa"

INDEX = BASE / "shared/usa_retrieval_index.json"
OUTPUT = BASE / "shared/usa_retrieval_quality_audit.json"

EXPECTED_INDEX_SHA = (
    "a5b801fd23d914861f04b51916e035"
    "f82e9c854fe3ad1353542bb80933d01c7a"
)

NOISE_PATTERNS = {
    "cookie_or_privacy_banner": [
        r"\bcookie preferences?\b",
        r"\baccept all cookies\b",
        r"\bmanage cookies\b",
    ],
    "navigation_or_website_ui": [
        r"\bskip to (main )?content\b",
        r"\bback to top\b",
        r"\bshare this page\b",
        r"\bfollow us on\b",
    ],
    "unrelated_site_function": [
        r"\bsign up for our newsletter\b",
        r"\bsubscribe to updates\b",
    ],
}

# 이 페이지는 표가 포함되어 있으므로
# PDF 추출 텍스트만으로 조건을 확정하지 않는다.
WEST_TABLE_PAGES = {2, 4, 6, 7, 9, 10}

HIGH_RISK_PATTERNS = [
    r"\b(?:must|required|eligible|ineligible)\b",
    r"\b(?:shall|prohibited|exempt)\b",
    r"지원\s*자격",
    r"지원\s*제한",
    r"제출\s*서류",
    r"정부\s*지원",
    r"참가비",
    r"비자",
]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def serialize(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def read_checked(path, expected):
    raw = path.read_bytes()
    assert sha256(raw) == expected, (
        f"SHA-256 불일치: {path}"
    )
    return raw


def reconstruct_unit(parts):
    parts = sorted(
        parts,
        key=lambda r: r["char_start"]
    )

    assert parts[0]["char_start"] == 0

    assembled = ""
    previous_end = 0

    for part in parts:
        start = part["char_start"]
        end = part["char_end"]
        text = part["text"]

        assert end - start == len(text)
        assert start <= previous_end
        assert end > previous_end

        if start < previous_end:
            overlap = previous_end - start

            assert assembled[start:previous_end] == (
                text[:overlap]
            )

            assembled += text[overlap:]
        else:
            assembled += text

        previous_end = end

    expected_sha = parts[0]["unit_text_sha256"]
    assert all(
        p["unit_text_sha256"] == expected_sha
        for p in parts
    )
    assert sha256(assembled.encode("utf-8")) == (
        expected_sha
    )

    return assembled


print("===== STEP 64-22 미국 RAG 품질 감사 =====")

assert not OUTPUT.exists(), (
    f"기존 감사 리포트가 존재합니다: {OUTPUT}"
)

index_raw = read_checked(
    INDEX, EXPECTED_INDEX_SHA
)
index = json.loads(index_raw.decode("utf-8"))

assert index["program_count"] == 7
assert index["total_chunks"] == 334
assert index["automatic_eligibility_rules_enabled"] is False

print("[PASS] 통합 인덱스 SHA-256")

all_chunks = []
input_hashes = {INDEX: EXPECTED_INDEX_SHA}
program_results = []

for entry in index["programs"]:
    program_id = entry["program_id"]
    path = ROOT / entry["retrieval_path"]

    assert path.resolve().is_relative_to(
        BASE.resolve()
    )
    assert path.suffix == ".jsonl"

    raw = read_checked(
        path, entry["retrieval_sha256"]
    )
    input_hashes[path] = entry["retrieval_sha256"]

    chunks = [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]

    assert len(chunks) == entry["chunk_count"]

    units = defaultdict(list)

    for chunk in chunks:
        assert chunk["program_id"] == program_id
        assert chunk["country"] == "US"
        assert (
            chunk["automatic_eligibility_rules_enabled"]
            is False
        )
        assert chunk["eligibility_rule_verified"] is False

        assert sha256(
            chunk["text"].encode("utf-8")
        ) == chunk["text_sha256"]

        assert len(chunk["text"]) <= 1400
        assert chunk["char_end"] > chunk["char_start"]

        units[chunk["evidence_unit_id"]].append(
            chunk
        )

    assert len(units) == (
        entry["unique_evidence_units"]
    )

    # 중첩 청크를 재조립하여 원래 근거 단위의
    # SHA-256과 일치하는지 독립적으로 검사한다.
    for unit_chunks in units.values():
        reconstruct_unit(unit_chunks)

    program_results.append({
        "program_id": program_id,
        "chunk_count": len(chunks),
        "unit_count": len(units),
        "source_sha256_verified": True,
        "unit_reconstruction": "pass",
    })

    all_chunks.extend(chunks)

    print(
        f"[PASS] {program_id}: "
        f"{len(chunks)}개 청크, "
        f"{len(units)}개 근거 원문 복원"
    )

assert len(all_chunks) == 334

ids = [c["chunk_id"] for c in all_chunks]
assert len(ids) == len(set(ids))

print("[PASS] 전체 334개 청크 및 ID 유일성")

# 2. 품질 점검
flags = []
text_occurrences = defaultdict(list)

for chunk in all_chunks:
    text_occurrences[
        chunk["text_sha256"]
    ].append(chunk)

    reasons = []
    text = chunk["text"]

    if len(text.strip()) < 80:
        reasons.append("short_chunk")

    for category, patterns in NOISE_PATTERNS.items():
        if any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        ):
            reasons.append(category)

    if (
        chunk["program_id"] == "US-WEST-01"
        and chunk["printed_page_candidate"]
        in WEST_TABLE_PAGES
    ):
        reasons.append(
            "pdf_table_layout_manual_review"
        )

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in HIGH_RISK_PATTERNS
    ):
        reasons.append(
            "potential_eligibility_or_legal_claim"
        )

    if reasons:
        flags.append({
            "chunk_id": chunk["chunk_id"],
            "program_id": chunk["program_id"],
            "source_url": chunk["source_url"],
            "reasons": sorted(set(reasons)),
            "text_length": len(text),
            "text_preview": text[:180],
        })

duplicates = []

for text_sha, occurrences in text_occurrences.items():
    if len(occurrences) > 1:
        duplicates.append({
            "text_sha256": text_sha,
            "chunk_ids": [
                c["chunk_id"] for c in occurrences
            ],
            "program_ids": sorted({
                c["program_id"] for c in occurrences
            }),
        })

reason_counts = dict(sorted(Counter(
    reason
    for item in flags
    for reason in item["reasons"]
).items()))

flagged_program_counts = dict(sorted(Counter(
    item["program_id"]
    for item in flags
).items()))

# 3. 품질 감사 리포트
audit = {
    "dataset_type": "usa_retrieval_quality_audit",
    "country": "US",
    "retrieval_index_sha256": EXPECTED_INDEX_SHA,
    "program_count": len(program_results),
    "total_chunks": len(all_chunks),
    "unique_chunk_ids": len(set(ids)),
    "total_flagged_chunks": len(flags),
    "exact_duplicate_text_groups": len(duplicates),
    "reason_counts": reason_counts,
    "flagged_program_counts": flagged_program_counts,
    "programs": program_results,
    "flags": flags,
    "duplicate_groups": duplicates,
    "validation": {
        "sha256": "pass",
        "chunk_ids": "pass",
        "unit_reconstruction": "pass",
        "quality_review": "needs_review",
    },
    "flag_semantics": (
        "Flags indicate candidates for manual review, "
        "not confirmed errors."
    ),
    "eligibility_claims_approved": False,
    "automatic_eligibility_rules_enabled": False,
    "embedding_generated": False,
    "database_loaded": False,
}

payload = serialize(audit)

# 저장 이전 JSON 직렬화 재현성 검사
assert payload == serialize(audit)

with OUTPUT.open("xb") as file:
    file.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == audit

for path, original_hash in input_hashes.items():
    assert sha256(path.read_bytes()) == original_hash

print("[PASS] 품질 감사 리포트 저장·재읽기")
print("[PASS] 기존 검색 JSONL·인덱스 불변")

print("\n===== STEP 64-22 최종 결과 =====")
print("전체 프로그램:", audit["program_count"])
print("전체 청크:", audit["total_chunks"])
print("청크 ID 검증: PASS")
print("원문 복원 검증: PASS")
print("검토 표시된 청크:", audit["total_flagged_chunks"])
print("동일 텍스트 중복 그룹:", audit["exact_duplicate_text_groups"])
print("검토 사유별 수량:", audit["reason_counts"])
print("프로그램별 검토 수량:", audit["flagged_program_counts"])
print("감사 리포트:", OUTPUT.relative_to(ROOT))
print("SHA-256:", sha256(payload))
print("기존 데이터 변경: 없음")
print("검색 품질 검수: needs_review")
print("자동 자격 판정: 비활성화")
print("임베딩 생성: 미실행")
print("DB 적재: 미실행")
print("Git 커밋·푸시: 미실행")