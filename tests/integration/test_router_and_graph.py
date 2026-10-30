"""The real graph follows each current function-node routing contract."""
import pytest
from app.agent import graph
from app.agent.router import route
from app.agent.state import initial_state


@pytest.mark.parametrize('value', ['ask_user','end','route_recommendation','official_information'])
def test_current_router(value):
    assert route({'next_node':value})==value


def test_unknown_route_ends():
    assert route({'next_node':'invalid'})=='end'


def test_real_graph_visits_b_a_b_and_preparation_once(monkeypatch):
    visited=[]
    transitions=[(graph.user_understanding,'user_understanding','route_recommendation'),
                 (graph.route_recommendation,'route_recommendation','eligibility_review'),
                 (graph.eligibility_review,'eligibility_review','official_information'),
                 (graph.official_information,'official_information','preparation_planning'),
                 (graph.preparation_planning,'preparation_planning','end')]
    for module,name,next_node in transitions:
        def run(state,name=name,next_node=next_node):
            visited.append(name)
            return dict(next_node=next_node,final_answer=name)
        monkeypatch.setattr(module,'run',run)
    result=graph._make_graph().compile().invoke(initial_state('test','질문'))
    assert visited==[name for _,name,_ in transitions]
    assert result['final_answer']=='preparation_planning'
