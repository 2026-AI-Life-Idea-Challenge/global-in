"""Resolve registered candidates using B's current catalog and explicit filters."""
from app.agent.state import AgentState
from app.services.consultation_b import resolve_candidates


def run(state: AgentState) -> dict:
    programs, supports = resolve_candidates(state)
    return dict(candidate_programs=programs, candidate_support_programs=supports,
                candidate_countries=sorted({p['country'] for p in programs}),
                next_node='official_information' if state.get('overview') else 'eligibility_review', current_agent='route_recommendation')
