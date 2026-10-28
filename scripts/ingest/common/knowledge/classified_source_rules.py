"""Explicit non-eligibility guidance, conflict guards and remaining comparisons.

No fallback relabels an unknown policy. Every classification is an explicit ID.
"""
import hashlib

INFORMATION={
 'AU_482_CORE_POL_01':'해당 스트림에 연령 요건 없음. 다른 요건의 면제가 아님',
 'AU_482_SPECIALIST_POL_01':'해당 스트림에 연령 요건 없음. 다른 요건의 면제가 아님',
 'CA_IEC_WH_POL_05':'가족 별도 자격·신청 단계·2026 시즌 pool 종료 안내',
 'DE_WH_POL_01':'양국 협약의 목적·최장 기간·현재 접수와 별도인 개요',
 'DE_WH_POL_04':'75유로 업무 수수료·당일 환산·환불 제한 안내',
 'US-WK-01-POL-0019':'연간 cap 수치·고급학위 면제 및 가용 인원 구분',
 'US-WK-01-POL-0052':'신분변경·영사 비자·재입국·취업 허용 절차 구분',
 'US-WK-01-POL-0064':'영사 신청·상호주의 발급·다른 수수료 구분',
 'US-WK-01-POL-0078':'I-94 체류 기한·비자 만료·연장 신청의 효과 구분',
 'US-WK-01-POL-EMP-005':'체불임금 구제 명령. 입국 자격 판정 조건이 아님',
 'US-WK-01-POL-ENF-001':'지정 판정 후 무작위 조사 권한. 자동 조사 대상 판정이 아님',
 'US-WK-01-POL-ENF-002':'지정 조사 개시의 정보·출처·기한·비공개 조건',
 'US-WK-01-POL-WPR-003':'지정 조사 경로의 사전 통지와 방해 우려 예외',
 'US-WK-01-POL-WPR-004':'조사·심리·판정의 서로 다른 60일·120일 기한',
 'US-WK-01-POL-AGL-002':'노동부 통지 후 지정 청원 승인 제한과 다른 제재의 구분',
 'US-WK-01-POL-MOD-008':'규정상 자동 취소 사유와 통지에 의한 취소 사유 구분',
 'US-WK-01-POL-MOD-009':'심사 지연 시 새 기간·LCA 등에 대한 RFE 처리',
 'US-WK-01-POL-REG-001':'최소 14일 최초 등록기간과 선정 통지 후 청원 절차',
 'US-WK-01-POL-DEF-001':'동일 당사자·사실의 이전 판단 존중과 중요 오류·변경·새 정보 예외',
}
CONFLICT_IDS=['0007','0008','0022','0053','0057','0072','0100','0103']


