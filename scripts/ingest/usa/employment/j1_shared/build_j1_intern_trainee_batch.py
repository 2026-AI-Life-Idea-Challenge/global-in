
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("data/processed/usa/employment")
OUTPUT = BASE / "j1_intern_trainee_batch_review_2026_draft.json"

SPECS = {
    "j1_intern": [
        (
            "Interns must be foreign nationals:",
            "applicant_eligibility",
            "해외의 학위 또는 수료증을 수여하는 고등교육기관에서 "
            "현재 학업 중이거나, 교환방문 프로그램 시작 전 "
            "12개월 이내 해당 기관을 졸업한 외국인이 대상이다."
        ),
        (
            "Limitations/Exceptions for Intern work environment",
            "work_restrictions",
            "비숙련·임시 노동, 보육·노인 돌봄, 의료 환자 "
            "진료 또는 접촉을 수반하는 직무가 제한된다. "
            "사무·행정 지원 업무 비중이 20%를 초과하는 "
            "직무도 허용되지 않는다."
        ),
        (
            "Internships are offered in the following occupational categories:",
            "allowed_occupations",
            "농업, 예술, 건설, 교육, 보건 관련 직종, "
            "관광, 정보통신, 경영·금융, 공공행정, "
            "과학·공학 등 공식적으로 열거된 직종 분야에서 "
            "인턴십을 운영할 수 있다."
        ),
        (
            "Sponsors are required to:",
            "sponsor_site_visit",
            "스폰서는 규정에서 정한 호스트 기관에 대해 "
            "현장 실사를 수행하고, 모든 호스트 기관의 "
            "EIN, 연락처·주소 등 확인 자료 및 "
            "산재보험 관련 증빙을 수집해야 한다. "
            "현장 실사 적용 조건의 결합 관계는 "
            "추가 법률 검토가 필요하다."
        ),
        (
            "Sponsors must ensure the following:",
            "participant_evaluation",
            "프로그램 기간이 6개월을 초과하면 중간 및 "
            "최종 평가가 필요하고, 6개월 미만이면 "
            "최종 평가가 필요하다. 평가서에는 참가자와 "
            "직속 감독자의 서명이 요구된다."
        ),
        (
            "Hosts are required to:",
            "host_obligations",
            "호스트는 DS-7002 훈련·인턴십 계획에 "
            "서명하고, 스폰서에 대한 변경·문제 보고, "
            "안전 규정 준수, 현장 감독·멘토링 및 "
            "구조화된 학습 활동 제공 의무를 부담한다."
        ),
    ],
    "j1_trainee": [
        (
            "A trainee must be a foreign national who:",
            "applicant_eligibility",
            "해외 고등교육기관의 학위 또는 전문자격과 "
            "관련 분야의 미국 외 경력 1년 이상을 "
            "보유하거나, 훈련 대상 분야에서 "
            "미국 외 경력 5년 이상을 보유해야 한다."
        ),
        (
            "Limitations or Exceptions",
            "work_restrictions",
            "비숙련·임시 노동, 돌봄, 환자 진료·접촉 "
            "업무 및 사무보조 20% 초과 직무가 제한된다. "
            "일반 고용이나 기존 직원의 업무를 대체해서는 "
            "안 되며, 이전 경력·훈련을 그대로 반복하는 "
            "훈련도 허용되지 않는다."
        ),
        (
            "Allowed Occupational Categories",
            "allowed_occupations",
            "농업, 예술, 건설, 교육, 보건 관련 직종, "
            "관광, 정보통신, 경영·금융, 공공행정, "
            "과학·공학 등 공식적으로 열거된 분야에서 "
            "훈련 프로그램을 운영할 수 있다."
        ),
        (
            "Sponsors are required to:",
            "sponsor_site_visit",
            "스폰서는 규정에서 정한 호스트 기관에 대해 "
            "현장 실사를 수행하고, 모든 호스트 기관의 "
            "EIN, 연락처·주소 등 확인 자료와 "
            "산재보험 또는 동등한 보험 증빙을 "
            "수집해야 한다. 현장 실사 적용 조건은 "
            "추가 검토가 필요하다."
        ),
        (
            "Sponsors must ensure the following for participants:",
            "participant_evaluation",
            "6개월 초과 프로그램에는 중간·최종 평가, "
            "6개월 미만 프로그램에는 최종 평가가 필요하다. "
            "스폰서는 참가자의 선발·오리엔테이션·감독을 "
            "관리하고 주 32시간 이상의 전일제 "
            "훈련을 보장해야 한다."
        ),
        (
            "Host Organizations are required to:",
            "host_obligations",
            "호스트 기관은 DS-7002 서명, 스폰서에 대한 "
            "변경·문제 보고, 안전 규정 준수, "
            "지속적인 현장 감독·멘토링 및 "
            "구조화된 훈련 제공 의무를 부담한다."
        ),
    ],
}

