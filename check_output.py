import json, sys
sys.path.insert(0, '.')

from app.agent.eligibility.demo_profile_schema import demo_profile_ca_iec_wh_pass, demo_profile_ca_iec_wh_fail_funds
from app.agent.eligibility.checker import check_eligibility
from app.agent.eligibility.fetcher import RuleSet, RequirementRecord

RELEASE_JSON = 'data/processed/knowledge/20261028/releases/knowledge-v1-20261028-0e63b144b983/knowledge_release.json'
with open(RELEASE_JSON, encoding='utf-8') as f:
    data = json.load(f)

reqs = [
    RequirementRecord(
        requirement_id=r['requirement_id'],
        target_type='PROGRAM',
        target_id='CA:iec_working_holiday',
        judgeability=r['judgeability'],
        definition=r['expression'],
        release_id='v1',
    )
    for r in data['requirements']
    if r.get('target', {}).get('target_id') == 'CA:iec_working_holiday'
]

rule_set = RuleSet(
    rule_set_id='RS_CA_IEC',
    target_type='PROGRAM',
    target_id='CA:iec_working_holiday',
    coverage_complete=False,
    definition={},
    release_id='v1',
)

for label, profile in [('PASS 케이스', demo_profile_ca_iec_wh_pass()), ('FAIL 케이스', demo_profile_ca_iec_wh_fail_funds())]:
    r = check_eligibility(rule_set=rule_set, requirements=reqs, profile=profile, as_of='2026-10-28', verified_reviews=[])
    print(f'=== [{label}] overall: {r.overall} ===')
    for req in r.requirements:
        print(f'  [{req.outcome}] {req.requirement_id}  ({req.judgeability})')
    print()
