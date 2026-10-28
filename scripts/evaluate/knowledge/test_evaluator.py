import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts/ingest/common/knowledge'))
from app.rules.evaluator import evaluate,evaluate_requirement,PASS,FAIL,UNKNOWN
from structured_support_rules import rules


class EvaluatorTests(unittest.TestCase):
    def test_missing_is_not_failure(self):
        self.assertEqual(evaluate(dict(operator='equals',field='x',value=True),{}),UNKNOWN)

    def test_wrong_types_never_coerce(self):
        for v in (1,'true',[],{}):
            self.assertEqual(evaluate(dict(operator='equals',field='x',value=True),{'x':v}),UNKNOWN)

    def test_and_or_three_states(self):
        yes=dict(operator='equals',field='yes',value=True)
        no=dict(operator='equals',field='no',value=True)
        unknown=dict(operator='manual_check')
        p={'yes':True,'no':False}
        for op,children,expected in [('all',[yes,unknown],UNKNOWN),('all',[no,unknown],FAIL),('any',[yes,unknown],PASS),('any',[no,unknown],UNKNOWN),('all',[],UNKNOWN)]:
            self.assertEqual(evaluate(dict(operator=op,children=children),p),expected)

    def test_nationalities_absent_empty_invalid(self):
        for op in ('contains','not_contains'):
            for value in (None,[],'KR',[1]):
                self.assertEqual(evaluate(dict(operator=op,field='nationalities',value='KR'),{'nationalities':value}),UNKNOWN)

    def test_fulbright_dual_national_excluded_condition(self):
        expression=dict(operator='all',children=rules()['US_FULBRIGHT_GRADUATE_2027'])
        self.assertEqual(evaluate(expression,dict(nationalities=['KR','US'],us_permanent_resident=False)),FAIL)
        self.assertEqual(evaluate(expression,dict(nationalities=['KR'],us_permanent_resident=False)),UNKNOWN)
        p=dict(nationalities=['KR'],us_permanent_resident=False,in_us_at_application=False,us_five_consecutive_years_within_last_six=False,
            same_level_degree_already_held=False,same_level_semesters_enrolled=0,professional_license_degree=False,professional_dual_degree=False,
            field_group='humanities',can_reside_in_korea_three_months_before_award=True,can_attend_required_orientations=True,
            us_government_scholarship_last_five_years=False)
        self.assertEqual(evaluate(expression,p),PASS)

    def test_rtp_coursework_is_not_research(self):
        self.assertEqual(evaluate(dict(operator='all',children=rules()['AU_RTP']),dict(degree_type='coursework_masters',rtp_eligible_university=True)),FAIL)

    def test_fu_admission_or_enrolment(self):
        p=dict(fu_berlin_accepted_and_starting=True,within_standard_degree_period_entire_funding_year=True,degree_type='masters',
            charite_student=False,fu_berlin_main_enrolment=True,seeking_fu_berlin_degree=True,other_merit_support_eur_month=0)
        expr=dict(operator='all',children=rules()['DE_FU_DEUTSCHLANDSTIPENDIUM'])
        self.assertEqual(evaluate(expr,p),PASS)
        self.assertEqual(evaluate(expr,{**p,'degree_type':'research_doctorate'}),FAIL)

    def test_necessary_conditions_do_not_become_final_pass(self):
        children=rules()['CA_WATERLOO_IMAE']+[dict(operator='manual_check')]
        self.assertEqual(evaluate(dict(operator='all',children=children),dict(waterloo_international_masters_student=True)),UNKNOWN)

    def test_expired_condition_not_reused(self):
        result=evaluate_requirement(dict(effective_until='2026-10-28'),{},'2026-10-29')
        self.assertEqual(result['status'],UNKNOWN)
        self.assertFalse(result['final_eligibility'])

    def test_numeric_invalid_values(self):
        for value in (True,'30',float('nan'),float('inf')):
            self.assertEqual(evaluate(dict(operator='lte',field='age',value=35),{'age':value}),UNKNOWN)

    def test_stale_source_and_actual_release_rules(self):
        import json
        data=json.loads((ROOT/'data/processed/knowledge/20261028/knowledge_release.json').read_text(encoding='utf-8'))
        rows=[r for r in data['requirements'] if r['judgeability']=='conditional']
        self.assertGreaterEqual(len(rows),209)
        for row in rows:
            self.assertEqual(evaluate_requirement(row,{},'2026-10-28')['status'],UNKNOWN)
            self.assertEqual(evaluate_requirement(row,{},'2026-10-29')['status'],UNKNOWN)

    def test_event_dates_and_passport_age_boundaries(self):
        from structured_visa_rules import rules as visas
        expression=visas()['AU_417_FIRST_POL_02']
        p=dict(date_of_birth='1990-10-29',application_date='2026-10-28',passport_country='KR')
        self.assertEqual(evaluate(expression,p),PASS)
        self.assertEqual(evaluate(expression,{**p,'application_date':'2026-10-29'}),FAIL)
        self.assertEqual(evaluate(expression,{**p,'passport_country':'unverified'}),UNKNOWN)
        self.assertEqual(evaluate(expression,{**p,'application_date':'2026-06-30'}),UNKNOWN)
        # Invitation age, not today's or EOI age.
        self.assertEqual(evaluate(visas()['AU_190_POL_05'],dict(date_of_birth='1981-10-29',invitation_date='2026-10-28')),PASS)

    def test_exceptions_do_not_become_hard_rejections(self):
        from structured_visa_rules import rules as visas
        self.assertEqual(evaluate(visas()['AU_186_TRT_POL_06'],dict(date_of_birth='1970-01-01',application_date='2026-10-28')),UNKNOWN)
        self.assertEqual(evaluate(visas()['AU_407_POL_03'],dict(date_of_birth='2010-01-01',application_date='2026-10-28')),UNKNOWN)
        self.assertEqual(evaluate(rules()['KR_SUPPORT_KMOVE_SCHOOL'][1],dict(age_at_training_start=36)),UNKNOWN)

    def test_well_hours_boundary(self):
        rule=rules()['KR_SUPPORT_WELL'][2]
        self.assertEqual(evaluate(rule,dict(unemployed=False,weekly_work_hours=29)),PASS)
        self.assertEqual(evaluate(rule,dict(unemployed=False,weekly_work_hours=30)),FAIL)

    def test_target_isolation_and_closed_is_not_ineligibility(self):
        from app.rules.evaluator import evaluate_target
        import json
        data=json.loads((ROOT/'data/processed/knowledge/20261028/knowledge_release.json').read_text(encoding='utf-8'))
        group=next(g for g in data['rule_sets'] if g['target_id']=='DE_FU_DEUTSCHLANDSTIPENDIUM')
        result=evaluate_target(group,[],{},'2026-10-28')
        self.assertEqual(result['overall_status'],UNKNOWN)
        self.assertEqual(result['application_availability'],'CLOSED')
        self.assertFalse(result['final_eligibility'])
        self.assertTrue(all(r['status']==UNKNOWN for r in result['condition_results']))

    def test_japan_school_and_application_do_not_leak(self):
        expr=dict(operator='japan_document_matrix',document_id='ROW1',application_type='certificate_of_eligibility',school_category='university',
            school_classification='university',source_record={'requirement_status':'required'})
        profile=dict(application_type='certificate_of_eligibility',school_category='university',school_classification='university',provided_document_ids=['ROW1'])
        self.assertEqual(evaluate(expr,profile),PASS)
        self.assertEqual(evaluate(expr,{**profile,'provided_document_ids':[]}),FAIL)
        self.assertEqual(evaluate(expr,{**profile,'school_category':'vocational_school'}),UNKNOWN)
        self.assertEqual(evaluate(expr,{**profile,'application_type':'change'}),UNKNOWN)
        self.assertEqual(evaluate({**expr,'source_record':{'requirement_status':'conditional'}},profile),UNKNOWN)
        self.assertEqual(evaluate({**expr,'source_record':{'requirement_status':'not_applicable'}},profile),UNKNOWN)

    def test_japan_employer_category_and_invalid_input(self):
        expr=dict(operator='japan_document_matrix',document_id='ROW1',application_type='coe',source_record={'category_requirements':{'3':{'status':'required'},'4':{'status':'conditional'}}})
        self.assertEqual(evaluate(expr,dict(application_type='coe',employer_category='3',provided_document_ids=[])),FAIL)
        self.assertEqual(evaluate(expr,dict(application_type='coe',employer_category='4',provided_document_ids=[])),UNKNOWN)
        self.assertEqual(evaluate(expr,dict(application_type='coe',employer_category=3,provided_document_ids=[])),UNKNOWN)

    def test_canada_funds_family_size_and_boundary(self):
        expr=dict(operator='canada_living_funds',family_field='n',funds_field='funds')
        self.assertEqual(evaluate(expr,{'n':1,'funds':23448}),PASS)
        self.assertEqual(evaluate(expr,{'n':1,'funds':23447}),FAIL)
        self.assertEqual(evaluate(expr,{'n':8,'funds':68372}),PASS)
        for n in (0,True,'2',None):self.assertEqual(evaluate(expr,{'n':n,'funds':999999}),UNKNOWN)

    def test_de_blue_card_exact_three_years(self):
        from structured_country_rules import rules as country
        expr=country()['DE_BLUE_CARD_POL_03']
        p=dict(years_since_qualification_at_application=3,salary_reference_year=2026,annual_gross_salary_eur=45934.2,ba_employment_approval=True)
        # Remaining section18g requirements need review; three years is not rejected.
        self.assertEqual(evaluate(expr,p),UNKNOWN)
        self.assertEqual(evaluate(expr,{**p,'years_since_qualification_at_application':3.01}),FAIL)

    def test_us_intern_and_trainee_alternatives(self):
        from structured_us_rules import rules as us
        expr=us()['US-J1-INTERN-POL-001']
        self.assertEqual(evaluate(expr,dict(us_citizen=False,foreign_postsecondary_degree_or_certificate_institution=True,full_time_enrolled_outside_us=False,months_from_graduation_to_program_start=12)),PASS)
        self.assertEqual(evaluate(expr,dict(us_citizen=False,foreign_postsecondary_degree_or_certificate_institution=True,full_time_enrolled_outside_us=False,months_from_graduation_to_program_start=12.01)),FAIL)
        self.assertEqual(evaluate(us()['US-J1-TRAINEE-POL-001'],dict(us_citizen=False,related_work_experience_years_outside_us=5)),PASS)

    def test_us_clerical_twenty_percent(self):
        from structured_us_rules import rules as us
        for prefix in ('US-J1-INTERN','US-J1-TRAINEE'):
            self.assertEqual(evaluate(us()[prefix+'-POL-003'],dict(clerical_work_percent=20)),PASS)
            self.assertEqual(evaluate(us()[prefix+'-POL-003'],dict(clerical_work_percent=20.001)),FAIL)

    def test_au_invitation_points_not_only_sixty_five(self):
        from australia_common_rules import compile_rule
        rule=compile_rule(dict(country='australia',topic='points',policy_id='AU_190_POL_06'),'')
        p=dict(verified_points=65,invitation_required_points=85,point_claims_supported_by_evidence=True)
        self.assertEqual(evaluate(rule,p),FAIL)
        self.assertEqual(evaluate(rule,{**p,'verified_points':85}),PASS)
        self.assertEqual(evaluate(rule,{**p,'invitation_required_points':None}),UNKNOWN)

    def test_au_debt_repayment_is_alternative_to_full_payment(self):
        from australia_common_rules import compile_rule
        rule=compile_rule(dict(country='australia',topic='government_debt',policy_id='X'),'PIC 4004')
        self.assertEqual(evaluate(rule,dict(pic4004_subject_scope_verified=True,no_outstanding_commonwealth_debt=False,appropriate_debt_repayment_arrangements=True)),PASS)
        self.assertEqual(evaluate(rule,dict(no_outstanding_commonwealth_debt=True)),UNKNOWN)

    def test_au_uk_work_exemption_and_taiwan_passport_scope(self):
        from australia_common_rules import compile_rule
        rule=compile_rule(dict(country='australia',topic='specified_work',policy_id='AU_417_SECOND_POL_04'),'')
        self.assertEqual(evaluate(rule,dict(passport_country='GB',application_date='2024-07-01')),PASS)
        self.assertEqual(evaluate(rule,dict(passport_country='GB',application_date='2024-06-30')),UNKNOWN)
        passport=compile_rule(dict(country='australia',topic='passport',policy_id='AU_417_FIRST_POL_01'),'')
        p=dict(passport_country='KR',passport_valid=True,citizenship_or_jurisdiction_status_matches_eligible_passport_verified=True,nationalities=['KR','TW'])
        self.assertEqual(evaluate(passport,p),PASS)
        self.assertEqual(evaluate(passport,{**p,'passport_country':'TW'}),UNKNOWN)


if __name__=='__main__':unittest.main()
