"""Narrow guards for scope-amplification failures observed in live tests.

These checks do not prove semantic entailment. Invalid citation IDs remain for
the normal citation validator to reject instead of being silently repaired.
"""
from app.services.rag_llm import build_citation_spans


def guard_unsupported_absolutes(draft, evidence, *, program_id=None):
    spans = build_citation_spans(evidence)
    markers = ('예외 없이', '예외없이', '무조건', '모든 경우', '항상 적용', '반드시 승인')
    items = []
    for item in draft.items:
        text = item.answer or ''
        if item.citation_ids and all(c in spans for c in item.citation_ids):
            quotes = ' '.join(spans[c].quote for c in item.citation_ids)
            if any(marker in text and marker not in quotes for marker in markers):
                item = item.model_copy(update={'answer': None, 'citation_ids': []})
            # A single-country call cannot apply its quoted rules to another
            # destination merely because the user asked for a comparison.
            countries = {'AU': ('호주', 'Australia'), 'CA': ('캐나다', 'Canada'),
                         'US': ('미국', 'United States'), 'JP': ('일본', 'Japan'),
                         'DE': ('독일', 'Germany')}
            own = (program_id or '').split(':')[0]
            if own in countries and any(code != own and any(name in text and name not in quotes for name in names)
                                        for code, names in countries.items()):
                item = item.model_copy(update={'answer': None, 'citation_ids': []})
        items.append(item)
    return draft.model_copy(update={'items': items})
