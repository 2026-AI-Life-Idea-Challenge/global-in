"""Source-specific conditions. Alternative routes remain separate conditions."""
def rules():
    def eq(field,value):return dict(operator='equals',field=field,value=value)
    def num(op,field,value):return dict(operator=op,field=field,value=value)
    def all_(*children):return dict(operator='all',children=list(children))
    def any_(*children):return dict(operator='any',children=list(children))
    def manual(reason):return dict(operator='manual_check',reason=reason)
    def age(minimum,maximum):return dict(operator='age_range',birth_field='date_of_birth',event_field='application_date',minimum=minimum,maximum=maximum)
    def kr():return dict(operator='contains',field='nationalities',value='KR')
    return {
        'DE_OPP_POL_01':any_(eq('recognised_german_skilled_worker_qualification',True),manual('점수 경로를 별도로 심사')),
        'DE_OPP_POL_02':all_(eq('foreign_qualification_meets_section20a',True),
            any_(dict(operator='in',field='german_cefr',value=['A1','A2','B1','B2','C1','C2']),dict(operator='in',field='english_cefr',value=['B2','C1','C2'])),
            num('gte','section20b_verified_points',6),manual('공식 점수표 항목별 산정 및 생계 증빙 확인')),
        'DE_BLUE_CARD_POL_01':all_(eq('blue_card_qualification_verified',True),num('gte','job_offer_months',6),eq('job_matches_qualification',True),
            any_(all_(eq('salary_reference_year',2026),num('gte','annual_gross_salary_eur',50700)),manual('부족직종·최근 졸업·IT 별도 급여 경로 검토'))),
        'DE_BLUE_CARD_POL_02':all_(eq('designated_shortage_isco_verified',True),num('gte','job_offer_months',6),eq('job_matches_qualification',True),
            eq('salary_reference_year',2026),num('gte','annual_gross_salary_eur',45934.20),eq('ba_employment_approval',True)),
        'DE_BLUE_CARD_POL_03':all_(num('lte','years_since_qualification_at_application',3),num('gte','years_since_qualification_at_application',0),
            eq('salary_reference_year',2026),num('gte','annual_gross_salary_eur',45934.20),eq('ba_employment_approval',True),manual('나머지 §18g 요건 확인')),
        'DE_BLUE_CARD_POL_04':all_(eq('it_isco_133_or_25_verified',True),num('gte','job_offer_months',6),num('gte','qualifying_it_experience_years_in_last_seven',3),
            eq('salary_reference_year',2026),num('gte','annual_gross_salary_eur',45934.20),eq('ba_employment_approval',True)),
        'DE_STUDY_VISA_POL_01':any_(all_(eq('admitted_full_time',True),eq('state_recognised_or_equivalent_institution',True)),manual('§16b 법정 입학준비·조건부 입학 분기 확인')),
        'DE_STUDY_VISA_POL_02':any_(all_(eq('financial_reference_year',2026),num('gte','available_annual_living_funds_eur',11904)),manual('인정 장학금·보증서 등 대체 재정 증빙 확인')),
        'DE_STUDY_VISA_POL_03':any_(eq('language_confirmed_in_admission',True),eq('course_language_requirement_met',True),manual('입학 준비 과정 등 법정 언어 취득 분기')),
        'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_01':any_(eq('higher_education_admission_qualification_met',True),manual('§17(2)의 9개월 내 충족 경로 확인')),
        'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_02':any_(eq('intended_course_language_requirement_met',True),manual('§17(2)의 9개월 내 언어 취득 경로 확인')),
        'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_03':any_(all_(eq('financial_reference_year',2026),num('gte','monthly_living_funds_eur',1091)),manual('예정 체류 기간 전체와 대체 증빙 확인')),
        'DE_WH_POL_02':all_(age(18,34),kr(),eq('accompanying_children',False),eq('accompanying_ineligible_spouse',False),manual('건강·기타 사증 심사')),
        'DE_WH_POL_05':all_(eq('previous_german_working_holiday_visa',False),manual('접수 절차·개인별 추가 서류 확인')),
        'CA_ESWP_POL_01':all_(eq('genuine_canadian_job_offer',True),eq('employer_on_ineligible_list',False),manual('IRPR 200 및 해당 고용주 선행 절차 심사')),
        'CA_ESWP_POL_03':any_(all_(eq('positive_lmia_obtained',True),eq('lmia_letter_and_required_annexes_available',True)),manual('실제 LMIA 면제 경로인지 별도 확인')),
        'CA_ESWP_POL_04':any_(all_(eq('specific_lmia_exemption_verified',True),eq('employer_portal_offer_submitted',True),eq('employer_compliance_fee_paid',True),eq('offer_number_available',True)),manual('Portal·수수료 지정 면제 또는 별도 허가 경로 심사')),
        'CA_IEC_WH_POL_01':all_(kr(),eq('korean_passport_valid_for_stay',True),manual('만18~35세 공개 범위 및 프로필·초청·신청 단계별 생일 경계 확인')),
        'CA_IEC_WH_POL_02':all_(num('lt','iec_actual_work_permit_participations',2),manual('구 협정 참여와 카테고리별 참여 제한·허가기간 확인')),
        'CA_IEC_WH_POL_03':all_(num('gte','initial_settlement_funds_cad',2500),any_(eq('return_ticket_available',True),eq('separate_return_ticket_funds_available',True)),
            num('gte','bank_statement_age_days_at_departure',0),num('lte','bank_statement_age_days_at_departure',7),eq('bank_statement_in_own_name',True)),
        'CA_IEC_WH_POL_04':all_(eq('insurance_covers_entire_planned_stay',True),eq('insurance_medical_care',True),eq('insurance_hospitalisation',True),eq('insurance_repatriation',True),manual('입국적격성 심사')),
        'CA_STUDY_POL_01':all_(eq('dli_admission',True),eq('required_admission_evidence_available',True),manual('입학 확인·퀘벡 CAQ·PAL/TAL 및 법정 면제 확인')),
        'CA_STUDY_POL_02':any_(all_(eq('living_funds_table_applicable_20260901_non_quebec',True),eq('tuition_and_travel_funded_separately',True),
            dict(operator='canada_living_funds',family_field='family_members_including_applicant',funds_field='annual_living_funds_cad'),
            manual('이용 가능 자금·장기 조달계획 확인')),manual('퀘벡·이전 신청일·IRPR 220의 지정 예외 분기 확인')),
        'CA_PGWP_POL_01':any_(all_(eq('pgwp_eligible_dli_and_program',True),
            any_(num('gte','normal_program_length_months',8),all_(eq('quebec_hour_based_program',True),num('gte','normal_program_hours',900))),
            eq('full_time_except_permitted_final_term',True),num('gte','days_since_first_completion_confirmation',0),num('lte','days_since_first_completion_confirmation',180),
            eq('study_permit_valid_during_180_days_after_completion',True)),manual('압축 과정·허용된 중단·기타 지정 예외 경로 확인')),
        'CA_PGWP_POL_06':all_(eq('previous_pgwp_issued',False),eq('only_esl_fsl_or_general_interest_study',False),manual('사립 제휴·비적격 기관·원격수업·장학 귀국 의무 등 지정 제한 확인')),
        'JP-POL-f8393e8d6f1d8da8055cdb11':all_(kr(),eq('residence_country','KR')),
        'JP-POL-8b804fe3bfeb2309fd2b2b60':all_(kr(),eq('residence_country','KR')),
        'JP-POL-f2b3c13e3729ec466981acca':any_(age(18,25),all_(age(18,30),manual('부득이한 사정의 공관 인정 확인'))),
        'JP-POL-6b986824f1c3095d6c1b0cf4':all_(num('gte','previous_japan_working_holiday_visa_issues',0),num('lte','previous_japan_working_holiday_visa_issues',1)),
        'JP-POL-042a6b29505bb2833baa2522':eq('accompanying_children',False),
        'JP-POL-90c2c98c2f9ec0360560d8b1':any_(eq('basic_japanese_for_living',True),eq('willing_to_acquire_basic_japanese',True)),
        'JP-POL-1b1a2b57a695802cf1a9358e':eq('primary_purpose_holiday',True),
        'JP-POL-7402f3813d9aa398419d6397':all_(eq('valid_national_passport',True),any_(eq('return_ticket_available',True),eq('separate_return_ticket_funds_available',True))),
        'JP-POL-54f47ecde2bc322be711ab35':all_(eq('valid_national_passport',True),any_(eq('return_ticket_available',True),eq('separate_return_ticket_funds_available',True))),
    }
