"""Country tables, dated English-score branches and student application branches."""
def rules():
    def eq(f,v):return dict(operator='equals',field=f,value=v)
    def n(op,f,v):return dict(operator=op,field=f,value=v)
    def member(f,v):return dict(operator='in',field=f,value=v)
    def all_(*c):return dict(operator='all',children=list(c))
    def any_(*c):return dict(operator='any',children=list(c))
    def review(reason):return dict(operator='manual_check',reason=reason)
    def window(years,reference,before=False):return dict(operator='within_calendar_years',event_field='test_date',reference_field=reference,years=years,strictly_before_reference=before)
    def scores(table):return dict(operator='score_matrix',test_field='english_test',scores_field='english_scores',table=table)
    tertiary=eq('tertiary_qualification',True)
    undergraduate=n('gte','successfully_completed_undergraduate_university_years',2)
    standard=any_(tertiary,undergraduate)
    education={code:standard for code in ['AR','CN','GR','HU','ID','LU','MY','MN','PE','PL','PT','SM','SK','SI','TR','UY','VN']}
    education.update({
        'AT':any_(tertiary,n('gte','successfully_completed_higher_education_years',2)),
        'BR':n('gte','successfully_completed_postsecondary_years',2),
        'CL':any_(tertiary,eq('third_undergraduate_year_completed_or_approved',True)),
        'CZ':n('gte','successfully_completed_tertiary_education_years',2),
        'EC':any_(tertiary,n('gte','successfully_completed_higher_education_years',2)),
        'IN':n('gte','successfully_completed_postsecondary_years',2),
        'IL':all_(eq('secondary_school_qualification',True),any_(eq('military_service_completed',True),eq('legal_military_exemption',True))),
        'PG':undergraduate,'PH':any_(tertiary,n('gte','successfully_completed_undergraduate_or_postsecondary_years',2)),
        'SG':any_(eq('qualification_tertiary_level_in_singapore',True),n('gte','completed_full_time_equivalent_tertiary_years',2)),
        'ES':n('gte','successfully_completed_higher_education_years',2),
        'CH':n('gte','completed_study_years_after_compulsory_schooling',2),'TH':tertiary,'US':eq('secondary_school_qualification',True),
    })
    english_passport=all_(member('passport_country',['CA','NZ','IE','GB','US']),eq('valid_passport_and_nationality_for_english_exemption',True))
    current482={'CELPIP General':dict(listening=5,reading=5,writing=5,speaking=5),'IELTS Academic':dict(listening=5,reading=5,writing=5,speaking=5),'IELTS General Training':dict(listening=5,reading=5,writing=5,speaking=5),
        'LANGUAGECERT Academic':dict(listening=41,reading=44,writing=45,speaking=54),'MET':dict(listening=49,reading=47,writing=45,speaking=38),
        'OET':dict(listening=220,reading=240,writing=200,speaking=270),'PTE Academic':dict(listening=33,reading=36,writing=29,speaking=24),'TOEFL iBT':dict(listening=8,reading=8,writing=9,speaking=14)}
    legacy482={'IELTS Academic':dict(overall=5,listening=5,reading=5,writing=5,speaking=5),'IELTS General Training':dict(overall=5,listening=5,reading=5,writing=5,speaking=5),'OET':dict(listening='B',reading='B',writing='B',speaking='B'),
        'TOEFL iBT':dict(overall=35,listening=4,reading=4,writing=14,speaking=14),'PTE Academic':dict(overall=36,listening=36,reading=36,writing=36,speaking=36),'CAE':dict(overall=154,listening=154,reading=154,writing=154,speaking=154)}
    new482=all_(dict(operator='date_gte',field='test_date',value='2025-09-13'),window(3,'english_evidence_provided_date'),scores(current482),eq('section6_single_sitting_or_permitted_component_retake_verified',True))
    old482=all_(dict(operator='date_lt',field='test_date',value='2025-09-13'),window(3,'application_date',True),scores(legacy482),eq('single_test_sitting',True))
    english482=any_(english_passport,all_(n('gte','full_time_secondary_higher_english_years',5),eq('statutory_full_time_subject_hours_definition_met',True)),eq('designated_diplomatic_consular_taiwan_sponsor_role',True),eq('required_professional_authorisation_obtained_with_equivalent_english',True),all_(eq('existing_overseas_business_employee_related_company_nomination',True),n('gte','annual_earnings_aud',96400)),new482,old482)
    functional_new={k:dict(overall=v) for k,v in [('CELPIP General',5),('IELTS Academic',4.5),('IELTS General Training',4.5),('LANGUAGECERT Academic',38),('MET',38),('OET',1020),('PTE Academic',24),('TOEFL iBT',26)]}
    functional_legacy={k:dict(overall=v) for k,v in [('IELTS Academic',4.5),('IELTS General Training',4.5),('TOEFL iBT',32),('PTE Academic',30),('CAE',147)]}
    functional=any_(english_passport,eq('all_primary_and_three_secondary_years_taught_in_english',True),eq('five_secondary_years_taught_in_english',True),eq('qualifying_australian_english_taught_degree_diploma_one_year_equivalent',True),
        eq('reg517c_two_year_full_time_english_qualification',True),eq('reg517d_minister_interview_satisfied',True),
        all_(eq('israeli_national_and_passport',True),n('gte','english_bagrut_study_units',3)),
        all_(dict(operator='date_gte',field='test_date',value='2025-08-07'),eq('test_within_twelve_months_before_or_on_after_application_under_lin25014',True),scores(functional_new)),
        all_(dict(operator='date_lt',field='test_date',value='2025-08-07'),window(1,'application_date',True),scores(functional_legacy)))
    new500base={'CELPIP General':[7,6,5],'IELTS Academic':[6,5.5,5],'IELTS General Training':[6,5.5,5],'LANGUAGECERT Academic':[61,54,46],'MET':[53,49,44],'OET':[1210,1090,1020],'PTE Academic':[47,39,31],'TOEFL iBT':[67,51,37]}
    old500base={'CAE':[169,162,154],'IELTS Academic':[6,5.5,5],'IELTS General Training':[6,5.5,5],'PTE Academic':[50,42,36],'TOEFL iBT':[64,46,35]}
    tracks={}
    for i,track in enumerate(['standard','ten_week_or_foundation_eligible_pathway','twenty_week_elicos']):
        new={k:dict(overall=v[i]) for k,v in new500base.items()};old={k:dict(overall=v[i]) for k,v in old500base.items()}
        if i==0:new['C1 Advanced']=dict(overall=161)
        old['OET']=dict(listening='B',reading='B',writing='B',speaking='B')
        tracks[track]=all_(eq('score_track_qualifying_course_conditions_verified',True),any_(all_(dict(operator='date_gte',field='test_date',value='2025-08-07'),scores(new)),all_(dict(operator='date_lt',field='test_date',value='2025-08-07'),scores(old))))
    student_test=all_(dict(operator='switch',field='student_english_score_track',cases=tracks),eq('test_format_and_delivery_accepted_for_applicable_instrument',True),
        any_(all_(eq('english_evidence_submitted_at_application',True),window(2,'application_date',True)),all_(eq('english_evidence_submitted_at_application',False),window(2,'decision_date',True))))
    student_english=any_(english_passport,eq('sole_course_matches_section7_course_exemption',True),eq('foreign_affairs_defence_secondary_exchange_english_exemption',True),eq('australian_english_year12_or_certiv_substantial_component_within_two_years_verified',True),eq('five_years_english_study_in_seven_designated_countries_verified',True),student_test)
    result={
        'AU_191_REGIONAL_PROVISIONAL_POL_02':all_(n('gte','ato_assessment_income_years_out_of_eligible_five_years',3),eq('eligible_visa_conditions_complied_during_australian_stay',True)),
        'AU_462_FIRST_POL_04':dict(operator='switch',field='passport_country',cases=education),
        'AU_462_FIRST_POL_05':all_(functional,review('시험 형식·4영역·증거 허용·462 신청의 실제 요건 충족 시점 및 사후시험 경로는 별도 검토')),
        'AU_482_CORE_POL_13':english482,
        'AU_482_SPECIALIST_POL_12':all_(any_(eq('prohibited_sponsorship_benefit_conduct_in_last_three_years',False),review('482.213의 장관 합리적 무시 분기')),english482),
        'AU_500_POL_04':student_english,
        'AU_500_POL_01':any_(eq('school_student',False),eq('secondary_school_exchange_participant',True),all_(dict(operator='age_range',birth_field='date_of_birth',event_field='application_date',minimum=6,maximum=None),
            dict(operator='switch',field='school_year',cases={str(y):dict(operator='age_range',birth_field='date_of_birth',event_field='school_year_start_date',minimum=0,maximum=y+7) for y in [9,10,11,12]}))),
        'AU_500_POL_06':any_(eq('in_australia',False),all_(eq('holds_substantive_visa',True),eq('current_visa_is_lin26102_excluded_class_verified',False),review('현재500 보유자 별도 재신청 예외·기타 유효 신청 조건 확인')),review('1222(4A)/(4B)의 마지막 비자·ART 통지·28일·반복 발급 금지 조건 검토')),
        'AU_500_POL_07':any_(eq('in_australia',False),all_(eq('previous500_primary_applicant',True),any_(eq('defence_foreign_affairs_or_school_student',True),eq('enrolled_phd_at_application',True),
            all_(eq('enrolled_on_provider_default_date',True),n('lte','months_since_provider_default_at_application',12),eq('same_default_already_used_for_reapplication',False)),
            all_(eq('qualifying_main_course_started_not_completed',True),n('lte','months_after_coe_end_to_complete',12),eq('same_provider_permitted_alternative_course_conditions_verified',True)),
            all_(eq('previous_compliant_main_course_completed',True),n('lte','additional_courses',1),eq('aqf_and_higher_education_progression_conditions_verified',True))))),
        'AU_500_POL_08':all_(any_(eq('primary_holder_defence_foreign_affairs_or_designated_pacific_5a_nationality',True),eq('exact_grandfathered_same_primary_holder_family_path_verified',True),eq('all_registered_course_costs_fully_foreign_government_funded',True),eq('family_of_phd_student',True),eq('sections22_23_default_completion_family_conditions_verified',True)),eq('combined_same_time_place_application_or_designated_exception_verified',True),review('각 신청자의 소재지·기존 비자·가족 자격 조건 별도 검토')),
    }
    for pid,cutoff in [('AU_500_POL_06','2026-10-02'),('AU_500_POL_07','2026-10-02'),('AU_500_POL_08','2026-10-02'),('AU_500_POL_04','2025-08-07'),('AU_482_CORE_POL_13','2025-09-13'),('AU_482_SPECIALIST_POL_12','2025-09-13')]:
        result[pid]=dict(operator='dated_rule',field='application_date',not_before=cutoff,condition=result[pid])
    school_cases=result['AU_500_POL_01']['children'][2]['children'][1]['cases']
    for year in range(0,9):school_cases[str(year)]=dict(operator='age_range',birth_field='date_of_birth',event_field='application_date',minimum=6,maximum=None)
    return result
