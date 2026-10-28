"""Source-boundary and trusted-evidence regression tests; all decisions are fixtures."""
import sys,json,unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts/ingest/common/knowledge'))
from app.rules.evaluator import evaluate,evaluate_requirement,PASS,FAIL,UNKNOWN
import app.rules.evaluator as loaded_engine
assert Path(loaded_engine.__file__).resolve().is_relative_to(ROOT),'Tests must use the packaged/workspace engine under test'
from app.rules.reviews import VerifiedReviewDecision,facts_hash
from structured_us_obligations import rules as obligations
from australia_final_rules import rules as australia
from classified_source_rules import rules as classified
from review_branch_compiler import compile_branches

class ReleaseRuleTests(unittest.TestCase):
    def fixture(self):
        p={'case_id':'test-1','age':25}
        r=dict(requirement_id='R1',target={'target_type':'PROGRAM','target_id':'AU:subclass_500'},source_document_ids=['D1'],verified_at='2026-10-28',
            expression=dict(operator='official_assessment',criterion_sha256='a'*64,authority_id='TEST_AUTHORITY',source_document_ids=['D1'],review_questions=['test criterion']))
        record=VerifiedReviewDecision('R1','PROGRAM','AU:subclass_500','a'*64,facts_hash(p),'TEST_AUTHORITY',PASS,'b'*64,'authenticated-test-reviewer',date(2026,10,28),date(2026,10,28))
        return r,p,record

    def test_profile_cannot_self_approve(self):
        r,p,record=self.fixture()
        self.assertEqual(evaluate_requirement(r,{**p,'officially_approved':True},'2026-10-28')['status'],UNKNOWN)
        self.assertEqual(evaluate_requirement(r,p,'2026-10-28',[record.__dict__])['status'],UNKNOWN)

    def test_valid_record_and_changed_facts(self):
        r,p,record=self.fixture();result=evaluate_requirement(r,p,'2026-10-28',[record])
        self.assertEqual(result['status'],PASS);self.assertFalse(result['final_eligibility'])
        self.assertEqual(evaluate_requirement(r,{**p,'age':26},'2026-10-28',[record])['status'],UNKNOWN)

    def test_wrong_program_authority_revision_or_id(self):
        r,p,record=self.fixture()
        for changes in [dict(target_id='AU:subclass_417_first'),dict(authority_id='OTHER'),dict(criterion_sha256='c'*64),dict(requirement_id='R2')]:
            self.assertEqual(evaluate_requirement(r,p,'2026-10-28',[replace(record,**changes)])['status'],UNKNOWN)

    def test_expiry_future_and_conflicting_outcomes(self):
        r,p,record=self.fixture()
        for day in (date(2026,10,27),date(2026,10,29)):
            self.assertEqual(evaluate_requirement(r,p,'2026-10-28',[replace(record,verified_at=day,valid_until=day)])['status'],UNKNOWN)
        self.assertEqual(evaluate_requirement(r,p,'2026-10-28',[record,replace(record,outcome=FAIL)])['status'],UNKNOWN)

    def test_malformed_record_rejected(self):
        _,_,record=self.fixture()
        for changes in [dict(evidence_sha256='invalid'),dict(verified_by_principal=''),dict(verified_at='2026-10-28'),dict(outcome='pending')]:
            with self.assertRaises(ValueError):replace(record,**changes)

    def test_nested_review_resolves_without_irrelevant_questions(self):
        document=dict(content_sha256='a'*64,text='test source criterion',document_id='D1',source_references=[{'source_url':'https://example.gov/criterion'}])
        expr=compile_branches(dict(operator='any',children=[dict(operator='equals',field='ordinary_route',value=True),dict(operator='manual_check',reason='actual official exception')]),'R1',{'target_type':'PROGRAM','target_id':'AU:subclass_500'},document)
        r,p,record=self.fixture();r['expression']=expr
        result=evaluate_requirement(r,{**p,'ordinary_route':True},'2026-10-28')
        self.assertEqual(result['status'],PASS);self.assertEqual(result['review_requests'],[])
        profile={**p,'ordinary_route':False};branch=expr['children'][1]
        record=replace(record,requirement_id=branch['review_id'],criterion_sha256=branch['criterion_sha256'],authority_id=branch['authority_id'],case_profile_sha256=facts_hash(profile))
        self.assertEqual(len(evaluate_requirement(r,profile,'2026-10-28')['review_requests']),1)
        self.assertEqual(evaluate_requirement(r,profile,'2026-10-28',[record])['status'],PASS)

    def test_host_visit_requires_or_of_size_thresholds(self):
        expr=obligations()['US-J1-INTERN-POL-005']
        p=dict(successful_previous_host_programme_participation=False,host_academic_or_government_institution=False,host_employee_count=25,host_annual_revenue_usd=3000000,required_sponsor_site_visit_completed=False)
        self.assertEqual(evaluate(expr,p),PASS)
        self.assertEqual(evaluate(expr,{**p,'host_employee_count':24}),FAIL)
        self.assertEqual(evaluate(expr,{**p,'host_annual_revenue_usd':2999999}),FAIL)
        self.assertEqual(evaluate(expr,{**p,'host_employee_count':1,'host_academic_or_government_institution':True}),PASS)

    def test_evaluations_exact_six_months(self):
        expr=obligations()['US-J1-INTERN-POL-008']
        p=dict(programme_duration_months=6,end_evaluation_before_end_signed_by_participant_and_supervisor=True,midpoint_evaluation_signed_by_participant_and_supervisor=False,sponsor_evaluation_retention_years_after_end=3)
        self.assertEqual(evaluate(expr,p),PASS)
        self.assertEqual(evaluate(expr,{**p,'programme_duration_months':6.1}),FAIL)
        self.assertEqual(evaluate(expr,{**p,'sponsor_evaluation_retention_years_after_end':2.99}),FAIL)

    def test_country_education_and_or(self):
        expr=australia()['AU_462_FIRST_POL_04']
        self.assertEqual(evaluate(expr,dict(passport_country='IL',secondary_school_qualification=True,military_service_completed=False,legal_military_exemption=False)),FAIL)
        self.assertEqual(evaluate(expr,dict(passport_country='IL',secondary_school_qualification=True,legal_military_exemption=True)),PASS)
        self.assertEqual(evaluate(expr,dict(passport_country='AR',tertiary_qualification=False,successfully_completed_undergraduate_university_years=2)),PASS)
        self.assertEqual(evaluate(expr,dict(passport_country='TH',tertiary_qualification=False,successfully_completed_undergraduate_university_years=2)),FAIL)
        self.assertEqual(evaluate(expr,dict(passport_country='KR',tertiary_qualification=True)),UNKNOWN)

    def test_calendar_boundary_and_leap(self):
        expr=dict(operator='within_calendar_years',event_field='test',reference_field='application',years=2,strict_after_earliest=True)
        self.assertEqual(evaluate(expr,dict(test='2024-10-28',application='2026-10-28')),FAIL)
        self.assertEqual(evaluate(expr,dict(test='2024-10-29',application='2026-10-28')),PASS)
        self.assertEqual(evaluate({**expr,'years':1,'strict_after_earliest':False},dict(test='2023-02-28',application='2024-02-29')),PASS)

    def test_score_units_and_each_component(self):
        expr=dict(operator='score_matrix',test_field='test',scores_field='scores',table={'IELTS':{'listening':5,'reading':5,'writing':5,'speaking':5}})
        p=dict(test='IELTS',scores=dict(listening=9,reading=9,writing=4.5,speaking=9),english_score_scheme_verified_for_instrument=True)
        self.assertEqual(evaluate(expr,p),FAIL)
        self.assertEqual(evaluate(expr,{**p,'english_score_scheme_verified_for_instrument':False}),UNKNOWN)
        self.assertEqual(evaluate(expr,{**p,'scores':dict(listening=5,reading=5,writing=5,speaking=5)}),PASS)

    def test_fee_fifty_percent_amendment_and_sunset(self):
        expr=dict(operator='h1b_additional_fee')
        p=dict(fee_category_and_applicability_authoritatively_verified=True,petition_filing_date='2026-10-28',us_employee_count=50,h1b_l1_employee_percent=50,amendment_without_extension=False,additional_fee_paid_usd=0)
        self.assertEqual(evaluate(expr,p),PASS)
        self.assertEqual(evaluate(expr,{**p,'h1b_l1_employee_percent':50.1}),FAIL)
        self.assertEqual(evaluate(expr,{**p,'h1b_l1_employee_percent':50.1,'additional_fee_paid_usd':4000}),PASS)
        self.assertEqual(evaluate(expr,{**p,'h1b_l1_employee_percent':99,'amendment_without_extension':True}),PASS)
        self.assertEqual(evaluate(expr,{**p,'petition_filing_date':'2027-10-01'}),UNKNOWN)

    def test_selection_weight_not_a_selection_guarantee(self):
        expr=dict(operator='oews_selection_weight')
        self.assertEqual(evaluate(expr,dict(selection_system_applicable_fiscal_year_verified=True,verified_oews_levels_for_all_positions=[4,2,3],claimed_selection_weight=2)),PASS)
        self.assertEqual(evaluate(expr,dict(selection_system_applicable_fiscal_year_verified=True,verified_oews_levels_for_all_positions=[4,2,3],claimed_selection_weight=4)),FAIL)

    def test_conflict_cannot_be_profile_overridden(self):
        self.assertEqual(evaluate(classified()['US-WK-01-POL-0007'],dict(approved=True,fee_exempt=True)),UNKNOWN)

    def test_income_no_invented_minimum_and_school_age(self):
        self.assertEqual(evaluate(australia()['AU_191_REGIONAL_PROVISIONAL_POL_02'],dict(ato_assessment_income_years_out_of_eligible_five_years=3,eligible_visa_conditions_complied_during_australian_stay=True,income=0)),PASS)
        school=australia()['AU_500_POL_01'];p=dict(school_student=True,secondary_school_exchange_participant=False,date_of_birth='2009-10-28',application_date='2026-10-28',school_year='9',school_year_start_date='2026-10-28')
        self.assertEqual(evaluate(school,p),FAIL);self.assertEqual(evaluate(school,{**p,'school_year':'10'}),PASS)

    def test_source_guard_and_completion_are_not_approvals(self):
        data=json.loads((ROOT/'data/processed/knowledge/20261028/knowledge_release.json').read_text(encoding='utf-8'))
        self.assertTrue(data['scope']['full_eligibility_rules_complete'])
        self.assertIn('eligibility_complete_scope',data['scope'])
        self.assertIn('WEST',data['scope']['eligibility_complete_scope'])
        self.assertTrue(all(r['execution_path_complete'] for r in data['requirements']))
        self.assertTrue(all(not r['all_requirements_complete'] for r in data['requirements']))
        guard=next(r for r in data['requirements'] if r['expression']['operator']=='source_gap_guard')
        self.assertEqual(evaluate_requirement(guard,dict(approved=True),'2026-10-28')['status'],UNKNOWN)

if __name__=='__main__':unittest.main()
