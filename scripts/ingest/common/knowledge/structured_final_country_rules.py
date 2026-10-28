"""Remaining country-specific conditions; source exceptions stay explicit."""
def rules():
    def eq(f,v):return dict(operator='equals',field=f,value=v)
    def n(op,f,v):return dict(operator=op,field=f,value=v)
    def member(f,v):return dict(operator='in',field=f,value=v)
    def all_(*c):return dict(operator='all',children=list(c))
    def any_(*c):return dict(operator='any',children=list(c))
    def review(reason):return dict(operator='manual_check',reason=reason)
    income45=any_(eq('first18a18b_issue_after45_rule_applies',False),all_(eq('salary_reference_year',2026),n('gte','annual_gross_salary_eur',55770)),eq('adequate_retirement_provision_verified',True),review('§18의 공익상 재량 예외 확인'))
    common_skilled=all_(eq('concrete_qualified_job_offer',True),any_(eq('required_ba_consent_granted',True),eq('specific_ba_consent_exemption_verified',True)),any_(eq('professional_license_not_required',True),eq('professional_license_granted_or_promised',True)),eq('genuine_employment_intention',True),income45)
    result={
        'DE_SKILLED_POL_01':all_(eq('german_qualified_vocational_or_equivalent_foreign_qualification',True),common_skilled),
        'DE_SKILLED_POL_02':all_(eq('german_recognised_or_comparable_academic_qualification',True),common_skilled),
        'DE_WH_POL_03':all_(eq('signed_visa_application',True),eq('passport_and_required_copies_valid_for_entire_stay',True),eq('two_required_recent_passport_photos',True),
            eq('own_english_bank_statement_issued_within_one_week',True),dict(operator='de_wh_financial_comparison'),eq('required_three_insurances_each30000_entire_stay',True),eq('medical_hospital_treatment_repatriation_and_required_purpose_wording_verified',True),review('각 지급증명의 공관 수리 및 해석상 계산과 공식 숫자 예시를 구분')),
        'CA_ESWP_POL_02':all_(eq('irpr200_general_eligibility_evidence',True),eq('required_medical_and_documents_available',True),review('신청 위치·입국적격성·면제 경로 심사. 허가 필요 시 발급 전 취업 금지')),
        'CA_ESWP_POL_05':all_(eq('permit_employer_occupation_location_conditions_complied',True),any_(eq('new_employer_work_not_started_before_authorisation',True),eq('specific_interim_work_authorisation_verified',True))),
        'CA_PGWP_POL_02':any_(member('completed_program_type',['bachelors','masters','doctorate','other_university','non_university']),all_(eq('eligible_dli_flight_training',True),any_(eq('canadian_commercial_pilot_license',True),all_(eq('flight_instructor_rating_held_or_in_progress',True),eq('dli_flight_school_instructor_job_offer',True))))),
        'CA_PGWP_POL_03':any_(dict(operator='date_lt',field='pgwp_application_date',value='2024-11-01'),eq('eligible_flight_school_language_exemption',True),
            all_(eq('recognised_in_person_language_test_and_clb_conversion_verified',True),dict(operator='within_calendar_years',event_field='language_test_date',reference_field='pgwp_application_date',years=2,strictly_before_reference=False,strict_after_earliest=True),
                dict(operator='switch',field='completed_program_type',cases={kind:dict(operator='four_skill_minimum',scores_field='clb_nclc_scores',minimum=minimum) for kind,minimum in [('bachelors',7),('masters',7),('doctorate',7),('other_university',7),('non_university',5)]})),review('장애로 응시 불가 영역의 공식 평균점수·설명 절차 확인')),
        'CA_PGWP_POL_04':any_(dict(operator='date_lt',field='pgwp_application_date',value='2024-11-01'),eq('pre20241101_study_permit_application_same_studies_exemption_verified',True),member('completed_program_type',['bachelors','masters','doctorate']),eq('eligible_flight_school_field_exemption',True),
            all_(eq('six_digit_cip_canada2021_verified',True),any_(eq('cip_eligible_at_relevant_study_permit_application',True),eq('cip_eligible_at_pgwp_application',True)))),
        'CA_PGWP_POL_05':any_(all_(eq('lockin_between20220901_and20240831_verified_from_earliest_dates',True),n('gte','program_percent_completed_in_canada',50),n('lt','counted_foreign_online_percent_before20240831',50),eq('postcutoff_and_prestudypermit_time_excluded',True)),
            all_(eq('lockin_on_or_after20240901_verified_from_earliest_dates',True),n('gte','program_percent_in_person_in_canada',50),eq('foreign_study_time_deducted_from_pgwp_length',True)),
            review('2020~2022 COVID 역사적 분기의 실제 등록·소재·사전 신청·과정 종료 전 승인 확인')),
        'CA_PGWP_POL_07':all_(n('gte','days_since_first_completion_confirmation',0),n('lte','days_since_first_completion_confirmation',180),
            any_(eq('normal_valid_status_application_route_verified',True),all_(eq('restoration_path_applies',True),n('gte','days_since_study_permit_expiry',0),n('lte','days_since_study_permit_expiry',90),eq('no_work_before_restoration_and_permit_approval',True))),
            review('심사 중 취업의 R186(w) 요건·석사/과정/여권별 허가기간·R197/199/182 처리와 새 입학허가서 분기 확인')),
        'CA_STUDY_POL_03':all_(eq('required_admissibility_evidence',True),any_(eq('departure_at_authorised_end_intention_verified',True),eq('irpr216_2_exception_verified',True)),review('개인별 입국적격성·필요한 경찰증명/신체검사 심사')),
        'CA_STUDY_POL_04':all_(any_(all_(eq('designated_dli_enrolment',True),eq('actively_pursuing_studies',True),eq('requested_study_evidence_available',True)),eq('specific_irpr2201_2_3_exception_verified',True)),
            any_(eq('postsecondary_dli_change',False),eq('new_study_permit_before_new_dli_start',True),all_(eq('continued_presence_in_canada',True),eq('previous_permit_conditions_met',True),member('previous_dli_change_exception_reason',['closure','course_discontinued','suspension_list','loss_of_designation'])))),
        'JP-POL-c19b5e960c1c6cf759cdcf07':all_(eq('initial_japan_stay_funds_sufficient',True),eq('funds_for_return_air_ticket_sufficient',True)),
    }
    return result
