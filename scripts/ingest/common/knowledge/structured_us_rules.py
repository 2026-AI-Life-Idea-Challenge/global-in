"""Bounded US conditions, keeping sponsor duties separate from applicant criteria."""
def rules():
    def eq(field,value):return dict(operator='equals',field=field,value=value)
    def num(op,field,value):return dict(operator=op,field=field,value=value)
    def all_(*children):return dict(operator='all',children=list(children))
    def any_(*children):return dict(operator='any',children=list(children))
    def manual(reason):return dict(operator='manual_check',reason=reason)
    result={
        'US-J1-INTERN-POL-001':all_(eq('foreign_postsecondary_degree_or_certificate_institution',True),
            any_(eq('full_time_enrolled_outside_us',True),all_(num('gte','months_from_graduation_to_program_start',0),num('lte','months_from_graduation_to_program_start',12)))),
        'US-J1-TRAINEE-POL-001':any_(all_(eq('foreign_postsecondary_degree_or_certificate',True),num('gte','related_work_experience_years_outside_us',1)),num('gte','related_work_experience_years_outside_us',5)),
        'US-J1-TRAINEE-POL-004':eq('ordinary_employment_is_program_purpose',False),
        'US-J1-TRAINEE-POL-005':eq('placement_replaces_regular_employee',False),
        'US-J1-TRAINEE-POL-006':eq('training_duplicates_prior_training_or_work',False),
        'US-J1-TRAINEE-POL-012':num('gte','training_hours_per_week',32),
        'US-F1-POL-001':eq('specific_program_sevp_f1_certified',True),
        'US-F1-POL-002':all_(eq('i20_in_own_name',True),eq('i20_from_sevp_certified_school',True)),
        'US-F1-POL-004':any_(eq('i901_paid_before_visa_issuance',True),manual('부양가족·계속 재학 등 214.13(e) 지정 수수료 면제 확인')),
        'US-F1-POL-005':any_(all_(eq('new_student',True),num('gte','days_before_program_start_at_entry',0),num('lte','days_before_program_start_at_entry',30),eq('i20_required_signatures_complete',True)),manual('계속 재학 학생 또는 별도 입국 시점 확인')),
        'US-F1-POL-006':any_(all_(eq('new_student',True),num('gte','days_before_program_start_at_entry',0),num('lte','days_before_program_start_at_entry',30),
            eq('valid_passport',True),eq('valid_required_visa',True),eq('signed_i20_available',True)),manual('계속 재학·SEVIS 유지 또는 별도 비자 면제·입국 심사 확인')),
        'US-F1-POL-007':all_(eq('i20_for_change_of_status_available',True),manual('8 CFR248 실제 신분변경 가능 범주·제외·기준일 확인')),
        'US-J1-COLLEGE-POL-002':any_(all_(eq('degree_granting_program',True),eq('program_until_degree_completion',True)),all_(eq('non_degree_program',True),num('lte','non_degree_program_months',24),eq('full_course_of_study',True))),
        'US-J1-COLLEGE-POL-004':all_(eq('academic_dean_or_adviser_approval',True),eq('sponsor_responsible_officer_approval',True),manual('학업 연계·시작 시점·기간 제한 확인')),
        'US-J1-COLLEGE-POL-006':any_(eq('admitted_to_ds2019_accredited_institution',True),eq('accepted_student_internship_at_ds2019_institution',True)),
        'US-J1-COLLEGE-POL-007':any_(eq('full_course_of_study',True),manual('공식 방학·질병·마지막 학기·승인 훈련 등 지정 예외 확인')),
        'US-SWT-POL-003':all_(eq('foreign_accredited_in_person_postsecondary',True),eq('full_time_enrolment_at_application',True),num('gte','postsecondary_semesters_completed',1)),
        'US-SWT-POL-004':any_(eq('job_placement_verified_before_entry',True),eq('eligible_vwp_nationality_for_j1_preplacement_exception',True)),
        'US-SWT-POL-005':all_(num('gt','program_months',0),num('lte','program_months',4),eq('during_long_academic_vacation',True),eq('return_before_next_academic_term',True)),
        'US-WK-01-POL-0023':any_(all_(eq('selected_registration_for_current_fiscal_year_and_beneficiary',True),eq('registration_valid',True)),manual('청원 cap 면제·등록 중단 등의 지정 예외 확인')),
        'US-WK-01-POL-0024':any_(eq('foreign_degree_equivalent_to_required_us_degree',True),manual('미국 학위·면허·교육훈련경력 동등성 대체 경로 확인')),
        'US-WK-01-POL-ADD-001':any_(eq('relevant_us_degree_from_accredited_institution',True),manual('외국 학위·면허·교육훈련경력 동등성 대체 경로 확인')),
        'US-WK-01-POL-ADD-002':any_(eq('unrestricted_state_professional_license',True),manual('학위·교육훈련경력 동등성 대체 경로 확인')),
        'US-WK-01-POL-ADD-003':any_(eq('education_training_experience_equivalence_and_expertise_verified',True),manual('학위·면허 대체 경로 확인')),
        'US-WK-01-POL-ADD-004':all_(eq('certified_lca_evidence_with_i129',True),manual('LCA·청원 내용 일치와 나머지 요건 확인')),
        'US-WK-01-POL-0030':eq('h1b_registrant_account_type','organizational'),
        'US-WK-01-POL-0045':all_(eq('valid_registration_passport_or_travel_document',True),eq('passport_number_issuer_expiry_entered',True)),
        'US-WK-01-POL-0050':all_(eq('registration_truthfulness_attested',True),eq('actual_employment_offer_exists',True)),
        'US-WK-01-POL-0069':eq('beneficiary_registration_fee_paid',True),
        'US-WK-01-POL-REG-003':eq('registration_collusion',False),
        'US-WK-01-POL-REG-005':num('lte','same_petitioner_beneficiary_registrations_in_fiscal_year',1),
        'US-WK-01-POL-MOD-001':eq('actual_specialty_position_at_requested_start',True),
        'US-WK-01-POL-MOD-002':eq('lca_corresponds_to_petition',True),
        'US-WK-01-POL-MOD-004':all_(eq('genuine_us_job_offer',True),eq('us_employer_legal_presence',True),eq('employer_amenable_to_service',True),eq('irs_tax_identifier_available',True)),
        'US-WK-01-POL-MOD-006':all_(num('gt','specialty_occupation_work_time_percent',50),manual('청원인 소유주 여부와 관련 경영 업무의 허용 범위 확인')),
        'US-WK-01-POL-STAY-002':all_(num('gte','days_since_relevant_labor_certification_or_immigrant_petition_filing',365),manual('6년 초과 체류의 추가 요건·결정 상태 확인')),
    }
    prohibited=all_(eq('unskilled_or_casual_labor',False),eq('childcare_or_eldercare',False),eq('medical_patient_care_or_contact',False))
    for prefix in ('US-J1-INTERN','US-J1-TRAINEE'):
        result[prefix+'-POL-002']=prohibited
        result[prefix+'-POL-003']=all_(num('gte','clerical_work_percent',0),num('lte','clerical_work_percent',20))
    for pid in ('US-J1-INTERN-POL-009','US-J1-TRAINEE-POL-013'):
        result[pid]=all_(eq('ds7002_complete',True),eq('host_ds7002_signed',True),eq('all_required_ds7002_signatures_before_ds2019',True))
    for pid in ('US-J1-INTERN-POL-011','US-J1-TRAINEE-POL-014'):
        result[pid]=eq('experienced_staff_continuous_onsite_supervision',True)
    for pid in ('US-J1-INTERN-POL-001','US-J1-TRAINEE-POL-001'):
        result[pid]=all_(eq('us_citizen',False),result[pid])
    return result
