"""일본 워킹홀리데이: 공식 원문 기반 자격요건 구조화 스크립트.

실행: python scripts/ingest/structure_japan_working_holiday.py
주의: 11개 규칙은 검토용 초안이며 자동 비자 승인 판정 기준이 아님.
"""

import json
from pathlib import Path

# __file__ 기준으로 실행 위치에 관계없이 프로젝트 루트를 계산한다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MOFA_PATH = PROJECT_ROOT / "data" / "raw" / "japan_working_holiday_eligibility.json"
EMBASSY_PATH = PROJECT_ROOT / "data" / "raw" / "japan_working_holiday_embassy_eligibility.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "japan_working_holiday_rules.json"


def load_json(path: Path) -> dict:
    """파일을 읽고 JSON 객체를 반환한다. 없거나 JSON 문법이 잘못되면 예외 발생."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_rules(mofa_data: dict, embassy_data: dict) -> dict:
    """공식 안내문을 사람이 검토해 정의한 11개 규칙 초안을 생성한다."""
    return {
        # 보완 STEP 21. 프로그램 식별자 통일

        # 상위 경로 ID
        "route_id": "JP-WH",

        # 팀원 데이터셋과 동일한 개별 프로그램 ID
        "program_id": "JP-WH-01",

        # 신청 대상 국적
        "target_nationality": "KR",

        # 공식 근거 출처
        "sources": {
            "mofa": mofa_data["source"]["source_url"],
            "embassy": embassy_data["source"]["source_url"],
        },

        # 보완 STEP 36-2. 자격요건 데이터 출처 및 검증 메타데이터
        "source_metadata": {

            # 데이터 수집 방식
            "collection_mode": "manual",

            # 수집 당시 공식 페이지에 표시되어 있던 날짜
            # 실제 웹페이지 수정일과 반드시 같은 의미는 아님
            "page_display_dates": {
                "mofa": "2026-04-01",
                "embassy": "2026-09-30",
            },

            # 정확한 최초 수집 시각은 확인되지 않음
            "extracted_at": None,

            # 정책 검증 완료일은 아직 지정하지 않음
            "verified_at": None,

            # 원문 재사용 라이선스는 미확인
            "source_license": None,

            # 최종 정책 검토가 필요함
            "needs_verification": True,

            # 확인이 필요한 내용
            "validation_status": "needs_review",
        },

        # 기존 11개 자격요건은 그대로 유지
        "requirements": [
            {
                'rule_id': 'JP_WH_001',
                'field': 'nationality',
                'operator': 'equals',
                'value': 'KR',
                'source': 'embassy',
                'description': '대한민국 국민일 것',
                'validation_status': 'needs_review',
            },
            {
                'rule_id': 'JP_WH_002',
                'field': 'residence_country',
                'operator': 'equals',
                'value': 'KR',
                'source': 'embassy',
                'description': '현재 대한민국에 거주할 것',
                'validation_status': 'needs_review',
            },
            {
                'rule_id': 'JP_WH_003',
                'field': 'age_at_application',
                'operator': 'range_with_exception',
                'normal_range': {'min': 18, 'max': 25},
                'exception_range': {'min': 26, 'max': 30},
                'exception_condition': '부득이한 사정 인정 필요',
                'source': 'embassy',
                'description': '신청 시 원칙적으로 18~25세, 예외적으로 30세 이하',
                'validation_status': 'needs_review',
            },
            {
                'rule_id': 'JP_WH_004',
                'field': 'previous_visa_issuances',
                'operator': 'less_than_or_equal',
                'value': 1,
                'source': 'embassy',
                'description': '과거 워킹홀리데이 사증 발급 횟수가 0회 또는 1회일 것',
                "note": (
                    "특단의 사정 없이 출국을 취소하거나 연기하여 "
                    "발급된 워킹홀리데이 사증을 사용하지 않은 채 "
                    "실효된 경우에도 발급 1회로 계산"
                ),
                "additional_evidence": {
                    "source": "embassy",
                    "source_url": "https://www.kr.emb-japan.go.jp/itpr_ko/visa_working.html",
                    "original_text": (
                        "※특단의 사정 없이 도항을 취소하거나 연기하여, "
                        "이미 발급된 워킹홀리데이 사증을 사용하지 않은 채 "
                        "실효된 경우 1회 발급받은 것으로 간주함."
                    ),
                },
                # 보완 STEP 37. 한국인 워킹홀리데이 2회 참가 정책
                'visa_issuance_policy': {

                    # 변경된 정책이 실제로 시행된 날짜
                    'effective_from': '2025-10-01',

                    # 평생 최대 참가 횟수
                    'maximum_lifetime_participations': 2,

                    # 두 번의 체류는 비연속적인 1년 체류
                    'stay_pattern': 'two_nonconsecutive_one_year_stays',

                    # 기존 발급 횟수 조건과 연결
                    'previous_issuances_allowed': [0, 1],

                    # 일본 외무성 공식 근거
                    'evidence': {
                        'source': 'mofa',
                        'source_url': (
                            'https://www.mofa.go.jp/j_info/visit/w_holiday/'
                        ),
                        'original_text': (
                            'Starting from 1 October, 2025, the nationals '
                            'of South Korea are allowed to participate '
                            'in the Working Holiday Programmes twice in '
                            'lifetime (two inconsecutive one-year stays '
                            'in total).'
                        ),
                    },

                    'validation_status': 'needs_review',
                },
                'validation_status': 'needs_review',
            },
            {
                'rule_id': 'JP_WH_005',
                'field': 'accompanying_children',
                'operator': 'equals',
                'value': False,
                'source': 'embassy',
                'description': '자녀를 동반하지 않을 것',

                # 일본 외무성의 일반 요건을 추가 근거로 보존
                'additional_evidence': {
                    'source': 'mofa',
                    'source_url': 'https://www.mofa.go.jp/j_info/visit/w_holiday/',
                    'original_text': (
                        'Not being accompanied by dependents or children.'
                    ),
                    'note': (
                        '외무성 일반 안내는 부양가족과 자녀를 모두 언급하지만, '
                        '주한일본대사관의 한국 대상 안내는 자녀만 명시함. '
                        '적용 범위에 대한 추가 검토가 필요함.'
                    ),
                    'validation_status': 'needs_review',
                },
                # 외무성 안내와 한국 대상 안내의 표현 차이를 확인하기 위한 필드
                'review_fields': [
                    {
                        # 신청자가 부양가족을 동반하는지 확인
                        'field': 'accompanying_dependents',

                        # 입력값은 True, False, None 중 하나
                        'value_type': 'boolean',

                        # 추가 확인 질문
                        'question': '일본 체류 시 부양가족을 동반할 예정인가요?',

                        # 부양가족을 동반한다면 자동 승인하지 않음
                        'review_when': True,

                        # 해당 상황에서 권장하는 개별 판정 상태
                        'review_status': 'NEEDS_REVIEW',

                        # 국가별 적용 범위에 대한 정책 검토가 필요함
                        'validation_status': 'needs_review',
                    }
                ],
                'validation_status': 'needs_review',
            },
            {
                'rule_id': 'JP_WH_006',
                'field': 'available_funds_krw',
                'operator': 'manual_review',
                'reference_amount': 2800000,
                'source': 'embassy',
                'description': '귀국 항공권 구입비 및 초기 체류비로 약 280만 원',
                'note': '안내 금액이므로 단순 수치 비교만으로 최종 자격 확정 금지',
                # 자금 증빙 방식에 대한 추가 확인 정보
                'funds_evidence_policy': {

                    # 본인 명의 은행 잔고증명서
                    'primary_document': '본인 명의 은행 잔고증명서',

                    # 가족 명의 잔고증명서를 사용할 수 있는 상황
                    'family_support_allowed': True,

                    'family_support_condition': (
                        '가족으로부터 부양을 받고 있는 학생 등'
                    ),

                    # 가족 명의 잔고증명서 사용 시 추가 서류
                    'family_support_documents': [
                        '부양하는 가족 명의의 은행 잔고증명서',
                        '부양자와의 관계를 증명하는 가족관계증명서',
                    ],

                    # 제출서류 데이터와 연결
                    'related_document_id': 'JP_WH_DOC_009',

                    # 참고 금액은 절대적인 자동 탈락 기준이 아님
                    'amount_is_approximate': True,

                    # 공식 원문
                    'evidence_text': (
                        '학생 등이 가족으로부터 부양을 받고 있는 경우는 '
                        '신청인 계좌(통장)가 아니라도 부양하는 가족의 '
                        '은행 발행의 잔고증명서도 가능하지만, '
                        '이때는 부양자와의 관계를 알 수 있는 '
                        '가족관계증명서를 제출해 주십시오.'
                    ),

                    'validation_status': 'needs_review',
                },
            },
            {
                'rule_id': 'JP_WH_007',
                'field': 'health',
                'operator': 'manual_review',
                'source': 'embassy',
                'description': '건강할 것',
            },
            {
                'rule_id': 'JP_WH_008',
                'field': 'japanese_language',
                'operator': 'manual_review',
                'source': 'embassy',
                'description': '최소한의 일본어 능력 또는 일본어 습득 의욕',
                # 보완 STEP 32-2. 일본어 능력 및 학습 의지 조건
                'japanese_language_policy': {

                    # 두 조건 중 하나를 충족하는 구조
                    'option_logic': 'OR',

                    # 공식 원문에 명시된 두 가지 조건
                    'acceptable_conditions': [
                        'basic_japanese_proficiency',
                        'willingness_to_learn_japanese',
                    ],

                    # 일본어 능력 입증자료와 연결
                    'related_document_id': 'JP_WH_DOC_014',

                    # 자격증 미보유만으로 자동 탈락 처리하지 않음
                    'certificate_required_for_eligibility': False,

                    # 구체적인 능력·학습 의지 판단은 추가 검토
                    'requires_individual_review': True,

                    'validation_status': 'needs_review',
                },
            },
            {
                'rule_id': 'JP_WH_009',
                'field': 'primary_purpose',
                'operator': 'manual_review',
                'source': 'embassy',
                'description': '일본에서 휴가를 보내는 것이 주목적',
                # 보완 STEP 33-2. 워킹홀리데이의 주된 체류 목적
                'purpose_policy': {

                    # 공식 요건상 주된 체류 목적
                    'required_primary_purpose': 'holiday',

                    # 서비스에서 확인할 사용자 정보
                    'review_fields': [
                        {
                            'field': 'primary_purpose',

                            'question': (
                                '일본에 체류하려는 가장 주된 목적은 무엇인가요?'
                            ),

                            # 답변 예시이며 공식적으로 정해진 선택지는 아님
                            'example_options': [
                                'holiday',
                                'cultural_experience',
                                'employment',
                                'study',
                                'other',
                            ],
                        }
                    ],

                    # 목적을 단순 문자열 비교로 확정하지 않음
                    'requires_individual_review': True,

                    # 체류 계획을 확인하는 관련 제출서류
                    'related_document_ids': [
                        'JP_WH_DOC_003',  # 지원 이유 진술서
                        'JP_WH_DOC_004',  # 일본 체류 활동계획 진술서
                    ],

                    'validation_status': 'needs_review',
                },
            },
            {
                'rule_id': 'JP_WH_010',
                'field': 'valid_passport',
                'operator': 'equals',
                'value': True,
                'source': 'mofa',
                'description': '유효한 여권을 소지할 것',
                # 보완 STEP 34-1. 여권 유효성 및 제출서류 연결
                'passport_policy': {

                    # 일본 외무성에서 요구하는 기본 자격
                    'valid_passport_required': True,

                    # 관련 제출서류 ID
                    'related_document_id': 'JP_WH_DOC_010',

                    # 현재 확보한 원문에는 잔여 유효기간 기준이 없음
                    # None은 제한이 없다는 뜻이 아니라 확인되지 않았다는 뜻
                    'minimum_remaining_validity_months': None,

                    # 여권 사본의 구체적인 제출 페이지는
                    # JP_WH_DOC_010에 이미 구조화되어 있음
                    'copy_requirements_defined_in_document': True,

                    # 세부 규정은 추가 확인 필요
                    'validation_status': 'needs_review',
                },
            },
            {
                'rule_id': 'JP_WH_011',
                'field': 'return_travel_funds',
                'operator': 'manual_review',
                'source': 'mofa',
                'description': '귀국 항공권 또는 이를 구입할 충분한 자금',
                'note': '대사관은 귀국 항공권 구입비와 초기 체류비로 약 280만 원을 안내함. JP_WH_006과 함께 검토할 것.',
                # 보완 STEP 30-2. 귀국 항공권과 자금 요건 연결

                'return_travel_policy': {

                    # 귀국 항공권을 이미 보유한 경우와
                    # 항공권을 구입할 자금이 있는 경우를 구분
                    'acceptable_options': [
                        'return_ticket',
                        'sufficient_funds_to_purchase_return_ticket',
                    ],

                    # 둘 중 하나를 충족하는 구조
                    'option_logic': 'OR',

                    # 종합 자금 요건과 연결
                    'related_rule_id': 'JP_WH_006',

                    # 관련 제출서류
                    'related_document_id': 'JP_WH_DOC_009',

                    # 별도의 금액을 중복 합산하지 않음
                    'avoid_double_counting': True,

                    # 귀국 항공권 확보 여부는 별도 확인
                    'requires_individual_review': True,

                    # 아직 정책 검토가 완료되지 않음
                    'validation_status': 'needs_review',
                },
            },
        ],
        'validation_status': 'needs_review',
    }


# (rule_id, 출처, 원문 발췌)
# 원문 문장이 두 규칙에 모두 적용되는 경우 동일 근거를 재사용한다.
EVIDENCE_ITEMS = [
    ("JP_WH_001", "embassy", "대한민국에 거주하는 대한민국 국민일 것."),
    ("JP_WH_002", "embassy", "대한민국에 거주하는 대한민국 국민일 것."),
    ("JP_WH_003", "embassy", "사증신청 시점에서 원칙적으로 18세 이상 25세(부득이한 사정이 있다고 인정되는 경우는 30세) 이하일 것."),
    ("JP_WH_004", "embassy", "과거 워킹홀리데이 사증을 발급받은 횟수가 1회 또는 0회일 것."),
    ("JP_WH_005", "embassy", "자녀를 동반하지 않는 자일 것."),
    ("JP_WH_006", "embassy", "귀국 시 비행기 표를 구입하기에 충분한 자금과 일본에서의 체재 초기에 생계를 유지할 수 있을 만큼의 자금을 소지할 것 (280만원 정도)."),
    ("JP_WH_007", "embassy", "건강할 것."),
    ("JP_WH_008", "embassy", "일본에서 생활하기 위해 필요한 최저한도의 일본어 능력을 갖고 있거나, 혹은 습득할 의욕을 가질 것."),
    ("JP_WH_009", "embassy", "주된 목적이 휴가를 보내기 위해 일본에 입국할 의도를 가질 것."),
    ("JP_WH_010", "mofa", "Possessing a valid passport of his or her country/region and a return travel ticket or sufficient funds with which to purchase such a ticket."),
    ("JP_WH_011", "mofa", "Possessing a valid passport of his or her country/region and a return travel ticket or sufficient funds with which to purchase such a ticket."),
]


def attach_evidence(rules: dict, documents: dict) -> None:
    """근거 문장이 수집한 원문에 존재할 때만 해당 규칙에 첨부한다."""
    rule_by_id = {rule["rule_id"]: rule for rule in rules["requirements"]}

    for rule_id, source_name, quote in EVIDENCE_ITEMS:
        if rule_id not in rule_by_id:
            raise ValueError(f"규칙 ID가 존재하지 않습니다: {rule_id}")
        if source_name not in documents:
            raise ValueError(f"출처가 존재하지 않습니다: {source_name}")

        document = documents[source_name]
        if quote not in document["eligibility_raw_text"]:
            raise ValueError(f"공식 원문에서 근거를 찾지 못했습니다: {rule_id}")
        rule = rule_by_id[rule_id]
        if rule["source"] != source_name:
            raise ValueError(f"규칙의 출처와 근거 출처가 다릅니다: {rule_id}")

        rule["evidence"] = {
            "source": source_name,
            "source_url": document["source"]["source_url"],
            "original_text": quote,
        }


def validate_rules(rules: dict) -> None:
    """필수 필드, 규칙 ID 중복, 근거 연결을 확인한다 (정책 해석 검증은 아님)."""
    requirements = rules["requirements"]
    required_keys = {"rule_id", "field", "operator", "source", "description", "evidence"}
    ids = [rule["rule_id"] for rule in requirements]

    if len(requirements) != 11:
        raise ValueError(f"규칙 개수 오류: {len(requirements)}")
    if len(ids) != len(set(ids)):
        raise ValueError("규칙 ID가 중복되었습니다.")

    for rule in requirements:
        missing = required_keys - rule.keys()
        if missing:
            raise ValueError(f"{rule['rule_id']} 필수 필드 누락: {sorted(missing)}")
        if rule["source"] != rule["evidence"]["source"]:
            raise ValueError(f"근거 출처 불일치: {rule['rule_id']}")


def main() -> None:
    """원문 읽기 → 규칙 생성 → 근거 연결 → 검증 → JSON 저장 → 재검증."""
    documents = {
        "mofa": load_json(MOFA_PATH),
        "embassy": load_json(EMBASSY_PATH),
    }
    rules = build_rules(documents["mofa"], documents["embassy"])
    attach_evidence(rules, documents)
    rules["validation_status"] = "evidence_attached_needs_review"

    # 보완 STEP 44-2. Rule Evaluator 판정 상태 정의
    # 현재는 데이터 구조만 정의하며, 실제 판정 로직은 구현하지 않음.

    rules["evaluation_policy"] = {

        # Rule Evaluator가 사용할 판정 상태
        "supported_statuses": [
            "ELIGIBLE",
            "INELIGIBLE",
            "NEEDS_REVIEW",
            "UNKNOWN",
            "BLOCKED_BY_KR_RULE",
        ],

        # 필수 입력값이 누락된 경우
        "missing_input_status": "UNKNOWN",

        # 개별 검토가 필요한 경우
        "manual_review_status": "NEEDS_REVIEW",

        # 공식 기관의 예외 인정이 필요한 경우
        "exception_review_status": "NEEDS_REVIEW",

        # 한국 측 제한이 확인된 경우에만 적용
        "kr_rule_block_requires_evidence": True,

        # 현재 정책은 설계 단계이며 실제 구현·테스트 전
        "implementation_status": "not_implemented",

        "validation_status": "needs_review",
    }

    validate_rules(rules)

    # 최종 상태를 한 번만 저장한다.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 보완 STEP 42-1. 개별 자격요건 검토 상태 추가

    # 최종 구조화 결과의 11개 자격요건을 순회
    for rule in rules["requirements"]:

        # 공식 근거가 연결되어 있는지 확인
        if not rule.get("evidence"):
            raise ValueError(
                f"공식 근거가 누락된 규칙: {rule['rule_id']}"
            )

        # 각 규칙의 정책 검토 상태를 통일
        rule["validation_status"] = "needs_review"

    # 보완 STEP 43-2. 규칙별 판정 방식 구조화

    # 연산자별 평가 방식 정의
    evaluation_modes = {
        "equals": "automatic",
        "less_than_or_equal": "automatic",
        "range_with_exception": "automatic_with_exception",
        "manual_review": "manual",
    }

    # 자격요건 11개에 평가 방식 추가
    for rule in rules["requirements"]:

        operator = rule["operator"]

        # 정의하지 않은 연산자가 있으면 오류 발생
        if operator not in evaluation_modes:
            raise ValueError(
                f"지원하지 않는 연산자: {rule['rule_id']} / {operator}"
            )

        # 연산자에 맞는 평가 방식 저장
        rule["evaluation_mode"] = evaluation_modes[operator]

        # 실제 Rule Evaluator 구현 및 테스트 여부
        # 아직 확인하지 않았으므로 False로 유지
        rule["evaluator_tested"] = False

    # 개별 검토 상태를 추가한 후 전쳋 구조 검증
    validate_rules(rules)

    # 최종 JSON 저장
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(rules, file, ensure_ascii=False, indent=2)

    # 디스크에 기록된 JSON을 다시 읽어 저장 결과를 검증한다.
    saved = load_json(OUTPUT_PATH)
    validate_rules(saved)
    print("===== 리팩터링 실행 결과 =====")
    print("파일:", OUTPUT_PATH)
    print("규칙 수:", len(saved["requirements"]))
    print("근거 수:", sum("evidence" in r for r in saved["requirements"]))
    print("검증 상태:", saved["validation_status"])
    print("저장 및 구조 검증: 성공")


# 다른 모듈에서 import할 때는 실행하지 않고, 직접 실행할 때만 main() 호출
if __name__ == "__main__":
    main()