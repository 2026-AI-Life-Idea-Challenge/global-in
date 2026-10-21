
from pathlib import Path
import hashlib
import json
import re

# 파일 위치: scripts/ingest/usa/employment/west/
ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT
    / "data/processed/usa/employment/west/2026_second_half"
)

SOURCE = BASE / "west_2026_second_half_structured_draft.json"
OUTPUT = BASE / "west_2026_second_half_eligibility_review.json"
AUDIT = BASE / "west_2026_second_half_eligibility_audit.json"

EXPECTED_DRAFT_SHA = (
    "977cd6b2d0fc2ac9f88b3c75027ac0c"
    "e665b1a38a37cb92339b4b8870fffbe9e"
)

EXPECTED_PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

# 27개 원래 필드 중 지원 자격과 관련된 항목
FIELD_PATTERNS = {
    "short_term_capacity": [
        r"단기", r"모집\s*인원", r"선발\s*인원", r"\d+\s*명",
    ],
    "medium_term_capacity": [
        r"중기", r"모집\s*인원", r"선발\s*인원", r"\d+\s*명",
    ],
    "academic_status_eligibility": [
        r"재학생", r"휴학생", r"졸업생",
        r"졸업예정자", r"학적", r"지원\s*자격",
    ],
    "graduation_date_conditions": [
        r"졸업", r"졸업\s*예정", r"졸업\s*시점",
        r"학위", r"졸업\s*증명",
    ],
    "language_score_requirements": [
        r"어학", r"영어", r"TOEIC", r"토익",
        r"G[\s-]?TELP", r"OPIc",
        r"Speaking", r"스피킹",
    ],
}

# 어학성적은 원래 필드의 세부 검수 항목으로 분리
LANGUAGE_PATTERNS = {
    "toeic": [
        r"\bTOEIC\b(?!\s*Speaking)", r"토익",
    ],
    "gtelp_level2": [
        r"G[\s-]?TELP", r"지텔프", r"Level\s*2",
    ],
    "opic": [
        r"OPIc", r"오픽", r"\bIM[1-3]\b",
    ],
    "toeic_speaking": [
        r"TOEIC\s*Speaking", r"토익\s*스피킹",
        r"토익\s*말하기",
    ],
    "gtelp_speaking": [
        r"G[\s-]?TELP\s*Speaking",
        r"지텔프\s*스피킹",
    ],
}

MAX_CANDIDATES_PER_FIELD = 18
CONTEXT_BEFORE = 100
CONTEXT_AFTER = 180


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def load_verified_source():
    if not SOURCE.is_file():
        raise FileNotFoundError(f"입력 파일 없음: {SOURCE}")

    raw = SOURCE.read_bytes()
    actual = sha256(raw)

    if actual != EXPECTED_DRAFT_SHA:
        raise ValueError(
            "STEP 64-50 입력 파일의 SHA-256이 다릅니다.\n"
            f"예상: {EXPECTED_DRAFT_SHA}\n"
            f"실제: {actual}"
        )

    return json.loads(raw.decode("utf-8")), actual


def collect_pages(data):
    """
    STEP 64-50에서 주제별로 묶어둔 페이지를
    다시 전체 22페이지 단위로 재구성한다.

    주제별 임시 분류에 의존하지 않고
    모든 페이지를 검색하도록 한다.
    """
    pages = {}

    for section in data["sections"].values():
        for page in section["evidence_pages"]:
            number = page["logical_page_candidate"]

            if number in pages:
                raise ValueError(
                    f"중복 논리 페이지: {number}"
                )

            text = page["source_text"]

            if sha256(text.encode("utf-8")) != (
                page["source_text_sha256"]
            ):
                raise ValueError(
                    f"본문 SHA-256 불일치: {number}"
                )

            pages[number] = page

    if set(pages) != set(range(1, 23)):
        raise ValueError(
            f"논리 페이지 구성 오류: {sorted(pages)}"
        )

    return [pages[n] for n in sorted(pages)]


