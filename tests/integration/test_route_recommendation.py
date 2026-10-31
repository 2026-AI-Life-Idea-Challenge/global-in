"""B catalog scope resolution, separate from personal eligibility."""
from app.agent.route_recommendation import run


def state():
    return dict(user_profile={'target_country':'canada','target_visa_type':'student'},
                catalog_programs=[dict(program_id='CA:study',country='canada',category='study'),dict(program_id='AU:work',country='australia',category='employment')],
                catalog_supports=[dict(support_program_id='S',destination_countries=['CA'],program_links=[dict(program_id='CA:study')],availability='CLOSED')])


def test_student_alias_and_linked_closed_support_are_preserved():
    data=state();data['information_scope']='both'
    result=run(data)
    assert [p['program_id'] for p in result['candidate_programs']]==['CA:study']
    assert result['candidate_support_programs'][0]['availability']=='CLOSED'
    assert result['next_node']=='eligibility_review'


def test_explicit_compare_targets_override_a_single_country_filter():
    data=state();data['requested_program_ids']=['CA:study','AU:work']
    assert len(run(data)['candidate_programs'])==2


def test_support_only_search_does_not_invent_a_visa_selection():
    data=state();data['information_scope']='support'
    assert run(data)['candidate_programs']==[]
