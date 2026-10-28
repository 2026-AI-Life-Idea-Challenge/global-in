
import json
from pathlib import Path


# STEP 56-4에서 저장한 공식 원문
INPUT_PATH = Path(
    "data/raw/japan/working_holiday/japan_working_holiday_useful_information.json"
)

# Global-In 서비스에서 사용할 구조화 데이터
OUTPUT_PATH = Path(
    "data/processed/japan/working_holiday/japan_working_holiday_useful_information_structured.json"
)


def extract_evidence(text: str, start: str, end: str) -> str:
    """공식 원문에서 시작·종료 문구 사이의 근거를 추출한다."""
    start_index = text.find(start)

    if start_index == -1:
        raise ValueError(f"시작 문구 누락: {start}")

    end_index = text.find(end, start_index)

    if end_index == -1:
        raise ValueError(f"종료 문구 누락: {end}")

    return text[start_index:end_index + len(end)]


def main() -> None:
    with INPUT_PATH.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    # 다른 일본 워킹홀리데이 데이터와 동일한 식별자 사용
    if raw["route_id"] != "JP-WH":
        raise ValueError("경로 ID 불일치")

    if raw["program_id"] != "JP-WH-01":
        raise ValueError("프로그램 ID 불일치")

    if raw["target_nationality"] != "KR":
        raise ValueError("대상 국적 불일치")

    original_text = raw["original_text"]

    # 정보별 원문 문장 보존
    fraud_evidence = extract_evidence(
        original_text,
        "Please beware of fraudulent entities",
        "operating the working holiday programmes.",
    )

    employment_evidence = extract_evidence(
        original_text,
        "Foreign job-seekers in Japan",
        "Information for foreigners who are seeking jobs in Japan ).",
    )

    survey_evidence = extract_evidence(
        original_text,
        "We may request working holiday programmes participants",
        "We would appreciate your cooperation in this regard.",
    )

    result = {
        "route_id": raw["route_id"],
        "program_id": raw["program_id"],
        "target_nationality": raw["target_nationality"],
        "data_type": "useful_information",
        "source": raw["source"],

        "useful_information": {
            "visa_fraud_warning": {
                "category": "safety_notice",
                "warning_type": "fraudulent_visa_assistance",
                "summary_ko": (
                    "일본 외무성은 워킹홀리데이 프로그램 운영과 "
                    "관련하여 일본 내 특정 단체와 협력하지 않으므로, "
                    "외무성 협력 기관을 사칭하는 비자 지원 단체에 주의"
                ),
                "evidence_text": fraud_evidence,
                "validation_status": "needs_review",
            },

            "employment_support": {
                "category": "support_service",
                "service_types": [
                    "employment_service_centre_for_foreigners",
                    "hello_work",
                ],
                "listed_cities": [
                    "Tokyo",
                    "Nagoya",
                    "Osaka",
                    "Fukuoka",
                ],
                "hello_work_scope": "some_regional_offices",
                "languages": "english_or_other_languages",
                "responsible_reference_agency": (
                    "Ministry of Health, Labour and Welfare"
                ),
                "eligibility_requirements": None,
                "operating_hours": None,
                "evidence_text": employment_evidence,
                "validation_status": "needs_review",
            },

            "post_programme_questionnaire": {
                "category": "optional_information",
                "may_be_requested": True,
                "request_timing": "after_programme_completion",
                "mandatory_participation": None,
                "evidence_text": survey_evidence,
                "validation_status": "needs_review",
            },
        },

        # 원문 전체를 함께 보관해 근거 추적 가능
        "original_text": original_text,
        "validation_status": "needs_review",
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 56-5 기타 정보 구조화 =====")
    print("파일:", OUTPUT_PATH)
    print("정보 항목:", len(result["useful_information"]))
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()
