
import json
import hashlib
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa/employment/west/2026_second_half"
PDF = ROOT / "data/raw/usa/employment/west/2026_second_half/west_2026_second_half_notice.pdf"
OUTPUT = ROOT / "data/processed/legal_review/west_h2_legal_review_consolidated_20261028.json"

def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8-sig"))

readiness = load("west_2026_second_half_readiness_audit.json")
findings = load("west_2026_second_half_pdf_findings.json")
remaining = load("west_2026_second_half_remaining_fields_audit.json")
semantic = load("west_2026_second_half_semantic_review_audit.json")
final = load("west_2026_h2_final_review_draft.json")

pdf_hash = hashlib.sha256(PDF.read_bytes()).hexdigest()
assert pdf_hash == readiness["source_pdf_sha256"]
assert pdf_hash == findings["source_pdf_sha256"]
assert pdf_hash == remaining["input_pdf_sha256"]

issues = readiness["issue_tracking"]
ids = [x["record_id"] for x in issues]
assert len(ids) == len(set(ids)) == 25
assert len(ids) == semantic["issue_records"]
assert remaining["remaining_fields_with_evidence"] == 7
assert final["structural_checks"]["original_policy_field_count"] == 27

groups = {
    "J1_212E": [
        "WEST-H2-SELECTION-05"
    ],
    "GRADUATION_DATES": [
        "WEST-H2-ACADEMIC-02",
        "WEST-H2-ELIGIBILITY-02"
    ],
    "ACADEMIC_LOANS": [
        "WEST-H2-ACADEMIC-03",
        "WEST-H2-APPLICATION-02",
        "WEST-H2-FINANCIAL-04",
        "WEST-H2-SELECTION-02",
        "WEST-H2-SELECTION-03"
    ],
    "GRADUATE_FINANCIAL_DOCUMENTS": [
        "WEST-H2-ACADEMIC-04",
        "WEST-H2-ACADEMIC-05",
        "WEST-H2-APPLICATION-03",
        "WEST-H2-DOCUMENTS-02",
        "WEST-H2-FINANCIAL-02"
    ],
    "FINANCIAL_AMOUNTS": [
        "WEST-H2-FINANCIAL-01",
        "WEST-H2-FINANCIAL-03"
    ],
    "FAQ_Q3_DISCREPANCY": [
        "WEST-H2-ACADEMIC-01",
        "WEST-H2-ELIGIBILITY-01",
        "WEST-H2-SELECTION-04"
    ],
    "DOCUMENTS_AND_SCORES": [
        "WEST-H2-DOCUMENTS-01",
        "WEST-H2-DOCUMENTS-03",
        "WEST-H2-DOCUMENTS-04"
    ],
    "PROCEDURES_AND_FAQ": [
        "WEST-H2-APPLICATION-01",
        "WEST-H2-ELIGIBILITY-03",
        "WEST-H2-SELECTION-01",
        "WEST-H2-SELECTION-06"
    ]
}

group_by_id = {
    issue_id: group
    for group, members in groups.items()
    for issue_id in members
}

assert len(group_by_id) == 25
assert set(group_by_id) == set(ids)

finding_by_issue = {}
for finding in findings["findings"]:
    for issue_id in finding["issue_ids"]:
        assert issue_id in group_by_id
        finding_by_issue.setdefault(issue_id, []).append(
            finding["finding_id"]
        )

notes = {
    "J1_212E": (
        "미국 국무부 자료에서 정부재정지원 등 INA 212(e) 적용 사유 확인. "
        "WEST 공고 FAQ와 구분하여 개인별 적용 여부 및 면제 판단은 보류."
    ),
    "GRADUATION_DATES": (
        "2026년 하반기 공고는 2026년 2월·8월 졸업자를 명시. "
        "개인별 실제 어학연수 시작일은 기관별 일정 확인 필요."
    ),
    "ACADEMIC_LOANS": (
        "학자금 지원구간 확인 신청과 실제 대출 실행은 서로 다른 절차. "
        "학적·등록 여부에 따른 조건부 적용 유지."
    ),
    "GRADUATE_FINANCIAL_DOCUMENTS": (
        "졸업생 증빙은 기초·차상위 증명서, 지원구간 통지서, "
        "신청증명서 등 개인별 상황에 따라 분기."
    ),
    "FINANCIAL_AMOUNTS": (
        "공고상 2026년 기준환율과 최대 지원액은 확인. "
        "실제 지급액 및 반올림 기준은 별도 검증 필요."
    ),
    "FAQ_Q3_DISCREPANCY": (
        "하반기 공식 공고 FAQ Q3에 '상반기 선발' 문구 존재. "
        "원문 불일치 확인. 발행기관의 정정 여부는 미확정."
    ),
    "DOCUMENTS_AND_SCORES": (
        "제출서류·시험별 식별번호 자료 존재. "
        "TOEIC Speaking 환산표 전체 검증 및 개별 서류 진위 판단은 보류."
    ),
    "PROCEDURES_AND_FAQ": (
        "신청·선발 일정은 2026년 하반기 회차에 한정. "
        "대학별 개별 마감일과 후속 변경, FAQ 의미 최종 승인 보류."
    )
}