def rules():
    def eq(f,v):return dict(operator='equals',field=f,value=v)
    def n(op,f,v):return dict(operator=op,field=f,value=v)
    def all_(*c):return dict(operator='all',children=list(c))
    def any_(*c):return dict(operator='any',children=list(c))
    def review(reason):return dict(operator='manual_check',reason=reason)
    result={
        'US-J1-INTERN-POL-004':all_(eq('occupation_in_published_j1_intern_categories',True),eq('sponsor_designated_for_actual_occupation_category',True),review('허용 직종 명칭과 개별 금지 업무·배치 적합성의 구분')),
        'US-J1-TRAINEE-POL-007':all_(eq('occupation_in_published_j1_trainee_categories',True),eq('sponsor_designated_for_actual_occupation_category',True),review('개별 훈련·금지 배치·감독 요건 별도 확인')),
        'US-SWT-POL-006':all_(eq('complete_published_swt_prohibited_placement_screening_verified',True),
            any_(eq('staffing_agency_placement',False),all_(eq('agency_employs_and_pays_participant',True),eq('agency_fulltime_primary_onsite_supervision',True),eq('agency_effectively_controls_worksite',True))),
            eq('post20121101_naics_goods_producing_sector_exclusion_checked',True)),
        'US-WK-01-POL-0001':dict(operator='h1b_additional_fee',scope='limited_fee_condition_comparison_not_actual_current_billing_determination'),
        'US-WK-01-POL-0061':dict(operator='h1b_additional_fee',scope='limited_fee_condition_comparison_not_actual_current_billing_determination'),
        'US-WK-01-POL-0002':all_(eq('soc_and_worksite_oews_data_verified',True),eq('highest_wage_level_met_used_for_each_job',True)),
        'US-WK-01-POL-0010':dict(operator='oews_selection_weight',scope='weight_arithmetic_not_selection_probability_or_eligibility'),
        'US-WK-01-POL-WGT-002':dict(operator='oews_selection_weight',scope='weight_arithmetic_not_selection_probability_or_eligibility'),
        'US-WK-01-POL-WGT-003':all_(eq('uscis_registration_suspension_for_fiscal_year_verified',True),eq('wage_basis_evidence_as_of_petition_filing_submitted',True),dict(operator='oews_selection_weight')),
        'US-WK-01-POL-WGT-001':all_(eq('valid_selected_registration',True),eq('beneficiary_petitioner_identity_matches_registration',True),eq('occupation_soc_wage_evidence_matches_lca_and_registration',True),review('USCIS가 허용하는 지정 변경의 실제 적용 확인')),
        'US-WK-01-POL-0012':dict(operator='dated_rule',field='consular_application_date',not_before='2025-12-15',condition=all_(eq('h1b_or_h4_consular_application',True),eq('social_media_profiles_public_for_required_consular_screening',True))),
        'US-WK-01-POL-0088':any_(eq('relationship_to_h1b_holder','spouse'),all_(eq('relationship_to_h1b_holder','child'),eq('unmarried',True),n('lt','age_at_h4_application',21))),
        'US-WK-01-POL-0090':all_(any_(eq('relationship_to_h1b_holder','spouse'),all_(eq('relationship_to_h1b_holder','child'),eq('unmarried',True),n('lt','age_at_h4_application',21))),review('H4 실제 자격 및 해당 배우자의 별도 I765/EAD 요건. 가족 모두의 자동 취업 허용 금지')),
        'US-WK-01-POL-AGL-001':all_(eq('agent_relationship_under_applicable_h_regulation_verified',True),eq('agent_required_employment_terms_evidence_submitted',True),review('Agent가 실제 고용주인 경우 계약·임금 보장 및 H1B 구체적 적용 범위 확인')),
        'US-WK-01-POL-EMP-003':all_(eq('required_wage_start_is_earliest_actual_availability_or_statutory_deadline_verified',True),eq('wages_paid_from_required_start',True),review('고용 시작 전 입국30일·미국 내 자격 취득60일과 더 이른 실제 근무 시작·비생산 기간 분기 확인')),
        'US-WK-01-POL-STAY-001':all_(any_(eq('initial_or_first_extension_of_controlling_owner',False),n('lte','requested_petition_months',18)),n('lte','requested_petition_months',36),any_(n('lte','total_h1b_years_including_request',6),review('해외 체류 산입 제외·법정 6년 초과 연장 경로 확인'))),
        'US-WK-01-POL-WPR-001':all_(eq('statutory_h1b_dependency_and_five_year_willful_violator_scope_checked',True),eq('exempt_h1b_only_lca_exception_checked',True),eq('direct_petition_and_indirect_placement_90day_windows_distinguished',True),eq('displacement_definition_and_statutory_exceptions_reviewed',True)),
    }
    capgap=all_(eq('qualifying_f1_cap_subject_change_of_status_beneficiary',True),eq('timely_properly_filed_nonfrivolous_h1b_petition',True),eq('requested_start_within_qualifying_fiscal_year',True),
        eq('extension_end_is_earlier_of_fiscal_april1_or_approved_h1b_start',True),eq('status_only_vs_employment_extension_distinguished',True),review('실제 I20·OPT·EAD·접수일·거절/철회/취소 종료 사유 및 별도 소송·시행 지연 확인'))
    for pid in ('US-WK-01-POL-0092','US-WK-01-POL-0095','US-WK-01-POL-CAPGAP-001'):result[pid]=capgap
    for pid,description in INFORMATION.items():result[pid]=dict(operator='information_only',description=description,scope='official_legal_or_procedural_information_not_personal_eligibility_predicate')
    for suffix in CONFLICT_IDS:
        result['US-WK-01-POL-'+suffix]=dict(operator='source_conflict_guard',reason='USCIS 경고·서로 다른 법원 명령·적용 시점과 관할을 대조해야 함. 현재 문구만으로 개인 청원 납부·면제·적격을 확정하지 않음',scope='case_specific_authoritative_clarification_required')
    return result


def support_review_rule(profile,document):
    """Call/institution selection is explicitly evidence-dependent, not self-certified."""
    return dict(operator='official_assessment',authority_id='SUPPORT_PROVIDER:'+profile['support_program_id'],
        assessment_scope='선택한 실제 회차·과정·기관의 자격·예외·선발 조건을 별도 확인',
        criterion_sha256=hashlib.sha256(document['text'].encode()).hexdigest(),source_document_ids=[document['document_id']],
        source_references=document['source_references'],review_questions=profile['missing_information'],
        source_criterion_text=document['text'],provider=profile['provider'],
        verification_evidence=['해당 제도 운영기관의 실제 회차·과정·기관별 요건과 개인 적용 판단을 확인할 수 있는 공식 자료'],
        missing_or_conflicting_evidence_result='추가 확인 필요',user_self_certification_accepted=False,
        implementation_scope='provider_specific_verification_protocol_not_exhaustive_call_criteria_collection')
