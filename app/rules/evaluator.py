"""Three-state, source-scoped conditions. Missing/invalid values never pass."""
from datetime import date
from math import isfinite

PASS='조건 충족'
FAIL='조건 미충족'
UNKNOWN='추가 확인 필요'


def evaluate(expression, profile, trusted_context=None):
    op=expression.get('operator')
    if op=='manual_check':
        return UNKNOWN
    if op=='official_assessment':
        if trusted_context:
            from app.rules.reviews import review_status
            requirement,as_of,records,original_profile=trusted_context[:4]
            scoped={**requirement,'expression':expression,'requirement_id':expression.get('review_id',requirement['requirement_id'])}
            status=review_status(scoped,original_profile,as_of,records)
            if status==UNKNOWN and len(trusted_context)>4:
                trusted_context[4].append(dict(review_id=scoped['requirement_id'],authority_id=expression['authority_id'],
                    questions=expression.get('review_questions',[]),source_document_ids=expression['source_document_ids']))
            return status
        return UNKNOWN
    if op in ('information_only','source_conflict_guard','source_gap_guard'):
        return UNKNOWN
    if op=='oews_selection_weight':
        if profile.get('selection_system_applicable_fiscal_year_verified') is not True:return UNKNOWN
        levels=profile.get('verified_oews_levels_for_all_positions')
        if not isinstance(levels,list) or not levels or not all(type(x) is int and 1<=x<=4 for x in levels):return UNKNOWN
        claim=profile.get('claimed_selection_weight')
        if type(claim) is not int:return UNKNOWN
        return PASS if claim==min(levels) else FAIL
    if op=='h1b_additional_fee':
        if profile.get('fee_category_and_applicability_authoritatively_verified') is not True:return UNKNOWN
        try:filing=date.fromisoformat(profile['petition_filing_date'])
        except (KeyError,ValueError,TypeError):return UNKNOWN
        count=profile.get('us_employee_count');ratio=profile.get('h1b_l1_employee_percent');amendment=profile.get('amendment_without_extension')
        if type(count) is not int or count<0 or type(ratio) not in (int,float) or not isfinite(ratio) or not 0<=ratio<=100 or type(amendment) is not bool:return UNKNOWN
        if not date(2026,9,9)<=filing<=date(2027,9,30):return UNKNOWN
        required=4000 if count>=50 and ratio>50 and not amendment else 0
        paid=profile.get('additional_fee_paid_usd')
        if type(paid) not in (int,float) or not isfinite(paid):return UNKNOWN
        return PASS if paid==required else FAIL
    if op=='dated_rule':
        try:
            if date.fromisoformat(profile[expression['field']])<date.fromisoformat(expression['not_before']):return UNKNOWN
        except (KeyError,TypeError,ValueError):return UNKNOWN
        return evaluate(expression['condition'],profile,trusted_context)
    if op=='switch':
        key=profile.get(expression['field'])
        if type(key) is not str or key not in expression['cases']:return UNKNOWN
        return evaluate(expression['cases'][key],profile,trusted_context)
    if op=='within_calendar_years':
        try:
            event=date.fromisoformat(profile[expression['event_field']]);reference=date.fromisoformat(profile[expression['reference_field']])
            year=reference.year-expression['years']
            try:earliest=reference.replace(year=year)
            except ValueError:earliest=reference.replace(year=year,day=28)
        except (KeyError,ValueError,TypeError):return UNKNOWN
        upper=event<reference if expression.get('strictly_before_reference') else event<=reference
        lower=event>earliest if expression.get('strict_after_earliest') else event>=earliest
        return PASS if lower and upper else FAIL
    if op=='four_skill_minimum':
        if profile.get('clb_nclc_scheme_verified') is not True:return UNKNOWN
        scores=profile.get(expression['scores_field'])
        if not isinstance(scores,dict):return UNKNOWN
        states=[]
        for key in ('listening','reading','writing','speaking'):
            value=scores.get(key)
            if type(value) not in (int,float) or not isfinite(value):states.append(UNKNOWN)
            else:states.append(PASS if value>=expression['minimum'] else FAIL)
        return FAIL if FAIL in states else UNKNOWN if UNKNOWN in states else PASS
    if op=='de_wh_financial_comparison':
        funds=profile.get('own_bank_funds_eur');ticket=profile.get('return_ticket_payment_evidence_accepted');housing=profile.get('first_three_months_accommodation_payment_evidence_accepted')
        if type(funds) not in (int,float) or not isfinite(funds) or type(ticket) is not bool or type(housing) is not bool:return UNKNOWN
        return PASS if funds>=3500-1000*(int(ticket)+int(housing)) else FAIL
    if op=='score_matrix':
        if profile.get('english_score_scheme_verified_for_instrument') is not True:return UNKNOWN
        test=profile.get(expression['test_field']);scores=profile.get(expression['scores_field'])
        if type(test) is not str or test not in expression['table'] or not isinstance(scores,dict):return UNKNOWN
        grades={'A':5,'B':4,'C+':3,'C':2,'D':1,'E':0};states=[]
        for skill,minimum in expression['table'][test].items():
            actual=scores.get(skill)
            if isinstance(minimum,str):
                if type(actual) is not str or actual not in grades:states.append(UNKNOWN)
                else:states.append(PASS if grades[actual]>=grades[minimum] else FAIL)
            elif type(actual) not in (int,float) or not isfinite(actual):states.append(UNKNOWN)
            else:states.append(PASS if actual>=minimum else FAIL)
        return FAIL if FAIL in states else UNKNOWN if UNKNOWN in states else PASS
    if op=='passport_nationality_match':
        passport=profile.get('passport_country');nationalities=profile.get('nationalities')
        if type(passport) is not str or not isinstance(nationalities,list) or not nationalities or not all(type(n) is str for n in nationalities):return UNKNOWN
        return PASS if passport in nationalities else FAIL
    if op in ('date_gte','date_lt'):
        try:
            actual=date.fromisoformat(profile[expression['field']]);boundary=date.fromisoformat(expression['value'])
            return PASS if (actual>=boundary if op=='date_gte' else actual<boundary) else FAIL
        except (KeyError,TypeError,ValueError):return UNKNOWN
    if op=='gte_field':
        values=[profile.get(expression[key]) for key in ('field','other_field')]
        if any(type(v) not in (int,float) or not isfinite(v) for v in values):return UNKNOWN
        return PASS if values[0]>=values[1] else FAIL
    if op=='japan_document_matrix':
        for key in ('application_type','school_category','school_classification'):
            if expression.get(key) and profile.get(key)!=expression[key]:
                return UNKNOWN
        record=expression['source_record']
        status=record.get('requirement_status')
        if record.get('category_requirements'):
            category=profile.get('employer_category')
            if type(category) is not str:
                return UNKNOWN
            status=record['category_requirements'].get(category,{}).get('status')
        if status!='required':
            return UNKNOWN
        documents=profile.get('provided_document_ids')
        if not isinstance(documents,list) or not all(type(d) is str for d in documents):
            return UNKNOWN
        return PASS if expression['document_id'] in documents else FAIL
    if op=='canada_living_funds':
        family=profile.get(expression['family_field']);funds=profile.get(expression['funds_field'])
        if type(family) is not int or family<1 or type(funds) not in (int,float) or not isfinite(funds):
            return UNKNOWN
        table=[23448,29192,35888,43572,49419,55736,62054]
        minimum=table[family-1] if family<=7 else table[-1]+6318*(family-7)
        return PASS if funds>=minimum else FAIL
    if op=='age_range':
        try:
            born=date.fromisoformat(profile[expression['birth_field']])
            event=date.fromisoformat(profile[expression['event_field']])
        except (KeyError,ValueError,TypeError):
            return UNKNOWN
        if born>event or (born.month, born.day)==(2,29) and (event.month,event.day)==(2,28):
            return UNKNOWN
        if expression.get('event_not_before') and event<date.fromisoformat(expression['event_not_before']):
            return UNKNOWN
        maximum=expression.get('maximum')
        if 'passport_maximum' in expression:
            maximum=expression['passport_maximum'].get(profile.get('passport_country'))
            if maximum is None:
                return UNKNOWN
        age=event.year-born.year-((event.month,event.day)<(born.month,born.day))
        return PASS if age>=expression.get('minimum',0) and (maximum is None or age<=maximum) else FAIL
    if op in ('all','any'):
        children=expression.get('children',[])
        if not children:
            return UNKNOWN
        collected=[];states=[]
        for child in children:
            requests=[]
            child_context=list(trusted_context[:4])+[requests] if trusted_context and len(trusted_context)>4 else trusted_context
            states.append(evaluate(child,profile,child_context));collected.append(requests)
        if op=='all':
            status=FAIL if FAIL in states else UNKNOWN if UNKNOWN in states else PASS
        else:status=PASS if PASS in states else UNKNOWN if UNKNOWN in states else FAIL
        if status==UNKNOWN and trusted_context and len(trusted_context)>4:
            for state,requests in zip(states,collected):
                if state==UNKNOWN:trusted_context[4].extend(requests)
        return status
    value=profile.get(expression.get('field'))
    if value is None:
        return UNKNOWN
    expected=expression.get('value')
    if op=='equals':
        if type(value) is not type(expected):
            return UNKNOWN
        result=value==expected
    elif op=='in':
        if not isinstance(expected,list) or not expected or not all(type(value) is type(x) for x in expected):
            return UNKNOWN
        result=value in expected
    elif op=='contains':
        if not isinstance(value,list) or not value or not all(type(x) is type(expected) for x in value):
            return UNKNOWN
        result=expected in value
    elif op=='not_contains':
        if not isinstance(value,list) or not value or not all(type(x) is type(expected) for x in value):
            return UNKNOWN
        result=expected not in value
    elif op in ('gte','lte','lt','gt'):
        if type(value) not in (int,float) or type(expected) not in (int,float) or not isfinite(value) or not isfinite(expected):
            return UNKNOWN
        if expression['field'].startswith('age_at_') and (type(value) is not int or not 0<=value<=120):
            return UNKNOWN
        result={'gte':value>=expected,'lte':value<=expected,'lt':value<expected,'gt':value>expected}[op]
    else:
        return UNKNOWN
    return PASS if result else FAIL


