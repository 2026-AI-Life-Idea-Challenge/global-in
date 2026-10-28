"""Explicitly transcribed necessary conditions; each group retains manual review."""

def rules():
    def eq(field,value):return dict(operator='equals',field=field,value=value)
    def member(field,values):return dict(operator='in',field=field,value=values)
    result = {
        'AU_RTP':[
            member('degree_type',['research_masters','research_doctorate']),
            eq('rtp_eligible_university',True)],
        'DE_FU_DEUTSCHLANDSTIPENDIUM':[
            dict(operator='any',children=[eq('fu_berlin_enrolled',True),eq('fu_berlin_accepted_and_starting',True)]),
            eq('within_standard_degree_period_entire_funding_year',True),
            member('degree_type',['bachelors','masters','state_exam']),
            eq('charite_student',False),eq('fu_berlin_main_enrolment',True),eq('seeking_fu_berlin_degree',True),
            dict(operator='any',children=[dict(operator='lte',field='other_merit_support_eur_month',value=30),dict(operator='manual_check',reason='공식 중복 장학 예외 목록 확인')])],
        'US_FULBRIGHT_GRADUATE_2027':[
            dict(operator='contains',field='nationalities',value='KR'),
            dict(operator='not_contains',field='nationalities',value='US'),
            eq('us_permanent_resident',False),eq('in_us_at_application',False),
            eq('us_five_consecutive_years_within_last_six',False),
            eq('same_level_degree_already_held',False),dict(operator='lte',field='same_level_semesters_enrolled',value=2),
            eq('professional_license_degree',False),eq('professional_dual_degree',False),
            member('field_group',['humanities','social_sciences','arts']),
            eq('can_reside_in_korea_three_months_before_award',True),eq('can_attend_required_orientations',True),
            dict(operator='any',children=[eq('us_government_scholarship_last_five_years',False),eq('only_prior_us_award_is_west_or_ugrad',True)])],
        'CA_WATERLOO_IMAE':[
            eq('waterloo_international_masters_student',True)],
    }
    # Upper-age exceptions are unresolved branches, never hard failures.
    def youth(event):
        return dict(operator='any',children=[dict(operator='lte',field=event,value=34),dict(operator='manual_check',reason='군복무 연장 또는 해당 사업의 초과연령 예외 심사')])
    result['KR_SUPPORT_KMOVE_SCHOOL']=[dict(operator='contains',field='nationalities',value='KR'),youth('age_at_training_start'),
        dict(operator='any',children=[eq('final_school_graduated',True),eq('final_year_graduation_possible_after_training',True)])]
    result['KR_SUPPORT_SETTLEMENT']=[youth('age_at_employment_start'),eq('lawful_employment_visa',True),
        dict(operator='gte',field='annual_salary_krw',value=17000000),dict(operator='gte',field='employment_contract_months',value=12)]
    result['KR_SUPPORT_WELL']=[dict(operator='gte',field='age_at_participation_reference_date',value=15),youth('age_at_participation_reference_date'),
        dict(operator='any',children=[eq('unemployed',True),dict(operator='all',children=[dict(operator='gte',field='weekly_work_hours',value=0),dict(operator='lt',field='weekly_work_hours',value=30)])]),
        eq('participating_in_youth_work_experience_at_pretraining_start',False),eq('prior_public_overseas_internship',False),
        eq('hrdk_employment_or_settlement_within_twelve_months',False),eq('hrdk_dropout_or_unemployed_completion_within_twelve_months',False)]
    result['KR_US_WEST_LANGUAGE_LOAN']=[eq('graduated_at_kosaf_application',False)]
    return result
