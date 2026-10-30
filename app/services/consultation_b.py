"""B's existing read-only search and validated RAG, adapted to the C graph."""
from copy import deepcopy

from app.retrieval.program_search import search_programs
from app.retrieval.support_search import search_support_programs, DESTINATION_COUNTRY_CODES
from app.services.program_rag import answer_program_question
from app.services.multi_program_rag import answer_programs_question
from app.services.support_rag import answer_support_question


def load_catalog():
    programs, supports = [], []
    for search, destination in ((search_programs, programs), (search_support_programs, supports)):
        offset = 0
        while True:
            rows = search(limit=100, offset=offset)
            destination.extend(rows)
            if len(rows) < 100:
                break
            offset += 100
    return programs, supports


def resolve_candidates(state):
    profile = state.get('user_profile') or {}
    programs = deepcopy(state.get('catalog_programs', []))
    supports = deepcopy(state.get('catalog_supports', []))
    country = profile.get('target_country')
    category = profile.get('target_visa_type')
    category = 'study' if category == 'student' else category
    requested = set(state.get('requested_program_ids', []))
    requested_supports = set(state.get('requested_support_ids', []))
    programs = [p for p in programs if (p['program_id'] in requested if requested else
                (not country or p['country'] == country) and (not category or p.get('category') == category))]
    program_ids = {p['program_id'] for p in programs}
    supports = [s for s in supports if (s['support_program_id'] in requested_supports if requested_supports else
                (not country or DESTINATION_COUNTRY_CODES[country] in (s.get('destination_countries') or []))
                and (not program_ids or any(link['program_id'] in program_ids for link in s.get('program_links', []))))]
    if state.get('information_scope') == 'support' and not requested:
        programs = []
    return programs, supports


from app.services.grounding_review import with_grounding_review

@with_grounding_review
def answer(state):
    """Reuse B citation validation; no extra interpreter or rewritten answer."""
    profile = state.get('user_profile') or {}
    question = state['user_query']
    programs = state.get('candidate_programs', [])
    supports = state.get('candidate_support_programs', [])
    scope = state.get('information_scope', 'program')
    results = []
    if scope != 'support' and programs:
        if state.get('requested_program_ids') or len(programs) == 1:
            for program in programs:
                results.append(answer_program_question(program['program_id'], question, profile=profile))
        else:
            category = profile.get('target_visa_type')
            results.append(answer_programs_question(question, country=profile.get('target_country'),
                           category='study' if category == 'student' else category, profile=profile))
    selected_supports = set(state.get('requested_support_ids', []))
    if scope in ('support', 'both'):
        for support in supports:
            if support['support_program_id'] in selected_supports or len(supports) == 1:
                results.append(answer_support_question(support['support_program_id'], question, profile=profile))
    return results


def linked_evidence(results):
    """Only B's validated, claim-bound citations become answer evidence."""
    evidence = {}
    for result in results:
        for claim in result.get('claims', []):
            for citation in claim.get('citations', []):
                for url in citation.get('source_urls', []):
                    if not isinstance(url, str) or not url.startswith(('https://', 'http://')):
                        continue
                    key = (citation['chunk_id'], url)
                    verified_at = next((ref.get('verified_at') or ref.get('checked_at') for ref in citation.get('source_references', [])
                                        if isinstance(ref, dict) and ref.get('source_url') == url), None)
                    evidence[key] = dict(chunk_id=citation['chunk_id'], document_id=citation.get('document_id', ''),
                                         content=citation.get('quote', ''), source_title=citation.get('title', ''),
                                         source_url=url, verified_at=verified_at, is_valid=True,
                                         validation_scope='citation_binding_only_not_legal_approval',
                                         program_id=claim.get('program_id') or result.get('program_id'),
                                         support_program_id=result.get('support_program_id'),
                                         source_references=deepcopy(citation.get('source_references', [])),
                                         answer_approved=citation.get('answer_approved'),
                                         content_review_status=citation.get('content_review_status'))
    return list(evidence.values())