result = {
    "dataset_type": "west_h2_consolidated_legal_review",
    "program_id": "US:US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_sha256": pdf_hash,
    "source_pdf": str(PDF.relative_to(ROOT)).replace("\\", "/"),
    "source_integrity_verified": True,
    "issue_count": 25,
    "review_group_count": len(groups),
    "issue_groups": [
        {
            "group_id": group,
            "issue_count": len(members),
            "issue_ids": members,
            "review_note": notes[group],
            "review_status": "needs_review"
        }
        for group, members in groups.items()
    ],
    "issues": [
        {
            "record_id": item["record_id"],
            "priority": item["suggested_priority"],
            "title": item["title"],
            "group_id": group_by_id[item["record_id"]],
            "source_finding_ids": finding_by_issue.get(
                item["record_id"], []
            ),
            "source_review_note": notes[
                group_by_id[item["record_id"]]
            ],
            "resolved": False,
            "semantic_review_completed": False,
            "review_status": "needs_review"
        }
        for item in issues
    ],
    "official_legal_references": [
        {
            "topic": "INA 212(e)",
            "url": "https://travel.state.gov/content/travel/en/us-visas/study/exchange/waiver-of-the-exchange-visitor/eligibility.html",
            "purpose": "2년 본국 거주의무의 적용 사유 검증",
            "individual_applicability_verified": False
        },
        {
            "topic": "Advisory Opinion",
            "url": "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/advisory-opinions.html",
            "purpose": "개인별 적용 여부 확인 절차"
        }
    ],
    "legal_validation_approved": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "approved_for_eligibility_decision": False,
    "automatic_eligibility_rules_enabled": False,
    "database_changed": False,
    "original_review_files_modified": False
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8"
)

saved = json.loads(OUTPUT.read_text(encoding="utf-8"))
assert len(saved["issues"]) == 25
assert len(saved["issue_groups"]) == 8
assert not saved["legal_validation_approved"]

print("=== WEST H2 CONSOLIDATED REVIEW ===")
print("SOURCE_HASH: PASS")
print("ISSUES: 25/25")
print("GROUPS: 8/8")
print("FINDING_LINKS:", sum(
    bool(x["source_finding_ids"]) for x in saved["issues"]
))
print("PRIORITIES:", dict(Counter(
    x["priority"] for x in saved["issues"]
)))
print("LEGAL_APPROVED:", saved["legal_validation_approved"])
print("DB_CHANGED:", saved["database_changed"])
print("OUTPUT:", OUTPUT.relative_to(ROOT))
print("RESULT: PASS")


# WEST H2 official-source substantive review
# Preserve original issues and all approval gates.

official_sources = {
    "niied": {
        "url": "https://www.niied.go.kr/web/niied/nid/niied_board/5749",
        "scope": "2026_second_half_notice",
    },
    "kosaf_application": {
        "url": "https://www.kosaf.go.kr/ko/notice.do?mode=view&seqNo=21036",
        "scope": "2026_second_half_application",
    },
    "kosaf_successful_applicants": {
        "url": "https://www.kosaf.go.kr/ko/notice.do?mode=view&seqNo=21386",
        "scope": "2026_second_half_post_selection",
    },
    "us_dos_212e": {
        "url": "https://travel.state.gov/content/travel/en/us-visas/study/exchange/waiver-of-the-exchange-visitor/eligibility.html",
        "scope": "general_j1_legal_rule",
    },
    "us_dos_advisory": {
        "url": "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/advisory-opinions.html",
        "scope": "individual_applicability_procedure",
    },
}

