# Row 데이터와 Processed 데이터 분리


import json
from pathlib import Path


# 기존 신청수속 JSON
INPUT_PATH = Path(
    "data/raw/japan_working_holiday_application.json"
)

# Global-In 서비스용 구조화 JSON
OUTPUT_PATH = Path(
    "data/processed/japan_working_holiday_application_structured.json"
)


def main() -> None:
    # 원본 JSON 읽기
    with INPUT_PATH.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    # 필수 구조 및 기존 데이터 확인
    if raw.get("program_id") != "JP-WH-01":
        raise ValueError("프로그램 ID 불일치")

    required_fields = [
        "structured_dates",
        "structured_method",
        "structured_location",
        "structured_notification",
        "structured_document_guidance",
    ]

    missing = [
        field for field in required_fields
        if field not in raw
    ]

    if missing:
        raise ValueError(f"구조화 데이터 누락: {missing}")

    if len(raw.get("sections", [])) != 5:
        raise ValueError("공식 원문 섹션 수 불일치")

    # 서비스에서 사용할 구조화 데이터 구성
    result = {
        "route_id": raw["route_id"],
        "program_id": raw["program_id"],
        "target_nationality": raw["target_nationality"],
        "data_type": "application",
        "source": raw["source"],

        # 신청기간 및 결과 발표일
        "application_dates": raw["structured_dates"],

        # 접수 방법
        "application_method": raw["structured_method"],

        # 관할 공관
        "application_location": raw["structured_location"],

        # 심사결과 알림
        "result_notification": raw["structured_notification"],

        # 제출서류 공통 주의사항
        "document_guidance": raw["structured_document_guidance"],

        # 공식 원문 연결
        "source_sections": raw["sections"],

        "validation_status": "needs_review",
    }

    # 결과 저장
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 53-1 구조화 저장 결과 =====")
    print("파일:", OUTPUT_PATH)
    print("프로그램:", result["program_id"])
    print("공식 원문 섹션:", len(result["source_sections"]))
    print("구조화 데이터: 5개")
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()
