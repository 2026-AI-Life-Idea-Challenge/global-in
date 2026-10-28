
import json
from pathlib import Path


# 공식 원문 추출 결과
INPUT_PATH = Path(
    "data/raw/japan/working_holiday/japan_working_holiday_post_entry.json"
)

# Global-In 서비스용 구조화 결과
OUTPUT_PATH = Path(
    "data/processed/japan/working_holiday/japan_working_holiday_post_entry_structured.json"
)


def verify_phrase(original_text: str, phrase: str) -> None:
    """구조화 정책의 근거 문구가 공식 원문에 있는지 확인한다."""
    if phrase.lower() not in original_text.lower():
        raise ValueError(f"공식 근거 문구 누락: {phrase}")


def main() -> None:
    with INPUT_PATH.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    # 기존 일본 워킹홀리데이 데이터셋과 식별자 통일
    assert raw["route_id"] == "JP-WH"
    assert raw["program_id"] == "JP-WH-01"
    assert raw["target_nationality"] == "KR"
    assert raw["data_type"] == "post_entry"

    original_text = raw["original_text"]

    # 모든 구조화 항목은 공식 원문 구절과 연결
    evidence = {
        "reporting_office": "municipal office where they live",
        "legal_notification_recipient": "notify the Ministry of Justice",
        "deadline": "within 14 days of finding a place to settle down",
        "detail_reference": "Immigration Services Agency of Japan",
    }

    for phrase in evidence.values():
        verify_phrase(original_text, phrase)

    result = {
        "route_id": raw["route_id"],
        "program_id": raw["program_id"],
        "target_nationality": raw["target_nationality"],
        "data_type": "post_entry",
        "source": raw["source"],

        "post_entry": {
            "procedure_type": "residence_address_notification",

            # 실제 방문할 장소
            "reporting_office": "municipal_office",
            "reporting_office_evidence": evidence["reporting_office"],

            # 법률상 신고 대상 기관
            "legal_notification_recipient": "ministry_of_justice",
            "legal_notification_recipient_evidence": evidence[
                "legal_notification_recipient"
            ],

            # 14일은 입국일부터가 아니라 거주지를 정한 시점부터
            "deadline_days": 14,
            "deadline_trigger": "finding_a_place_to_settle_down",
            "deadline_evidence": evidence["deadline"],

            # 이 원문에서는 별도 방문 필요 여부를 직접 명시하지 않음
            "separate_immigration_office_visit_required": None,
            "separate_visit_verification_status": "needs_external_source",

            # 자세한 절차는 출입국재류관리청 자료 확인 필요
            "detail_reference": "immigration_services_agency_of_japan",
            "detail_reference_evidence": evidence["detail_reference"],

            # 제출서류 등 아직 수집하지 않은 정보는 추정하지 않음
            "required_documents": None,
            "validation_status": "needs_review",
        },

        "original_text": original_text,
        "validation_status": "needs_review",
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 55-3 입국 후 행정 절차 구조화 =====")
    print("파일:", OUTPUT_PATH)
    print("신고 장소:", result["post_entry"]["reporting_office"])
    print("신고 기한:", result["post_entry"]["deadline_days"], "일")
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()
