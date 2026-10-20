
import json
from pathlib import Path


# 기존 구조화 데이터에 출입국재류관리청 근거 추가
DATA_PATH = Path(
    "data/processed/japan/working_holiday/japan_working_holiday_post_entry_structured.json"
)

# 일본 출입국재류관리청의 공식 신고 안내
OFFICIAL_URL = (
    "https://www.moj.go.jp/isa/applications/procedures/"
    "nyuukokukanri10_00021.html"
)

GUIDANCE_URL = (
    "https://www.moj.go.jp/isa/support/guidance/index.html?hl=en"
)


def main() -> None:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data["program_id"] != "JP-WH-01":
        raise ValueError("프로그램 ID 불일치")

    post = data["post_entry"]

    if post["deadline_days"] != 14:
        raise ValueError("기존 신고 기한 확인 필요")

    if post["reporting_office"] != "municipal_office":
        raise ValueError("기존 신고 장소 확인 필요")

    # 지방자치단체에서 적법한 전입신고를 완료한 경우에 한정
    post["separate_immigration_office_visit_required"] = False
    post["separate_visit_condition"] = (
        "qualifying_municipal_residence_notification_completed"
    )
    post["separate_visit_verification_status"] = (
        "supported_by_official_isa_source"
    )

    # 재류카드 발급 여부에 따른 지참 서류 구분
    post["required_documents"] = {
        "standard": ["residence_card"],
        "alternative": {
            "document": "passport",
            "condition": "residence_card_to_be_issued_later_notation",
        },
        "additional_local_requirements": "confirm_with_municipality",
    }

    # 외무성 원문과 별개로 추가 확인한 공식 출처 관리
    post["additional_official_sources"] = [
        {
            "official_agency": (
                "Immigration Services Agency of Japan"
            ),
            "source_url": OFFICIAL_URL,
            "supports": [
                "deadline_days",
                "reporting_office",
                "separate_immigration_office_visit_required",
                "required_documents",
            ],
            "verified_at": None,
            "needs_verification": True,
        },
        {
            "official_agency": (
                "Immigration Services Agency of Japan"
            ),
            "source_url": GUIDANCE_URL,
            "supports": [
                "deadline_days",
                "reporting_office",
                "required_documents",
            ],
            "verified_at": None,
            "needs_verification": True,
        },
    ]

    # 자동화된 원문 대조까지 끝난 상태는 아니므로 검토 유지
    post["validation_status"] = "needs_review"
    data["validation_status"] = "needs_review"

    with DATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print("===== STEP 55-4 공식 근거 보강 =====")
    print("프로그램:", data["program_id"])
    print(
        "별도 방문 필요:",
        post["separate_immigration_office_visit_required"],
    )
    print("추가 공식 출처:", len(post["additional_official_sources"]))
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()
