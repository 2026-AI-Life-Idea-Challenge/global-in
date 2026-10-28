"""Common AU predicates with explicit subject scope and exception branches."""
def compile_rule(original,reviewed_text):
    if original['country']!='australia':return None
    topic=original['topic'];pid=original['policy_id']
    def eq(field,value):return dict(operator='equals',field=field,value=value)
    def all_(*children):return dict(operator='all',children=list(children))
    def any_(*children):return dict(operator='any',children=list(children))
    def manual(reason):return dict(operator='manual_check',reason=reason)
    def num(op,field,value):return dict(operator=op,field=field,value=value)
    explicit={
        'AU_191_REGIONAL_PROVISIONAL_POL_01':all_(eq('eligible_visa_for191_verified',True),num('gte','eligible_visa_held_years_at_application',3)),
        'AU_491_POL_01':eq('valid_skillselect_invitation',True),
        'AU_491_POL_02':any_(eq('state_territory_nomination_verified',True),eq('eligible_relative_sponsorship_indicated',True)),
        'AU_491_POL_03':dict(operator='age_range',birth_field='date_of_birth',event_field='invitation_date',minimum=0,maximum=44),
        'AU_491_POL_06':eq('competent_english_at_invitation_verified',True),
        'AU_494_EMPLOYER_SPONSORED_POL_01':any_(dict(operator='age_range',birth_field='date_of_birth',event_field='application_date',minimum=0,maximum=44),manual('LIN19/216 section8(1)의 지정 면제 전체 조건 확인')),
        'AU_494_LABOUR_AGREEMENT_POL_02':any_(dict(operator='age_range',birth_field='date_of_birth',event_field='application_date',minimum=0,maximum=44),manual('해당 노동협약의 연령 양허 확인')),
        'AU_494_EMPLOYER_SPONSORED_POL_02':all_(eq('approved_sponsor_nomination',True),eq('nominating_business_lawfully_operating_in_australia',True)),
        'AU_494_EMPLOYER_SPONSORED_POL_05':eq('competent_english_at_grant_verified',True),
        'AU_186_DE_POL_05':all_(eq('employer_nomination',True),eq('nominating_business_actively_and_lawfully_operating',True)),
        'AU_186_TRT_POL_02':all_(num('gte','eligible_sponsored_employment_months_in_last_three_years',24),manual('해당 스폰서·직위·비자 및 무급휴가 제외 조건 확인')),
        'AU_186_TRT_POL_04':eq('nominator_is_last_457_482_full_time_sponsor',True),
        'AU_186_TRT_POL_05':all_(eq('employer_nomination',True),eq('nominating_business_actively_and_lawfully_operating',True)),
        'AU_186_TRT_POL_07':eq('competent_english_at_grant_verified',True),
        'AU_189_PT_POL_02':all_(eq('valid_skillselect_invitation',True),eq('application_within_invitation_period',True)),
        'AU_190_POL_02':eq('valid_skillselect_invitation',True),
        'AU_190_POL_03':all_(eq('state_territory_nomination_verified',True),eq('state_nomination_not_withdrawn_at_decision',True)),
        'AU_407_POL_01':all_(eq('approved_temporary_activities_sponsor',True),manual('신청 시점 선행 요건 및 Commonwealth 기관 예외 확인')),
        'AU_494_LABOUR_AGREEMENT_POL_01':eq('nominated_occupation_covered_by_current_labour_agreement',True),
        'AU_186_LA_POL_01':eq('current_or_planned_employment_under_labour_agreement',True),
        'AU_186_LA_POL_02':any_(eq('licensing_registration_membership_not_mandatory',True),eq('required_state_territory_authorisation_held',True)),
        'AU_186_TRT_POL_03':any_(eq('licensing_registration_membership_not_mandatory',True),eq('required_state_territory_authorisation_held',True)),
        'AU_500_POL_03':any_(eq('under18_welfare_not_applicable_verified',True),eq('adequate_under18_welfare_arrangements',True)),
        'AU_500_POL_09':all_(eq('genuine_access_to_required_study_living_family_funds',True),manual('500.214 지정 재정 증빙 및 실제 비용 범위 확인')),
    }
    if pid in explicit:return explicit[pid]
    if topic=='government_debt' and 'PIC 4004' in reviewed_text:
        return all_(eq('pic4004_subject_scope_verified',True),any_(eq('no_outstanding_commonwealth_debt',True),eq('appropriate_debt_repayment_arrangements',True)))
    if topic in ('australian_values','australian_values_statement','values_statement') and 'PIC 4019' in reviewed_text:
        return any_(eq('pic4019_not_applicable_to_this_applicant_verified',True),all_(eq('pic4019_applies_to_this_applicant_verified',True),
            any_(eq('life_in_australia_read',True),eq('life_in_australia_explained',True)),eq('required_values_declaration_complete',True)))
    if topic=='points':
        return all_(num('gte','verified_points',65),dict(operator='gte_field',field='verified_points',other_field='invitation_required_points'),eq('point_claims_supported_by_evidence',True))
    if pid in ('AU_189_PT_POL_06','AU_190_POL_07'):
        return eq('competent_english_at_invitation_verified',True)
    if pid=='AU_407_POL_09':return eq('functional_english_verified',True)
    if pid=='AU_186_DE_POL_02':return any_(num('gte','relevant_occupation_work_experience_years',3),manual('실제 기술심사 면제 및 연동 경력 면제 지정 요건 확인'))
    if pid in ('AU_482_CORE_POL_07','AU_482_SPECIALIST_POL_07','AU_482_LA_02_POL'):
        return any_(all_(num('gte','relevant_full_time_equivalent_months_in_last_five_years',12),eq('experience_tasks_relevant_under_anzsco',True)),manual('해당 스트림·실제 노동협약·동등 경력 증빙 분기 확인'))
    if topic=='passport' and pid.startswith('AU_417_'):
        return all_(dict(operator='in',field='passport_country',value=['BE','CA','CY','DK','EE','FI','FR','DE','HK','IE','IT','JP','KR','MT','NL','NO','SE','TW','GB']),
            eq('passport_valid',True),eq('citizenship_or_jurisdiction_status_matches_eligible_passport_verified',True),
            any_(dict(operator='in',field='passport_country',value=['BE','CA','CY','DK','EE','FI','FR','DE','HK','IE','IT','JP','KR','MT','NL','NO','SE','GB']),eq('taiwan_passport_not_official_or_diplomatic',True)))
    if topic=='specified_work' and pid.startswith(('AU_417_','AU_462_')):
        months=6 if '_THIRD_' in pid else 3
        work=all_(num('gte','officially_verified_specified_work_months',months),eq('specified_work_industry_region_dates_remuneration_verified',True),eq('specified_work_qualifying_visa_period_verified',True))
        if pid.startswith('AU_417_'):
            return any_(work,all_(eq('passport_country','GB'),dict(operator='date_gte',field='application_date',value='2024-07-01')))
        return work
    return None
