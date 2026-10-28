"""Explicit US programme, sponsor, wage and filing-condition comparisons."""
def rules():
    def eq(field,value):return dict(operator='equals',field=field,value=value)
    def n(op,field,value):return dict(operator=op,field=field,value=value)
    def all_(*children):return dict(operator='all',children=list(children))
    def any_(*children):return dict(operator='any',children=list(children))
    def manual(reason):return dict(operator='manual_check',reason=reason)
    result={
        'US-J1-COLLEGE-POL-001':any_(eq('qualifying_government_or_international_organisation_funding',True),eq('qualifying_government_agreement',True),eq('qualifying_educational_institution_agreement',True),eq('substantial_funding_other_than_personal_or_family',True),eq('qualifying_student_intern_under_6223',True)),
        'US-J1-COLLEGE-POL-003':all_(eq('good_academic_standing',True),manual('해당 학생취업 사유·승인·주당 시간과 방학 예외 확인')),
        'US-J1-COLLEGE-POL-005':eq('sponsor_obtained_required_academic_background_information',True),
        'US-F1-POL-003':all_(eq('required_i20_signatures_complete',True),eq('each_eligible_dependent_has_own_i20',True),eq('i20_program_category_matches_requested_f_or_m',True),manual('미성년 서명·동반가족의 실체 자격 별도 심사')),
        'US-SWT-POL-001':any_(eq('english_verified_by_recognised_test',True),eq('english_verified_by_documented_interview',True)),
        'US-SWT-POL-002':all_(eq('foreign_accredited_in_person_postsecondary',True),eq('full_time_enrolment_at_application',True),eq('actively_pursuing_degree_or_full_course',True)),
        'US-SWT-POL-007':all_(eq('seasonal_or_temporary_job',True),eq('regular_us_citizen_interaction',True),eq('suitable_affordable_housing_transport_considered',True),eq('necessary_housing_transport_assistance_provided',True),
            eq('no_domestic_worker_displacement',True),eq('host_no_layoffs_in_last120days',True),eq('host_no_relevant_strike_or_lockout',True)),
        'US-SWT-POL-008':all_(any_(eq('eligible_vwp_nationality_for_j1_preplacement_exception',True),eq('prearranged_fully_vetted_employment',True)),
            eq('dos_swt_brochure_provided',True),eq('dos_emergency_number_provided',True),eq('sponsor_24_7_contact_provided',True),eq('arrival_job_residence_notification_duties_provided',True),eq('applicable_employment_contract_obligations_provided',True)),
        'US-SWT-POL-009':all_(eq('wage_all_applicable_minima_and_comparable_us_treatment_verified',True),eq('monthly_personal_contact_documented',True),eq('health_safety_welfare_response_arranged',True),manual('VWP 국적자의 사전 고용 없는 입국에 관한 구직·재정 지원 확인')),
        'US-SWT-POL-010':all_(eq('agreed_paid_hours_provided',True),eq('required_overtime_paid',True),eq('host_arrival_changes_earlydeparture_notified',True),eq('host_emergency_notifications_arranged',True)),
        'US-J1-INTERN-POL-010':all_(eq('training_plan_changes_concerns_notified_to_sponsor',True),eq('host_emergency_notifications_arranged',True)),
        'US-WK-01-POL-0004':all_(eq('job_requires_highly_specialised_knowledge',True),eq('job_requires_directly_related_specific_specialty_degree_or_equivalent',True)),
        'US-WK-01-POL-0005':eq('required_lca_filed',True),
        'US-WK-01-POL-0006':all_(eq('employer_i129_petition_approved',True),manual('해당 영사 비자·입국 심사 및 분류별 예외 확인')),
        'US-WK-01-POL-0016':any_(all_(eq('duties_highly_specialised_complex_or_unique',True),eq('duties_usually_require_directly_related_specific_specialty_degree',True)),manual('전문직 판단의 다른 법정 입증 경로 확인')),
        'US-WK-01-POL-0037':any_(eq('comparable_organisations_similar_roles_usually_require_directly_related_degree',True),manual('다른 전문직 입증 경로 확인')),
        'US-WK-01-POL-0020':all_(eq('wage_basis_and_classification_verified',True),dict(operator='gte_field',field='offered_wage_usd_same_basis',other_field='actual_wage_usd_same_basis'),dict(operator='gte_field',field='offered_wage_usd_same_basis',other_field='prevailing_wage_usd_same_basis')),
        'US-WK-01-POL-0028':eq('certified_h1b_lca_available_before_i129',True),
        'US-WK-01-POL-0031':all_(eq('employer_i129_petition_approved',True),eq('i797_approval_notice_available',True),manual('별도 영사 비자·입국 심사 확인')),
        'US-WK-01-POL-0048':all_(eq('petition_within_selection_notice_window',True),eq('requested_start_within_applicable_fiscal_year',True),eq('petition_not_more_than_six_calendar_months_before_start',True)),
        'US-WK-01-POL-0058':any_(eq('license_not_required_for_state_occupation',True),eq('required_state_license_before_approval',True),manual('임시면허·감독하 업무·기술적 발급 장애의 지정 예외 확인')),
        'US-WK-01-POL-0062':all_(eq('employer_i129_petition_approved',True),eq('required_consular_visa_obtained_or_exemption_verified',True),manual('CBP 개별 입국 심사')),
        'US-WK-01-POL-0068':any_(eq('prohibited_early_departure_penalty_imposed',False),manual('주법상 적법한 손해배상 예정액과 위약 벌금 구분')),
        'US-WK-01-POL-0076':any_(n('gte','passport_months_beyond_intended_us_stay',6),eq('applicable_passport_validity_agreement_exception_verified',True)),
        'US-WK-01-POL-0079':all_(eq('approved_eb1_eb2_eb3_immigrant_petition',True),eq('immigrant_visa_number_unavailable',True),n('lte','requested_extension_years',3),manual('해당 6년 초과 연장의 다른 요건·신청 지연 제한 확인')),
        'US-WK-01-POL-0084':any_(eq('adjustment_or_immigrant_visa_application_within_one_year_of_availability',True),manual('불가항력 등 지정 예외 및 다른 연장 경로 심사')),
        'US-WK-01-POL-0086':any_(eq('status_maintenance_evidence_submitted',True),manual('지연 제출 재량·해외 영사 처리 등 적용 분기 확인')),
        'US-WK-01-POL-0096':any_(eq('status_maintenance_evidence_submitted',True),manual('지연 제출 재량·해외 영사 처리 등 적용 분기 확인')),
        'US-WK-01-POL-0097':any_(eq('amended_or_new_petition_and_required_lca_before_material_change',True),manual('동일 고용지역·단기 배치 등 지정 예외 확인')),
        'US-WK-01-POL-ADD-005':all_(eq('lca_no_adverse_effect_attestation',True),eq('comparable_us_working_conditions_standards_applied',True),eq('working_conditions_obligation_period_verified',True)),
        'US-WK-01-POL-ADD-006':all_(eq('no_relevant_strike_lockout_at_lca_filing',True),any_(eq('subsequent_relevant_strike_lockout',False),all_(n('lte','days_to_eta_written_strike_notification',3),eq('required_strike_placement_petition_restrictions_observed',True)))),
        'US-WK-01-POL-ADD-007':all_(eq('lca_notice_correct_representative_or_employee_audience',True),eq('lca_notice_timing_verified',True),eq('applicable_posting_electronic_or_direct_delivery_requirements_met',True),eq('worker_certified_lca_copy_and_records_provided',True)),
        'US-WK-01-POL-ADD-008':any_(eq('worker_resigned_voluntarily',True),all_(eq('employer_dismissed_before_authorised_end',True),eq('reasonable_return_transport_costs_provided',True)),manual('실제 종료 사유·의무 적용 범위 확인')),
        'US-WK-01-POL-ADD-009':all_(eq('h1b_portability_eligibility_verified',True),eq('new_employer_nonfrivolous_timely_i129_filed',True),eq('work_started_no_earlier_than_later_of_filing_and_requested_start',True),manual('무허가 취업 이력·청원 결과와 종료 사유 확인')),
        'US-WK-01-POL-ADD-010':all_(n('gte','days_since_employment_ended',0),n('lte','days_since_employment_ended',60),eq('within_remaining_authorised_validity',True),manual('해당 유예기간의 재량·개별 제한 및 실제 취업 허용 별도 확인')),
        'US-WK-01-POL-ADD-011':any_(eq('cap_subject_new_employment_registration_and_cap_compliance',True),manual('과거 cap 산입 등 지정 예외 심사')),
        'US-WK-01-POL-ADD-012':all_(eq('qualifying_cap_exempt_employment_continues',True),eq('new_employer_nonfrivolous_timely_i129_filed',True),eq('concurrent_work_start_timing_verified',True),manual('동시취업·portability의 다른 요건 확인')),
        'US-WK-01-POL-AGL-003':all_(eq('lca_suspended_or_invalidated',True),eq('employer_certified_continued_lca_compliance_for_existing_authorised_workers',True),manual('기존 승인 청원에 대한 해당 보호 범위·다른 취소 사유 확인')),
        'US-WK-01-POL-EMP-001':all_(eq('full_time_petition',True),eq('qualifying_nonproductive_period_after_employment_start',True),eq('required_full_time_wages_paid',True),manual('개인 사유 자발적 비근무 등 지정 예외 구분')),
        'US-WK-01-POL-EMP-002':all_(eq('part_time_petition',True),eq('qualifying_nonproductive_period_after_employment_start',True),eq('petition_hours_and_rate_wages_paid',True),manual('비생산 기간의 적용·예외 확인')),
        'US-WK-01-POL-EMP-004':eq('benefit_offers_and_eligibility_same_basis_as_us_workers',True),
        'US-WK-01-POL-MOD-003':eq('lawful_uscis_site_visit_cooperation',True),
        'US-WK-01-POL-MOD-005':all_(eq('third_party_integrated_role_is_specialty_occupation',True),eq('third_party_actual_duty_requirements_verified',True)),
        'US-WK-01-POL-MOD-007':all_(n('gte','work_time_directly_furthering_qualifying_institution_percent',50),eq('qualifying_institution_and_core_activity_link_verified',True),manual('cap 면제의 다른 법정 요건·실제 근무 관계 확인')),
        'US-WK-01-POL-REG-002':eq('offered_wage_meets_claimed_oews_level',True),
        'US-WK-01-POL-REG-004':eq('registration_material_misrepresentation',False),
        'US-WK-01-POL-WPR-002':eq('prohibited_whistleblower_retaliation',False),
    }
    host_visit=any_(eq('successful_previous_host_programme_participation',True),eq('host_academic_or_government_institution',True),all_(n('gte','host_employee_count',25),n('gte','host_annual_revenue_usd',3000000)),eq('required_sponsor_site_visit_completed',True))
    for pid in ('US-J1-INTERN-POL-005','US-J1-TRAINEE-POL-008'):result[pid]=host_visit
    host_details=all_(eq('host_ein_collected',True),eq('host_identity_contact_details_verified',True),any_(eq('workers_compensation_policy_evidence',True),eq('lawful_state_workers_compensation_exemption_evidence',True)))
    for pid in ('US-J1-INTERN-POL-006','US-J1-TRAINEE-POL-009'):result[pid]=host_details
    evaluations=all_(n('gt','programme_duration_months',0),eq('end_evaluation_before_end_signed_by_participant_and_supervisor',True),any_(n('lte','programme_duration_months',6),eq('midpoint_evaluation_signed_by_participant_and_supervisor',True)),n('gte','sponsor_evaluation_retention_years_after_end',3))
    for pid in ('US-J1-INTERN-POL-007','US-J1-INTERN-POL-008','US-J1-TRAINEE-POL-010','US-J1-TRAINEE-POL-011'):result[pid]=evaluations
    return result