decisions = {
    "J1_212E": {
        "source_keys": ["niied", "us_dos_212e", "us_dos_advisory"],
        "verified_facts": [
            "Government financing is a ground for INA 212(e).",
            "Not every J-1 visitor is automatically subject.",
            "Advisory Opinion can assess individual applicability.",
        ],
        "outstanding": [
            "Individual funding and immigration records",
            "Individual waiver or satisfaction of requirement",
        ],
    },
    "GRADUATION_DATES": {
        "source_keys": ["niied"],
        "verified_facts": [
            "H2 notice lists February and August 2026 graduates.",
            "The one-year condition depends on language-program start.",
        ],
        "outstanding": ["Actual start date for each sponsor"],
    },
    "ACADEMIC_LOANS": {
        "source_keys": ["niied", "kosaf_application"],
        "verified_facts": [
            "Support-bracket application is separate from loan execution.",
            "Graduate applicants are excluded from KOSAF application.",
            "H2 KOSAF application period was July 6-August 5, 2026.",
        ],
        "outstanding": [
            "Individual registration and loan-execution eligibility",
        ],
    },
    "GRADUATE_FINANCIAL_DOCUMENTS": {
        "source_keys": ["niied", "kosaf_application"],
        "verified_facts": [
            "Graduate evidence follows conditional document branches.",
            "Existing support-bracket notice and alternative certificates differ.",
        ],
        "outstanding": [
            "Applicant-specific document validity and bracket",
        ],
    },
    "FINANCIAL_AMOUNTS": {
        "source_keys": ["niied", "kosaf_successful_applicants"],
        "verified_facts": [
            "The notice uses a 2026 reference rate of KRW 1,472/USD.",
            "Published support totals are maximum amounts, not guarantees.",
        ],
        "outstanding": [
            "Actual disbursement rate, period, and rounding basis",
        ],
    },
    "FAQ_Q3_DISCREPANCY": {
        "source_keys": ["niied"],
        "verified_facts": [
            "The H2 notice FAQ Q3 refers to first-half selection.",
            "This is a confirmed inconsistency in the source text.",
        ],
        "outstanding": ["Official correction or clarification"],
    },
    "DOCUMENTS_AND_SCORES": {
        "source_keys": ["niied"],
        "verified_facts": [
            "The notice lists evidence types and score identifiers.",
            "The notice contains a TOEIC Speaking ACTFL conversion table.",
        ],
        "outstanding": [
            "Full independent table verification",
            "Authenticity of individual score reports",
        ],
    },
    "PROCEDURES_AND_FAQ": {
        "source_keys": ["niied", "kosaf_successful_applicants"],
        "verified_facts": [
            "Published schedules are tied to the 2026 H2 intake.",
            "KOSAF published post-selection guidance on October 15, 2026.",
        ],
        "outstanding": [
            "University-specific deadlines and subsequent amendments",
            "Final semantic approval of all 49 FAQ answers",
        ],
    },
}

assert set(decisions) == set(groups)
assert set(group_by_id) == set(ids)

for group_id, review in decisions.items():
    assert review["verified_facts"]
    assert review["outstanding"]
    assert all(key in official_sources for key in review["source_keys"])

consolidated = json.loads(OUTPUT.read_text(encoding="utf-8"))
assert consolidated["source_pdf_sha256"] == pdf_hash
assert {item["record_id"] for item in consolidated["issues"]} == set(ids)
assert consolidated["legal_validation_approved"] is False

consolidated["substantive_review"] = {
    "review_date": "2026-10-28",
    "method": "official_notice_and_agency_source_comparison",
    "official_sources": official_sources,
    "group_decisions": decisions,
    "verified_group_count": len(decisions),
    "legal_conclusions_finalized": False,
    "individual_eligibility_determined": False,
}

for item in consolidated["issue_groups"]:
    item["substantive_review"] = decisions[item["group_id"]]
    item["review_status"] = "needs_review"

for item in consolidated["issues"]:
    item["substantive_review_group"] = item["group_id"]
    item["resolved"] = False
    item["review_status"] = "needs_review"

consolidated["legal_validation_approved"] = False
consolidated["approved_for_user_answers"] = False
consolidated["approved_for_embedding"] = False
consolidated["approved_for_eligibility_decision"] = False
consolidated["automatic_eligibility_rules_enabled"] = False
consolidated["database_changed"] = False

OUTPUT.write_text(
    json.dumps(consolidated, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

verified = json.loads(OUTPUT.read_text(encoding="utf-8"))
assert len(verified["issues"]) == 25
assert len(verified["substantive_review"]["group_decisions"]) == 8
assert all(not issue["resolved"] for issue in verified["issues"])
assert not verified["legal_validation_approved"]
assert not verified["approved_for_eligibility_decision"]

print("=== SUBSTANTIVE REVIEW ===")
print("GROUPS_REVIEWED: 8/8")
print("ISSUES_PRESERVED: 25/25")
print("OFFICIAL_SOURCES:", len(official_sources))
print("FINAL_LEGAL_APPROVAL: False")
print("DATABASE_CHANGED: False")
print("RESULT: PASS")