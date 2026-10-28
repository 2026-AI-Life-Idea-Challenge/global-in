"""AU visa-history, sponsor, insurance and country-specific education branches."""
def rules():
    def eq(f,v):return dict(operator='equals',field=f,value=v)
    def n(op,f,v):return dict(operator=op,field=f,value=v)
    def member(f,v):return dict(operator='in',field=f,value=v)
    def all_(*c):return dict(operator='all',children=list(c))
    def any_(*c):return dict(operator='any',children=list(c))
    def review(reason):return dict(operator='manual_check',reason=reason)
    no48=any_(eq('in_australia',False),eq('holds_substantive_visa',True),eq('relevant_refusal_or_cancellation_since_last_entry',False),eq('current_visa_class_permitted_by_reg212_verified',True))
    history=all_(no48,review('s501E·PIC4013/4014·특별 재입국 기준 및 실제 신청 유효성의 적용 여부 확인'))
    result={
        'AU_186_DE_POL_03':any_(dict(operator='age_range',birth_field='date_of_birth',event_field='application_date',minimum=0,maximum=44),review('LIN19/216 section6(2) academic·science·444/461 worker의 지정 정의·기간·무급휴가 제외 및 경과 요건 전체 확인')),
        'AU_186_DE_POL_04':any_(eq('appropriate_positive_skills_assessment',True),review('해당 academic·science·444/461 worker 기술심사 면제의 지정 요건 확인')),
        'AU_186_DE_POL_10':all_(eq('primary_applicant_competent_english_at_grant',True),any_(eq('adult_dependants_functional_english',True),eq('required_second_instalment_paid_when_requested',True),eq('no_applicable_adult_dependants',True))),
        'AU_186_LA_POL_03':all_(eq('employer_nomination',True),eq('nominating_business_actively_and_lawfully_operating',True),eq('nominator_party_to_current_labour_agreement',True),eq('nomination_not_withdrawn',True),eq('nominated_position_still_available',True),any_(eq('nominator_adverse_information',False),review('장관이 불리한 정보를 무시하는 것이 합리적인지 실제 판단 확인'))),
        'AU_186_LA_POL_05':any_(eq('in_australia',False),all_(member('current_substantive_visa',['457','482']),eq('visa_issued_under_labour_agreement',True))),
        'AU_186_TRT_POL_01':eq('skills_and_qualifications_for_nominated_tasks_verified',True),
        'AU_186_TRT_POL_08':all_(eq('primary_visa_holder',True),any_(member('current_substantive_visa',['457','482']),all_(eq('qualifying_bridging_visa',True),member('bridging_associated_application',['457','482','186','187']),member('last_substantive_visa',['457','482'])))),
        'AU_189_PT_POL_01':all_(any_(eq('in_australia',False),eq('holds_substantive_visa',True),member('current_bridging_visa',['A','B','C'])),any_(eq('current_or_last_substantive_is491or494',False),n('gte','relevant_491_494_visa_held_years_at_application',3))),
        'AU_190_POL_01':all_(any_(eq('in_australia',False),eq('holds_substantive_visa',True),member('current_bridging_visa',['A','B','C'])),any_(eq('current_or_last_substantive_is491or494',False),n('gte','relevant_491_494_visa_held_years_at_application',3))),
        'AU_407_POL_02':any_(eq('sponsor_is_commonwealth_government_agency',True),all_(eq('occupational_training_nomination_approved_before_application',True),member('training_type',['registration','improve_eligible_occupation_skills','capacity_building_overseas']))),
        'AU_407_POL_04':any_(eq('in_australia',False),all_(eq('current_or_last_visa_is_excluded407_class',False),any_(eq('valid_temporary_substantive_visa',True),all_(eq('holds_substantive_visa',False),n('gte','days_since_relevant_expiry_or_art_notification',0),n('lte','days_since_relevant_expiry_or_art_notification',28))))),
        'AU_417_FIRST_POL_03':all_(eq('previously_entered_on417',False),eq('previously_entered_on462',False)),
        'AU_462_FIRST_POL_03':all_(eq('previously_entered_on417',False),eq('previously_entered_on462',False)),
        'AU_482_LA_01_POL':eq('nominated_occupation_covered_by_current_labour_agreement',True),
        'AU_482_LA_03_POL':eq('required_nomination',True),
        'AU_482_LA_06_POL':review('해당 직종·실제 노동협약의 영어 기준·명시적 양허와 일반482 기준을 대조'),
        'AU_494_LABOUR_AGREEMENT_POL_03':all_(eq('skills_qualifications_experience_meet_actual_labour_agreement',True),review('494.235 및 해당 협약의 실제 경력 기간·양허 증빙 확인')),
        'AU_494_LABOUR_AGREEMENT_POL_04':any_(eq('skills_assessment_not_required_under_actual_agreement',True),eq('required_appropriate_positive_skills_assessment',True)),
        'AU_494_LABOUR_AGREEMENT_POL_05':eq('english_meets_actual_labour_agreement',True),
        'AU_500_POL_02':all_(any_(all_(eq('cricos_course_enrolment',True),eq('all_uncancelled_coe_numbers_entered_at_application',True)),eq('permitted_government_exchange_or_thesis_alternative_evidence',True)),review('결정 시500.211·코스 패키지 연결·간격·2026년 호주 내 재신청의 별도 예외 조건 확인')),
        'AU_500_POL_05':any_(eq('oshc_for_applicable_applicants_from_arrival_through_stay',True),eq('designated_norway_sweden_belgium_insurance_exception_verified',True)),
    }
    for pid in ('AU_186_DE_POL_12','AU_186_LA_POL_10','AU_186_TRT_POL_13','AU_189_PT_POL_12','AU_407_POL_12','AU_417_FIRST_POL_08','AU_417_SECOND_POL_09','AU_417_THIRD_POL_09','AU_462_FIRST_POL_11','AU_462_SECOND_POL_09','AU_462_THIRD_POL_09','AU_482_CORE_POL_14','AU_482_LA_10_POL','AU_482_SPECIALIST_POL_13','AU_500_POL_15'):result[pid]=history
    result['AU_191_REGIONAL_PROVISIONAL_POL_06']=all_(eq('pic4004_subject_scope_verified',True),any_(eq('no_outstanding_commonwealth_debt',True),eq('appropriate_debt_repayment_arrangements',True)),history)
    for pid in ('AU_407_POL_07','AU_482_CORE_POL_09','AU_482_LA_08_POL','AU_482_SPECIALIST_POL_09'):
        result[pid]=all_(eq('adequate_australian_health_insurance_for_entire_intended_stay',True),eq('applicable_condition8501_compliance_arranged',True))
    for prefix in ('AU_417','AU_462'):
        result[prefix+'_SECOND_POL_02']=all_(eq('one_first_same_subclass_held',True),eq('entered_australia_on_first_same_subclass',True),eq('first_same_subclass_conditions_complied',True),any_(eq('in_australia',False),eq('holds_substantive_visa',True),all_(n('gte','days_since_last_substantive_expiry',0),n('lt','days_since_last_substantive_expiry',28))))
        result[prefix+'_THIRD_POL_02']=all_(any_(eq('second_same_subclass_held',True),eq('bridging_effective_on_second_same_subclass_expiry',True)),eq('relevant_previous_same_subclass_conditions_complied',True),any_(eq('in_australia',False),eq('holds_substantive_visa',True),all_(n('gte','days_since_last_substantive_expiry',0),n('lt','days_since_last_substantive_expiry',28))))
    for pid in ('AU_417_FIRST_POL_04','AU_417_SECOND_POL_03','AU_417_THIRD_POL_03','AU_462_FIRST_POL_07','AU_462_SECOND_POL_03','AU_462_THIRD_POL_03'):
        result[pid]=all_(eq('initial_australian_stay_funds_sufficient_for_actual_case',True),any_(eq('departure_ticket_available',True),eq('separate_departure_funds_sufficient',True)))
    for prefix in ('AU_482_CORE','AU_482_SPECIALIST'):
        result[prefix+'_POL_02']=any_(eq('in_australia',False),eq('holds_substantive_visa',True),member('current_bridging_visa',['A','B','C']))
        result[prefix+'_POL_03']=any_(eq('in_australia_at_decision',False),eq('last_substantive_and_bridging_conditions_substantially_complied',True))
        result[prefix+'_POL_04']=all_(eq('employer_nomination_application_lodged',True),any_(eq('approved_standard_business_sponsor',True),eq('standard_business_sponsorship_application_lodged',True)))
        result[prefix+'_POL_05']=any_(all_(eq('employed_in_nominated_occupation',True),any_(all_(eq('sponsor_is_australian_business',True),eq('employed_by_sponsor_or_associated_entity',True)),all_(eq('sponsor_is_overseas_business',True),eq('employed_by_sponsor_only',True)))),review('지정 직종의 고용관계 면제 적용 확인'))
        result[prefix+'_POL_06']=all_(eq('skills_and_experience_for_nominated_tasks_verified',True),any_(eq('nominated_medical_practitioner',False),eq('medical_qualifications_recognised_for_australian_registration',True)),review('필수 기술심사 또는 허용되는 다른 직무능력 증빙 확인'))
        result[prefix+'_POL_08']=any_(eq('mandatory482_assessment_not_applicable_verified',True),all_(eq('appropriate_mandatory482_assessment_commenced_before_application',True),n('lte','months_since_assessment_commenced_at_application',36),eq('relevant_assessment_reference_provided',True)))
    result['AU_482_CORE_POL_12']=any_(eq('prohibited_sponsorship_benefit_conduct_in_last_three_years',False),review('장관이 해당 행위를 무시하는 것이 합리적인지 판단 확인'))
    for pid in ('AU_189_PT_POL_03','AU_190_POL_04','AU_491_POL_04'):
        result[pid]=all_(eq('assessment_for_correct_nominated_occupation_and_migration_purpose',True),any_(eq('appropriate_assessment_valid_at_invitation',True),all_(eq('thapa_current_administrative_path_applies',True),n('gte','days_from_invitation_to_assessment',0),n('lte','days_from_invitation_to_assessment',60)),eq('permitted_medical_or_legal_registration_alternative_verified',True)),review('심사 유효기간·지정 평가기관·Thapa 수용 방침의 실제 적용·CRICOS 조건을 대조'))
    for pid in ('AU_186_DE_POL_01','AU_189_PT_POL_07','AU_190_POL_08','AU_491_POL_07'):
        result[pid]=all_(eq('occupation_on_correct_visa_stream_instrument_list',True),eq('occupation_code_assessing_authority_and_caveats_verified',True))
    result['AU_494_EMPLOYER_SPONSORED_POL_03']=all_(eq('skills_qualifications_experience_for_nominated_tasks_verified',True),review('주신청자 적용 및 경력 기간·해당 면제 증빙 확인'))
    result['AU_494_EMPLOYER_SPONSORED_POL_04']=any_(eq('positive_relevant_occupation_skills_assessment',True),review('해당 instrument의 지정 기술심사 면제 확인'))
    eligible462=['AR','AT','BR','CL','CN','CZ','EC','GR','HU','IN','ID','IL','LU','MY','MN','PG','PE','PH','PL','PT','SM','SG','SK','SI','ES','CH','TH','TR','US','UY','VN']
    for suffix in ('FIRST_POL_01','SECOND_POL_01','THIRD_POL_01'):
        result['AU_462_'+suffix]=all_(member('passport_country',eligible462),eq('passport_valid',True),eq('citizenship_matches_required462_passport',True))
    result['AU_462_FIRST_POL_06']=any_(member('passport_country',['AR','AT','BR','CL','CN','CZ','HU','IN','IL','LU','PG','PT','SG','SK','ES','CH','US','UY','VN']),eq('required_home_government_support_obtained',True))
    return result
