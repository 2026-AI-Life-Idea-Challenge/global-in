"""일본 워킹홀리데이 제출서류 구조화 (보완 STEP 23 리팩터링).

- 원본 HTML에서 별도 추출한 raw JSON을 입력으로 사용한다.
- 제출서류 14개와 기존 9개 조건부/선택 규칙, 공식 근거 문구를 보존한다.
- 결과 생성 후 JSON을 한 번만 저장하며, 저장된 파일을 검증한다.
- 정책 해석의 승인 여부를 뜻하지 않으므로 needs_review 상태를 유지한다.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "japan" / "working_holiday" / "japan_working_holiday_documents.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "japan" / "working_holiday" / "japan_working_holiday_documents_structured.json"
EXPECTED_RULE_IDS = {
    "JP_WH_DOC_004_C01", "JP_WH_DOC_008_C01", "JP_WH_DOC_008_C02",
    "JP_WH_DOC_008_C03", "JP_WH_DOC_010_C01", "JP_WH_DOC_010_C02",
    "JP_WH_DOC_011_C01", "JP_WH_DOC_013_C01", "JP_WH_DOC_014_C01",
}


def normalize_text(text: str) -> str:
    """원문 존재 여부 검사에 한해서 공백 차이를 무시한다."""
    return "".join(text.split())


def load_raw_data() -> dict:
    """원본 데이터는 수정하지 않고 읽기만 한다."""
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_document(documents_by_id: dict, document_id: str) -> dict:
    """고유 ID로 서류를 조회하고, 존재하지 않으면 즉시 중단한다."""
    return documents_by_id[document_id]

def build_documents(raw_data: dict) -> list[dict]:
        """원문 순서를 유지하며 필수 12개와 조건부 2개에 ID를 부여한다."""
        documents = []
        for requirement_type, key in (
            ("required", "required_documents"),
            ("conditional", "conditional_documents"),
        ):
            for original_text in raw_data[key]:
                documents.append({
                    "document_id": f"JP_WH_DOC_{len(documents) + 1:03d}",
                    "requirement_type": requirement_type,
                    "name": None,
                    "original_text": original_text,
                    "validation_status": "needs_review",
                })
        return documents

def attach_requirements(documents: list[dict], by_id: dict) -> None:
        """작성 언어·대체자료·본인 작성/서명·사진/여권/출입국 범위를 부여한다."""
        document_names = {
            "JP_WH_DOC_001": "사증신청서",
            "JP_WH_DOC_002": "이력서",
            "JP_WH_DOC_003": "워킹홀리데이 지원 이유 진술서",
            "JP_WH_DOC_004": "일본 체류 활동계획 진술서",
            "JP_WH_DOC_005": "조사표",
            "JP_WH_DOC_006": "기본증명서(상세)",
            "JP_WH_DOC_007": "주민등록초본 또는 대체 신분·주소 증빙",
            "JP_WH_DOC_008": "재학증명서 또는 최종학력증명서",
            "JP_WH_DOC_009": "은행 잔고증명서",
            "JP_WH_DOC_010": "여권 사본",
            "JP_WH_DOC_011": "출입국사실증명서",
            "JP_WH_DOC_012": "제출자료 체크리스트",
            "JP_WH_DOC_013": "병역 관련 증명서",
            "JP_WH_DOC_014": "일본어 능력 입증자료"
        }

        language_requirements = {
            "JP_WH_DOC_002": ["ja", "en"],
            "JP_WH_DOC_003": ["ja", "en"],
            "JP_WH_DOC_004": ["ja", "en"],
            "JP_WH_DOC_005": ["ja"]
        }

        alternative_documents = {

            # 주민등록초본 대신 제출할 수 있는 자료
            "JP_WH_DOC_007": {
                "alternatives": [
                    "주민등록증 앞·뒷면 사본",
                    "주민등록등본"
                ],
                "condition": None,
                "note": "대사관 원문에서 대체 제출 가능하다고 안내함"
            },

            # 학적 상태에 따라 제출할 자료가 달라짐
            "JP_WH_DOC_008": {
                "alternatives": [
                    "최종학력증명서"
                ],
                "condition": "신청인의 학적 상태에 따라 적합한 증빙 제출",
                "note": "휴학·퇴학·해외 학력 등에 대한 추가 자료 조건은 별도 검토 필요"
            },

            # 가족의 부양을 받는 경우 사용할 수 있는 증빙
            "JP_WH_DOC_009": {
                "alternatives": [
                    "부양하는 가족 명의의 은행 잔고증명서"
                ],
                "condition": "가족의 부양을 받는 학생 등",
                "additional_documents": [
                    "가족관계증명서"
                ],
                "note": "가족 명의 잔고증명서 제출 시 부양자와의 관계 증빙 필요"
            }
        }

        applicant_written_ids = {
            "JP_WH_DOC_001",
            "JP_WH_DOC_002",
            "JP_WH_DOC_003",
            "JP_WH_DOC_004",
            "JP_WH_DOC_005",
            "JP_WH_DOC_012"
        }

        applicant_signature_ids = {
            "JP_WH_DOC_005"
        }

        # 확인되지 않은 작성자·서명 정보는 False가 아니라 None으로 보관한다.
        for doc in documents:
            doc_id = doc["document_id"]
            doc["name"] = document_names[doc_id]
            doc["allowed_languages"] = language_requirements.get(doc_id)
            doc["alternative_submission"] = alternative_documents.get(doc_id)
            doc["applicant_must_complete"] = True if doc_id in applicant_written_ids else None
            doc["applicant_signature_required"] = True if doc_id in applicant_signature_ids else None

        photo_requirements = {
            "required": True,

            # 사진의 대략적인 크기 (cm)
            "width_cm": 3.5,
            "height_cm": 4.5,
            "size_is_approximate": True,

            # 배경 요건
            "background": "plain",

            # 촬영 시점: 최근 6개월 이내
            "taken_within_months": 6,

            # 공식 근거
            "evidence_text": (
                "사진부착: 대강 가로3.5cm X 세로4.5cm. "
                "무배경 6개월 이내에 촬영한 것."
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_001")["photo_requirements"] = photo_requirements

        passport_copy_requirements = {
            "required": True,

            # 모든 신청자가 기본적으로 제출할 페이지
            "required_pages": [
                "여권 신분사항 페이지",
                "과거 일본 출입국 도장이 있는 모든 페이지"
            ],

            # 일본 출입국 도장이 있는 경우 관련 페이지 전체 제출
            "include_all_japan_entry_exit_stamps": True,

            # 공식 원문
            "evidence_text": (
                "여권복사(신분사항 란 및 지금까지 "
                "일본으로의 출입국도장이 있는 페이지 전부)"
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_010")["passport_copy_requirements"] = passport_copy_requirements

        travel_history_requirements = {
            "required": True,

            # 증명서에 포함되어야 하는 기간
            "period_start": "birth",
            "period_end": "application_date",

            # 공식 원문에는 '현재까지'라고 명시됨
            # 신청 시점에 발급한다는 전제로 내부 필드를 정의
            "note": "출생 후 현재까지의 출입국 기록 제출",

            "evidence_text": (
                "출생 후 현재까지의 기간의 "
                "출입국사실증명서를 제출해 주십시오."
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_011")["travel_history_requirements"] = travel_history_requirements

def attach_conditional_rules(by_id: dict) -> None:
        """기존 STEP 4~11 및 STEP 18의 9개 조건부·선택 규칙을 연결한다."""
        english_evidence_rule = {
            "rule_id": "JP_WH_DOC_004_C01",

            # 필수가 아닌 선택 제출자료
            "requirement_type": "optional",

            # 활동계획 진술서를 영어로 작성하는 경우
            "field": "activity_plan_language",
            "operator": "eq",
            "value": "en",

            # 제출 가능한 선택적 증빙자료
            "optional_supporting_documents": [
                "TOEFL 성적표",
                "TOEIC 성적표",
                "영어권 대학 등의 졸업증명서"
            ],

            # 증빙자료가 없어도 신청 가능
            "can_apply_without_documents": True,

            # 대사관 원문의 핵심 내용 보존
            "evidence_text": (
                "영어로 작성한 자는 영어능력입증자료"
                "(TOEFL,TOEIC,영어권의 대학 등의 졸업증명서 등)가 "
                "있는 경우는 제출해 주십시오. "
                "또한 이들 입증자료가 없어도 신청은 가능합니다."
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_004").setdefault("conditional_rules", []).extend([english_evidence_rule])

        academic_status_rules = [
            {
                "rule_id": "JP_WH_DOC_008_C01",

                # 조건 유형: 특정 상황에서 추가서류 필요
                "requirement_type": "conditional",

                # 사용자 정보에서 확인할 항목
                "field": "academic_status",

                # 다음 상태 중 하나에 해당하면 조건 적용
                "operator": "in",
                "values": ["on_leave", "withdrawn"],

                # 상태별 제출서류
                "required_documents_by_status": {
                    "on_leave": ["휴학증명서"],
                    "withdrawn": ["제적증명서"]
                },

                # 일본대사관 원문 보존
                "evidence_text": (
                    "대학교나 대학원을 휴학하거나 퇴학한 경우 "
                    "그것을 증명할 수 있는 서류를 제출해 주십시오."
                    "(휴학증명서, 제적증명서 등)"
                ),

                # 공식 원문의 조건을 구조화했으나 최종 정책 검토는 남음
                "validation_status": "needs_review"
            }
        ]

        get_document(by_id, "JP_WH_DOC_008").setdefault("conditional_rules", []).extend(academic_status_rules)

        japan_study_history_rule = {
            "rule_id": "JP_WH_DOC_008_C02",

            # 일본 유학 경험이 있는 경우에만 적용
            "requirement_type": "conditional",

            # 사용자에게 확인할 정보
            "field": "has_studied_in_japan",

            # 값이 True이면 조건 충족
            "operator": "eq",
            "value": True,

            # 제출해야 할 증빙 자료
            "required_documents": [
                "일본에서 재적한 학교의 졸업·수료 등 증명자료"
            ],

            # 적용 범위에 교환학생·단기유학 포함
            "note": "교환유학 및 단기유학 경험도 포함",

            # 일본대사관 공식 원문
            "evidence_text": (
                "일본에 유학한 적이 있는 자"
                "(교환유학, 단기유학 등을 포함)는 "
                "재적한 학교의 졸업, 수료 등을 "
                "증명할 수 있는 자료를 제출해 주십시오."
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_008").setdefault("conditional_rules", []).extend([japan_study_history_rule])

        foreign_academic_translation_rule = {
            "rule_id": "JP_WH_DOC_008_C03",

            "requirement_type": "conditional",

            # 두 조건을 모두 충족해야 규칙 적용
            "operator": "and",

            "conditions": [
                {
                    # 한국·일본 외 국가의 대학/대학원 졸업·수료 여부
                    "field": "has_completed_higher_education_outside_kr_jp",
                    "operator": "eq",
                    "value": True
                },
                {
                    # 증명서 작성 언어
                    "field": "academic_document_language",
                    "operator": "not_in",
                    "values": ["ko", "ja", "en"]
                }
            ],

            "required_documents": [
                "학력증명서의 공증된 번역문"
            ],

            "evidence_text": (
                "한국 및 일본 이외 국가 등의 대학교이나 대학원을 "
                "졸업 및 수료한 경우로 일본어, 한국어 및 영어 이외의 "
                "언어로 쓰여진 증명서인 경우, 번역을 첨부해 주십시오."
                "(공증된 것)"
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_008").setdefault("conditional_rules", []).extend([foreign_academic_translation_rule])

        long_stay_history_rule = {
            "rule_id": "JP_WH_DOC_010_C01",

            "requirement_type": "conditional",

            # 사용자의 출입국 이력에서 확인할 조건
            "field": "has_90day_travel_record_after_18",

            "operator": "eq",
            "value": True,

            # 해당 조건을 충족하는 경우 추가로 제출할 자료
            "required_documents": [
                "해당 해외 출입국 이력과 관련된 사증 및 출입국 도장 페이지 사본"
            ],

            # 방문 국가에 관계없이 적용
            "note": (
                "만 18세 이후 90일 이상에 해당하는 출입국 이력. "
                "방문 국가와 관계없이 관련 페이지를 제출."
            ),

            # 공식 원문을 보존
            "evidence_text": (
                "아래 11의 자료에 있어서 만 18세 이후 "
                "90일이상의 출입국사실이 있는 경우는, "
                "도항처를 불문하고, 해당하는 사증 및 "
                "출입국도장이 있는 페이지의 복사를 제출해 주십시오."
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_010").setdefault("conditional_rules", []).extend([long_stay_history_rule])

        previous_wh_visa_rule = {
            "rule_id": "JP_WH_DOC_010_C02",

            "requirement_type": "conditional",

            # 과거 일본 워킹홀리데이 사증 발급 횟수
            "field": "previous_japan_wh_visa_issuances",

            # 발급 횟수가 1회 이상인 경우
            "operator": "gte",
            "value": 1,

            # 추가 제출자료
            "required_documents": [
                "과거 발급받은 일본 워킹홀리데이 사증이 부착된 여권 페이지 사본"
            ],

            # 실제 입국 여부와 발급 이력을 구분
            "note": (
                "실제 일본 입국 여부가 아닌 사증 발급 이력 기준. "
                "사용하지 않고 실효된 사증도 발급 이력에 포함될 수 있음."
            ),

            # 대사관 공식 원문
            "evidence_text": (
                "과거에 워킹홀리데이 사증을 발급받은 경우에는 "
                "해당 사증이 부착된 페이지의 복사를 제출해 주십시오"
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_010").setdefault("conditional_rules", []).extend([previous_wh_visa_rule])

        name_change_rule = {
            "rule_id": "JP_WH_DOC_011_C01",

            "requirement_type": "conditional",

            # 신청자의 개명 이력 여부
            "field": "has_name_change_history",
            "operator": "eq",
            "value": True,

            # 추가로 확인해야 하는 제출 범위
            "required_documents": [
                "개명 전후의 모든 출입국 기록"
            ],

            "evidence_text": (
                "또, 개명 등을 했을 경우, "
                "개명 전후의 모든 기록을 제출해 주십시오."
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_011").setdefault("conditional_rules", []).extend([name_change_rule])

        military_service_rule = {
            "rule_id": "JP_WH_DOC_013_C01",

            "requirement_type": "conditional",

            # 병역에 종사한 이력이 있는지 확인
            "field": "has_military_service_history",

            "operator": "eq",
            "value": True,

            # 해당하는 경우 제출할 자료
            "required_documents": [
                "병역에 종사한 사실을 증명할 수 있는 서류"
            ],

            # 주민등록초본으로 증빙할 수 있는 경우
            "alternative_documents": [
                "병역사항이 기재된 주민등록초본"
            ],

            # 별도의 병역증명서가 반드시 필요한 것은 아님
            "note": (
                "일본대사관 안내에 따라 주민등록초본과 "
                "겸용 가능. 해당 초본에 필요한 병역사항이 "
                "기재되어 있는지 확인해야 함."
            ),

            # 공식 원문
            "evidence_text": (
                "병역에 종사한 것을 증명할 수 있는 서류 "
                "(7의 주민등록초본과 겸용가능)"
            ),

            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_013").setdefault("conditional_rules", []).extend([military_service_rule])

        japanese_evidence_rule = {
            "rule_id": "JP_WH_DOC_014_C01",

            # 증빙자료의 보유 여부를 확인하기 위한 내부 필드
            "field": "has_japanese_proficiency_evidence",

            # 증빙자료가 없는 경우 대체 안내 적용
            "operator": "eq",
            "value": False,

            # 증빙이 없더라도 신청 불가로 처리하지 않음
            "requirement_type": "conditional",
            "can_apply_without_documents": True,

            # 증빙자료가 없을 때 안내할 내용
            "alternative_action": (
                "이력서 또는 지원 이유 진술서에 "
                "지금까지의 일본어 학습 이력을 설명"
            ),

            # 원문에 제시된 일본어 능력 관련 자료 예시
            "accepted_evidence_examples": [
                "JLPT 인정증",
                "일본어학교 수료증서",
                "학습 기간과 학습 내용이 기재된 일본어 학습자료"
            ],

            # 공식 원문 보존
            "evidence_text": (
                "자료가 없다면 이력서나 사유서 안에서 "
                "지금까지의 일본어 학습이력에 대해 "
                "설명해 주시기 바랍니다."
            ),

            # 정책 해석 최종 검토 전 상태
            "validation_status": "needs_review"
        }

        get_document(by_id, "JP_WH_DOC_014").setdefault("conditional_rules", []).extend([japanese_evidence_rule])

def build_result(raw_data: dict, documents: list[dict]) -> dict:
        """공식 출처 원본을 보존하며 수집·검증 상태를 추가한다."""
        source = raw_data["source"].copy()
        source.update({
            "collection_mode": "manual",
            "verified_at": None,
            "source_license": None,
            "needs_verification": True,
        })
        return {
            "route_id": "JP-WH",
            "program_id": "JP-WH-01",
            "target_nationality": raw_data["target_nationality"],
            "source": source,
            "documents": documents,
            "submission_notes": raw_data["submission_notes"],
            "validation_status": "needs_review",
        }

def validate_result(data: dict) -> int:
        """실제로 저장된 JSON의 구조, ID, 원문 문구 일치를 검사한다."""
        assert data["route_id"] == "JP-WH" and data["program_id"] == "JP-WH-01"
        assert data["target_nationality"] == "KR"
        docs = data["documents"]
        assert len(docs) == 14, "제출서류 수가 14개가 아닙니다."
        ids = [d["document_id"] for d in docs]
        assert len(ids) == len(set(ids)), "서류 ID가 중복되었습니다."
        assert sum(d["requirement_type"] == "required" for d in docs) == 12
        assert sum(d["requirement_type"] == "conditional" for d in docs) == 2
        assert all(d.get("name") for d in docs), "서류명 누락이 있습니다."
        assert sum(d.get("allowed_languages") is not None for d in docs) == 4
        assert sum(d.get("alternative_submission") is not None for d in docs) == 3
        assert sum(d.get("applicant_must_complete") is True for d in docs) == 6
        assert sum(d.get("applicant_signature_required") is True for d in docs) == 1
        by_id = {d["document_id"]: d for d in docs}
        assert "photo_requirements" in by_id["JP_WH_DOC_001"]
        assert "passport_copy_requirements" in by_id["JP_WH_DOC_010"]
        assert "travel_history_requirements" in by_id["JP_WH_DOC_011"]

        rules = [(doc, rule) for doc in docs for rule in doc.get("conditional_rules", [])]
        rule_ids = [rule["rule_id"] for _, rule in rules]
        assert len(rule_ids) == 9 and set(rule_ids) == EXPECTED_RULE_IDS
        assert len(rule_ids) == len(set(rule_ids)), "조건부 규칙 ID가 중복되었습니다."
        for doc, rule in rules:
            assert normalize_text(rule["evidence_text"]) in normalize_text(doc["original_text"]), (
                f"공식 원문과 불일치: {rule['rule_id']}"
            )
        source = data["source"]
        assert source["collection_mode"] == "manual"
        assert source["verified_at"] is None and source["source_license"] is None
        assert source["needs_verification"] is True
        return len(rules)

def main():
        raw_data = load_raw_data()
        documents = build_documents(raw_data)
        by_id = {doc["document_id"]: doc for doc in documents}

        attach_requirements(documents, by_id)
        attach_conditional_rules(by_id)
        result = build_result(raw_data, documents)

        # 파일을 쓰기 전에 먼저 검증한다. 실패하면 이전 JSON을 덮어쓰지 않는다.
        validate_result(result)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 저장된 파일을 다시 읽어 재검증한다.
        with OUTPUT_PATH.open("r", encoding="utf-8") as f:
            saved = json.load(f)
        rule_count = validate_result(saved)
        print("===== 리팩터링 실행 결과 =====")
        print("프로그램:", saved["route_id"], saved["program_id"])
        print("필수 서류: 12 / 조건부 서류: 2")
        print("조건부·선택 규칙:", rule_count)
        print("작성 언어: 4 / 대체 제출: 3")
        print("본인 작성: 6 / 본인 서명: 1")
        print("저장 및 구조·근거 검증: 성공")
        print("저장 경로:", OUTPUT_PATH)

if __name__ == "__main__":
    main()
