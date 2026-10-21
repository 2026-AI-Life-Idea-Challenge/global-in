
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa/employment/west"

INVENTORY = BASE / "west_2026_first_half_evidence_inventory.json"
REVIEW = BASE / "west_2026_first_half_review_package.json"
OUTPUT = BASE / "west_2026_first_half_program_draft.json"

EXPECTED_INVENTORY_SHA = (
    "0312dffcc92914630f8b597b70efdb7fbb"
    "ffc3b2cc222ed7d312ebff01343cdd"
)

EXPECTED_REVIEW_SHA = (
    "cc0de9999cef6ee38ec106612f84274d"
    "bca0ceb203776911cd1df40d87b5d0ca"
)

# 검토하고 싶은 핵심 정보의 검색어.
# 검색어는 법적 요건을 의미하지 않음.
FIELD_QUERIES = {
    "program_overview": {
        "program_name": ["WEST(Work", "한․미 대학생 연수"],
        "program_types": ["단기 WEST", "중기 WEST"],
        "program_composition": ["어학연수", "인턴"],
    },
    "eligibility": {
        "nationality": ["대한민국 국적"],
        "student_status": ["재·휴학생", "졸업생"],
        "english_scores": ["TOEIC", "OPIc", "G-TELP"],
        "restrictions": ["지원 제한", "복수 국적자"],
    },
    "documents": {
        "application_documents": [
            "자기소개서",
            "개인정보동의서",
            "성적증명서",
            "공인영어성적",
        ],
        "university_recommendation": [
            "추천 공문",
            "소속 대학",
        ],
    },
    "application": {
        "recruitment_dates": ["신청 기간", "2. 11.", "3. 18."],
        "online_application": ["월드잡플러스", "온라인 지원"],
        "submission_procedure": ["서류 제출"],
    },
    "cost_and_support": {
        "participation_fees": ["참가비"],
        "government_support": ["정부재정지원"],
        "living_expenses": ["생활비"],
        "financial_support_brackets": ["지원구간"],
    },
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def serialize(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def searchable_pattern(keyword):
    # 공백과 줄바꿈 차이를 허용하면서
    # 원문에서 실제 위치를 반환한다.
    parts = [re.escape(char) for char in keyword if not char.isspace()]
    return re.compile(r"\s*".join(parts), re.IGNORECASE)


def find_evidence(pages, keywords):
    matches = []
    seen = set()

    for page in pages:
        text = page["text"]

        for keyword in keywords:
            found = searchable_pattern(keyword).search(text)

            if not found:
                continue

            key = (page["logical_page_candidate"], keyword)
            if key in seen:
                continue

            seen.add(key)

            start = max(0, found.start() - 180)
            end = min(len(text), found.end() + 420)

            matches.append({
                "search_keyword": keyword,
                "physical_pdf_page": page[
                    "physical_pdf_page"
                ],
                "logical_page_candidate": page[
                    "logical_page_candidate"
                ],
                "side": page["side"],
                "source_excerpt": text[start:end].strip(),
                "source_page_sha256": page["text_sha256"],
                "value_verified": False,
                "table_relationship_verified": False,
            })

    return matches


def build_draft(inventory):
    pages = inventory["logical_pages"]
    sections = {}
    missing = []

    for section_name, fields in FIELD_QUERIES.items():
        section_data = {}

        for field_name, keywords in fields.items():
            evidence = find_evidence(pages, keywords)

            if not evidence:
                missing.append(
                    f"{section_name}.{field_name}"
                )

            section_data[field_name] = {
                "status": (
                    "evidence_found_needs_review"
                    if evidence
                    else "evidence_not_found"
                ),
                "extracted_value": None,
                "evidence_count": len(evidence),
                "evidence": evidence,
            }

        sections[section_name] = section_data

    return {
        "dataset_type": "program_information_draft",
        "country": "US",
        "program_id": "US-WEST-01",
        "route_id": "US-EM",
        "program_name": (
            "WEST (Work, English Study, Travel)"
        ),
        "notice_id": "NIIED-2026-15",
        "notice_period": "2026_first_half",
        "historical_notice": True,
        "source_inventory_sha256": EXPECTED_INVENTORY_SHA,
        "source_review_package_sha256": EXPECTED_REVIEW_SHA,
        "source_pdf_path": (
            "data/raw/usa/employment/west/"
            "west_2026_first_half_notice.pdf"
        ),
        "fields": sections,
        "missing_evidence_fields": missing,
        "table_review_priorities": [
            "short_vs_mid_term_english_scores",
            "short_vs_mid_term_program_duration",
            "financial_support_bracket_amounts",
            "required_vs_conditional_documents",
        ],
        "current_application_status": "not_verified",
        "manual_review_required": True,
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
        "recommendation_rules_enabled": False,
        "embedding_generated": False,
    }


print("===== STEP 64-11 WEST 프로그램 정보 구조화 =====")

# 1. 입력 데이터 검증
inventory_raw = INVENTORY.read_bytes()
review_raw = REVIEW.read_bytes()

assert sha256(inventory_raw) == EXPECTED_INVENTORY_SHA
assert sha256(review_raw) == EXPECTED_REVIEW_SHA

inventory = json.loads(
    inventory_raw.decode("utf-8")
)
review = json.loads(
    review_raw.decode("utf-8")
)

assert inventory["program_id"] == "US-WEST-01"
assert review["program_id"] == "US-WEST-01"
assert inventory["logical_page_candidate_count"] == 22
assert inventory["source_block_count"] == 577
assert review["unique_evidence_block_count"] == 241

# 두 입력 파일이 동일한 원본 체계를 참조하는지 확인
assert review["source_inventory_sha256"] == (
    EXPECTED_INVENTORY_SHA
)

print("[PASS] Inventory / Review Package SHA-256")
print("[PASS] 프로그램 및 근거 연결")

# 2. 구조화 초안 생성
draft = build_draft(inventory)

assert draft["validation_status"] == "needs_review"
assert draft["automatic_eligibility_rules_enabled"] is False
assert draft["recommendation_rules_enabled"] is False

# 3. 재현성 검사
payload = serialize(draft)
replay_payload = serialize(build_draft(inventory))
assert payload == replay_payload

print("[PASS] 구조화 초안 생성 및 재현성")

# 4. 출처 근거 일치 검사
page_by_id = {
    p["logical_page_candidate"]: p
    for p in inventory["logical_pages"]
}

total_fields = 0
fields_with_evidence = 0
total_evidence = 0

for section in draft["fields"].values():
    for field in section.values():
        total_fields += 1

        if field["evidence_count"] > 0:
            fields_with_evidence += 1

        assert field["extracted_value"] is None

        for evidence in field["evidence"]:
            page = page_by_id[
                evidence["logical_page_candidate"]
            ]

            assert evidence["source_page_sha256"] == (
                page["text_sha256"]
            )

            assert evidence["source_excerpt"] in (
                page["text"]
            )

            assert searchable_pattern(
                evidence["search_keyword"]
            ).search(page["text"])

            total_evidence += 1

print("[PASS] 근거 원문·페이지·SHA-256 대조")

# 5. 기존 출력 덮어쓰기 방지
assert not OUTPUT.exists(), (
    "기존 프로그램 초안이 존재합니다."
)

with OUTPUT.open("xb") as f:
    f.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == draft

print("[PASS] 프로그램 초안 JSON 저장·재읽기")

# 6. 기존 원본 불변
assert INVENTORY.read_bytes() == inventory_raw
assert REVIEW.read_bytes() == review_raw

print("[PASS] 기존 원본 불변")

# 7. 결과 요약
print("\n[섹션별 필드 현황]")

for section_name, fields in draft["fields"].items():
    populated = sum(
        field["evidence_count"] > 0
        for field in fields.values()
    )

    print(
        section_name,
        f"| 근거 발견 {populated}/{len(fields)}"
    )

print("\n[근거 미발견 필드]")
if draft["missing_evidence_fields"]:
    for name in draft["missing_evidence_fields"]:
        print("-", name)
else:
    print("없음")

print("\n===== STEP 64-11 최종 결과 =====")
print("전체 정보 필드:", total_fields)
print("근거 발견 필드:", fields_with_evidence)
print("근거 연결 건수:", total_evidence)
print("출력:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", sha256(payload))
print("원본 무결성: PASS")
print("재현성: PASS")
print("근거 연결: PASS")
print("표 열 대응 검증: 미완료")
print("자격·서류 조건 승인: 미완료")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")