def evaluate_requirement(requirement,profile,as_of,trusted_review_records=None):
    """An explicit assessment date is required; condition results aren't awards."""
    day=date.fromisoformat(as_of)
    if requirement.get('verified_at') and day!=date.fromisoformat(requirement['verified_at']):
        return dict(status=UNKNOWN,reason='요청 시점의 근거 재확인 필요',final_eligibility=False)
    for field in ('effective_from','effective_until'):
        boundary=requirement.get(field)
        if boundary and ((field=='effective_from' and day<date.fromisoformat(boundary)) or (field=='effective_until' and day>date.fromisoformat(boundary))):
            return dict(status=UNKNOWN,reason='적용 기간 밖의 조건',final_eligibility=False)
    review_requests=[]
    condition=evaluate(requirement['expression'],profile,(requirement,as_of,trusted_review_records,profile,review_requests))
    return dict(status=condition,requirement_id=requirement['requirement_id'],
        final_eligibility=False,source_document_ids=requirement['source_document_ids'],
        assessment_scope=requirement['expression'].get('scope','source_condition_only_not_overall_eligibility'),
        rule_kind=requirement['expression']['operator'],review_requests=review_requests)


def evaluate_target(rule_set,requirements,profile,as_of,trusted_review_records=None):
    """No cross-target evidence; collection coverage and recruitment are separate."""
    target={'target_type':rule_set['target_type'],'target_id':rule_set['target_id']}
    selected={r['requirement_id']:r for r in requirements if r['target']==target}
    results=[]
    for rid in rule_set['requirement_ids']:
        if rid not in selected:
            results.append(dict(requirement_id=rid,status=UNKNOWN,reason='요건 자료 누락'))
        else:
            results.append(evaluate_requirement(selected[rid],profile,as_of,trusted_review_records))
    return dict(target=target,overall_status=UNKNOWN,coverage_complete=rule_set['coverage_complete'],
        condition_results=results,application_availability=rule_set['application_availability'],
        final_eligibility=False,blockers=rule_set['blockers'])
