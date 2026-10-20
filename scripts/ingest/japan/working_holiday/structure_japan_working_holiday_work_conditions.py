
import json
from pathlib import Path


# 공식 원문 추출 결과
INPUT_PATH = Path(
    "data/raw/japan/working_holiday/japan_working_holiday_work_conditions.json"
)

# Global-In 서비스용 구조화 데이터
OUTPUT_PATH = Path(
    "data/processed/japan/working_holiday/japan_working_holiday_work_conditions_structured.json"
)


def check_evidence(original_text: str, phrase: str) -> None:
    """구조화할 정책의 근거 문구가 원문에 존재하는지 검사한다."""
    if phrase.lower() not in original_text.lower():
        raise ValueError(f"공식 근거 누락 또는 변경: {phrase}")


def main() -> None:
    with INPUT_PATH.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    # 기존 일본 워홀 데이터셋과 식별자 통일
    if raw.get("route_id") != "JP-WH":
        raise ValueError("경로 ID 불일치")

    if raw.get("program_id") != "JP-WH-01":
        raise ValueError("프로그램 ID 불일치")

    original_text = raw["original_text"]

    # 각각의 정책에 연결할 공식 원문 구절
    evidence_phrases = {
        "employment_purpose": (
            "employment as an incidental activity of their holidays"
        ),
        "prohibited_workplaces": (
            "bars, cabarets, nightclubs, gambling establishments"
        ),
        "violation_consequences": (
            "will face deportation"
        ),
        "deportation_exception": (
            "victim of human trafficking"
        ),
        "employer_liability": (
            "could face criminal charges"
        ),
    }

    for phrase in evidence_phrases.values():
        check_evidence(original_text, phrase)

    result = {
        "route_id": raw["route_id"],
        "program_id": raw["program_id"],
        "target_nationality": raw["target_nationality"],
        "data_type": "work_conditions",
        "source": raw["source"],

        "work_conditions": {
            "employment_purpose": {
                "type": "incidental_activity",
                "purpose": "supplement_travel_funds",
                "employment_is_primary_purpose": False,
                "evidence_text": evidence_phrases["employment_purpose"],
                "validation_status": "needs_review",
            },

            "prohibited_workplaces": {
                "categories": [
                    "bars",
                    "cabarets",
                    "nightclubs",
                    "gambling_establishments",
                    "other_premises_affecting_public_morals",
                ],
                "prohibited": True,
                "evidence_text": evidence_phrases["prohibited_workplaces"],
                "validation_status": "needs_review",
            },

            "violation_consequences": {
                "immigration_law_violation": True,
                "deportation_risk": True,
                "evidence_text": evidence_phrases["violation_consequences"],
                "validation_status": "needs_review",
            },

            "deportation_exception": {
                "exception_type": "recognized_human_trafficking_victim",
                "exception_scope": "deportation_consequence",
                "grants_permission_to_work_in_prohibited_places": False,
                "evidence_text": evidence_phrases["deportation_exception"],
                "validation_status": "needs_review",
            },

            "employer_liability": {
                "possible_criminal_charges": True,
                "related_activities": [
                    "promoting_illegal_work",
                    "human_trafficking",
                ],
                "evidence_text": evidence_phrases["employer_liability"],
                "validation_status": "needs_review",
            },

            # 원문에는 특정 근로시간 상한이 제시되어 있지 않음
            "weekly_work_hour_limit": None,
            "weekly_work_hour_limit_status": "not_specified_in_source",
        },

        # 해석과 별도로 공식 원문 전체 보존
        "original_text": original_text,
        "validation_status": "needs_review",
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 54-3 취업 제한 구조화 =====")
    print("파일:", OUTPUT_PATH)
    print("정책 항목:", len(evidence_phrases))
    print("원문 길이:", len(original_text))
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()