def extract_candidates(pages, patterns):
    found = []
    seen = set()

    for page in pages:
        text = page["source_text"]
        number = page["logical_page_candidate"]

        for pattern in patterns:
            for match in re.finditer(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                start = max(
                    0, match.start() - CONTEXT_BEFORE
                )
                end = min(
                    len(text),
                    match.end() + CONTEXT_AFTER
                )

                snippet = text[start:end].strip()

                # 같은 페이지의 동일 문구는 중복 제거
                key = (
                    number,
                    re.sub(r"\s+", " ", snippet),
                )

                if key in seen:
                    continue

                seen.add(key)

                found.append({
                    "logical_page": number,
                    "physical_pdf_page": (
                        page["physical_pdf_page"]
                    ),
                    "side": page["side"],
                    "matched_pattern": pattern,
                    "matched_text": match.group(),
                    "source_offset_start": start,
                    "source_offset_end": end,
                    "source_excerpt": snippet,
                    "source_text_sha256": (
                        page["source_text_sha256"]
                    ),
                    "candidate_id": page["candidate_id"],
                    "source_block_ids": (
                        page["source_block_ids"]
                    ),
                    "evidence_status": "candidate_only",
                })

    # 앞에 나온 페이지부터 확인할 수 있도록 정렬
    found.sort(
        key=lambda item: (
            item["logical_page"],
            item["source_offset_start"],
        )
    )

    total_matches = len(found)

    return {
        "candidate_count_total": total_matches,
        "candidate_count_included": min(
            total_matches, MAX_CANDIDATES_PER_FIELD
        ),
        "truncated": (
            total_matches > MAX_CANDIDATES_PER_FIELD
        ),
        "candidate_evidence": (
            found[:MAX_CANDIDATES_PER_FIELD]
        ),
    }


def build_review_item(field, patterns, pages):
    result = extract_candidates(pages, patterns)

    return {
        "field": field,
        "value": None,
        "validation_status": "needs_review",
        "semantic_verification_completed": False,
        "short_term_value": None,
        "medium_term_value": None,
        "table_row_column_alignment_verified": False,
        "reviewer_notes": None,
        **result,
    }


def encode_json(data):
    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def write_new_or_verify(path, data):
    raw = encode_json(data)

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                "기존 결과가 달라 덮어쓰지 않습니다: "
                + str(path)
            )
        return "EXISTS_VERIFIED", sha256(raw)

    with path.open("xb") as f:
        f.write(raw)

    return "CREATED", sha256(raw)


print("===== STEP 64-51 지원 자격·어학성적 근거 추출 =====")
print("프로젝트:", ROOT)

# 1. 원본 무결성 확인
data, draft_sha = load_verified_source()

assert data["program_id"] == "US-WEST-01"
assert data["notice_period"] == "2026_second_half"
assert data["source_pdf_sha256"] == EXPECTED_PDF_SHA
assert data["approved_for_user_answers"] is False
assert data["approved_for_embedding"] is False

pages = collect_pages(data)

print("[PASS] STEP 64-50 결과 SHA-256")
print("[PASS] WEST 하반기 22페이지 본문 검증")

# 2. 5개 정책 필드 전체 페이지 검색
policy_fields = {}

for field, patterns in FIELD_PATTERNS.items():
    policy_fields[field] = build_review_item(
        field, patterns, pages
    )

    print(
        f"[FIELD] {field}: "
        f"{policy_fields[field]['candidate_count_total']}건"
    )

# 3. 세부 어학시험별 근거 후보 추출
language_fields = {}

for field, patterns in LANGUAGE_PATTERNS.items():
    language_fields[field] = build_review_item(
        field, patterns, pages
    )

    print(
        f"[LANG] {field}: "
        f"{language_fields[field]['candidate_count_total']}건"
    )

# 4. 검토용 JSON 구성
review = {
    "dataset_type": "west_eligibility_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_sha256": EXPECTED_PDF_SHA,
    "structured_draft_sha256": draft_sha,
    "searched_logical_pages": list(range(1, 23)),
    "policy_fields": policy_fields,
    "language_subfields": language_fields,
    "review_guidelines": {
        "short_medium_must_be_separated": True,
        "general_and_speaking_scores_must_be_separated": True,
        "academic_status_exceptions_must_be_checked": True,
        "source_table_alignment_required": True,
        "historical_notice_not_current_policy": True,
    },
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_eligibility_extraction_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "searched_pages": 22,
    "policy_fields": len(policy_fields),
    "language_subfields": len(language_fields),
    "total_candidate_matches": sum(
        item["candidate_count_total"]
        for item in (
            list(policy_fields.values())
            + list(language_fields.values())
        )
    ),
    "fields_without_candidates": [
        field
        for field, item in {
            **policy_fields,
            **language_fields,
        }.items()
        if item["candidate_count_total"] == 0
    ],
    "fields_with_truncated_candidates": [
        field
        for field, item in {
            **policy_fields,
            **language_fields,
        }.items()
        if item["truncated"]
    ],
    "policy_values_confirmed": 0,
    "input_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 5. 결과 저장
review_state, review_sha = write_new_or_verify(
    OUTPUT, review
)

audit["review_file_sha256"] = review_sha

audit_state, audit_sha = write_new_or_verify(
    AUDIT, audit
)

# 6. 결과 확인
assert sha256(OUTPUT.read_bytes()) == review_sha
assert sha256(AUDIT.read_bytes()) == audit_sha
assert sha256(SOURCE.read_bytes()) == draft_sha

print("\n===== STEP 64-51 최종 결과 =====")
print("근거 검색 페이지:", len(pages))
print("정책 검수 필드:", len(policy_fields))
print("세부 어학 검수 필드:", len(language_fields))
print("총 근거 후보 검색 결과:", audit["total_candidate_matches"])
print(
    "근거 후보 없는 항목:",
    audit["fields_without_candidates"]
)
print(
    "검색 결과 일부만 수록된 항목:",
    audit["fields_with_truncated_candidates"]
)
print("정책값 확정:", 0)
print("원본 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")

print(f"[PASS] {review_state}: {OUTPUT.name}")
print("SHA-256:", review_sha)

print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)