PENDING = [
    "Official source section boundaries and navigation text",
    "Current regulatory applicability",
    "Program duration and category-specific exceptions",
    "Sponsor designation and DS-2019 issuance",
    "DS-7002 filing and training plan requirements",
    "SEVIS, visa fees, and insurance requirements",
    "J-2 dependents and INA 212(e), where applicable",
    "Complete semantic and legal review",
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"출력 파일이 이미 존재합니다: {OUTPUT}"
        )

    programs = {}
    counts = {}

    for folder, specs in SPECS.items():
        path = BASE / folder / "official_evidence.json"
        source = read_json(path)
        sections = source["sections"]

        if len(sections) != 13:
            raise ValueError(
                f"{folder}: 예상과 다른 섹션 수"
            )

        if len(specs) != 6:
            raise ValueError(
                f"{folder}: 정책 정의 수 불일치"
            )

        headings = {}

        for section in sections:
            heading = section["heading"].strip()

            if heading in headings:
                raise ValueError(
                    f"{folder}: 중복 제목 {heading}"
                )

            text = section["source_text"]

            if sha256(text) != section[
                "source_text_sha256"
            ]:
                raise ValueError(
                    f"{folder}: Evidence 해시 오류"
                )

            if len(text) != section["source_text_length"]:
                raise ValueError(
                    f"{folder}: Evidence 길이 오류"
                )

            if (
                section["source_html_sha256"]
                != source["source_html_sha256"]
            ):
                raise ValueError(
                    f"{folder}: 원본 HTML 해시 연결 오류"
                )

            headings[heading] = section

        records = []
        evidence_records = []

        for number, (heading, topic, summary) in enumerate(
            specs, 1
        ):
            if heading not in headings:
                raise ValueError(
                    f"{folder}: 섹션 누락 {heading}"
                )

            section = headings[heading]
            policy_id = (
                f"{source['program_id']}-POL-"
                f"{number:03d}"
            )

            records.append({
                "policy_id": policy_id,
                "topic": topic,
                "summary_ko": summary,
                "evidence_id": section["evidence_id"],
                "source_heading": heading,
                "review_status": "needs_review",
                "semantic_support_verified": False,
                "legal_effect_verified": False,
                "approved_for_user_answers": False,
                "approved_for_embedding": False,
            })

            evidence_records.append({
                "policy_id": policy_id,
                "evidence_id": section["evidence_id"],
                "heading": heading,
                "source_url": section["source_url"],
                "source_html_sha256": section[
                    "source_html_sha256"
                ],
                "source_text": section["source_text"],
                "source_text_sha256": section[
                    "source_text_sha256"
                ],
                "section_boundaries_verified": False,
            })

        programs[folder] = {
            "program_id": source["program_id"],
            "official_program_name": source[
                "official_program_name"
            ],
            "total_source_sections": len(sections),
            "selected_policy_count": len(records),
            "policy_records": records,
            "evidence_records": evidence_records,
            "section_boundaries_verified": False,
            "eligibility_rules_verified": False,
            "review_status": "needs_review",
            "approved_for_user_answers": False,
            "approved_for_embedding": False,
            "automatic_eligibility_rules_enabled": False,
            "embedding_generated": False,
        }

        counts[folder] = len(records)

    all_ids = [
        record["policy_id"]
        for program in programs.values()
        for record in program["policy_records"]
    ]

    if len(all_ids) != len(set(all_ids)):
        raise ValueError("프로그램 간 정책 ID 중복")

    report = {
        "dataset_type": "j1_intern_trainee_policy_batch_draft",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "programs": programs,
        "comparison": {
            "shared_topics": [
                "work_restrictions",
                "allowed_occupations",
                "sponsor_site_visit",
                "participant_evaluation",
                "host_obligations",
            ],
            "distinct_applicant_eligibility": True,
            "trainee_minimum_training_hours": 32,
            "intern_minimum_training_hours_verified": False,
        },
        "pending_review_items": PENDING,
        "source_section_hashes_verified": True,
        "section_boundaries_verified": False,
        "semantic_support_verified": False,
        "legal_effect_verified": False,
        "completeness_verified": False,
        "automatic_exclusion_performed": False,
        "review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    saved = read_json(OUTPUT)

    if saved["programs"] != programs:
        raise ValueError("저장 후 검증 실패")

    print("=== J-1 INTERN / TRAINEE BATCH ===")
    print("PROGRAMS:", len(programs))
    print("INTERN POLICIES:", counts["j1_intern"])
    print("TRAINEE POLICIES:", counts["j1_trainee"])
    print("TOTAL POLICY DRAFTS:", len(all_ids))
    print("SOURCE SECTIONS:", 26)
    print("SOURCE TEXT SHA-256: PASS")
    print("SOURCE HTML HASH LINKS: PASS")
    print("POLICY ID UNIQUENESS: PASS")
    print("SECTION BOUNDARIES VERIFIED: False")
    print("LEGAL EFFECT VERIFIED: False")
    print("COMPLETENESS VERIFIED: False")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()