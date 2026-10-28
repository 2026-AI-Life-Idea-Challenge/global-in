"""Offline evidence-integrity audit; never changes source data or approval flags."""
import argparse
import hashlib
import json
from html.parser import HTMLParser
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def audit(snapshot):
    evidence = snapshot['evidence']
    policies = snapshot['policy_candidates']
    programs = {p['program_id'] for p in snapshot['programs']}
    index = {}
    for item in evidence:
        index.setdefault(item['evidence_id'], []).append(item)
    cache = {}
    text_cache = {}
    evidence_rows = []
    for item in evidence:
        issues = []
        relative = item.get('source_file')
        path = (ROOT / relative).resolve() if relative else None
        if path is None or not path.is_relative_to(ROOT) or not path.is_file():
            issues.append('source_file_unavailable')
            raw = None
        else:
            if path not in cache:
                cache[path] = path.read_bytes()
            raw = cache[path]
        metadata = item.get('metadata') or {}
        structured = metadata.get('source_document_type') == 'structured_json'
        expected = metadata.get('processed_file_sha256') if structured else item.get('source_sha256')
        if structured:
            issues.append('official_source_hash_requires_separate_verification')
        if not expected:
            issues.append('source_hash_missing')
        elif raw is not None and hashlib.sha256(raw).hexdigest() != expected:
            issues.append('source_hash_mismatch')
        quote = item.get('exact_quote')
        if not isinstance(quote, str) or not quote.strip():
            issues.append('quote_missing')
        elif raw is not None:
            if path not in text_cache:
                text_cache[path] = raw.decode('utf-8-sig', errors='replace')
            text = text_cache[path]
            if quote not in text:
                # Whitespace-only differences are distinguished from absent text.
                if ' '.join(quote.split()) in ' '.join(text.split()):
                    issues.append('quote_whitespace_difference')
                else:
                    key = (path, 'extracted')
                    if key not in text_cache:
                        extracted = []
                        if path.suffix.lower() == '.json':
                            try:
                                extracted = list(strings(json.loads(text)))
                            except ValueError:
                                pass
                        elif path.suffix.lower() in ('.html', '.htm'):
                            parser = VisibleText()
                            parser.feed(text)
                            extracted = [' '.join(parser.parts)]
                        text_cache[key] = [' '.join(part.split()) for part in extracted]
                    if any(' '.join(quote.split()) in part for part in text_cache[key]):
                        issues.append('quote_matches_extracted_text_only')
                    else:
                        issues.append('quote_not_found_verbatim')
        if not item.get('source_url'):
            issues.append('source_url_missing')
        if item.get('program_id') not in programs:
            issues.append('program_missing')
        evidence_rows.append({'evidence_id': item['evidence_id'], 'program_id': item.get('program_id'), 'issues': issues})
    policy_rows = []
    for item in policies:
        issues = []
        refs = item.get('source_evidence_ids') or []
        if not refs:
            issues.append('evidence_reference_missing')
        for ref in refs:
            linked = index.get(ref, [])
            if not linked:
                issues.append('evidence_reference_unresolved')
            elif len(linked) != 1:
                issues.append('evidence_reference_ambiguous')
            elif linked[0].get('program_id') != item.get('program_id'):
                issues.append('evidence_program_mismatch')
        if not item.get('policy_text'):
            intentional = item.get('metadata', {}).get('policy_text_missing_intentionally')
            issues.append('policy_conditions_pending_review' if intentional else 'policy_text_missing')
        if item.get('program_id') not in programs:
            issues.append('program_missing')
        policy_rows.append({'policy_id': item['policy_id'], 'program_id': item.get('program_id'), 'issues': sorted(set(issues)), 'review_status': item.get('review_status')})
    def counts(rows):
        return dict(Counter(issue for row in rows for issue in row['issues']))
    return {
        'scope': 'snapshot integrity only; not legal approval or live database verification',
        'counts': {key: len(snapshot[key]) for key in ('programs', 'policy_candidates', 'evidence', 'support_programs')},
        'policy_countries': dict(Counter(p['country'] for p in policies)),
        'evidence_issues': counts(evidence_rows), 'policy_issues': counts(policy_rows),
        'duplicate_evidence_ids': [key for key, rows in index.items() if len(rows) > 1],
        'duplicate_policy_ids': [key for key, n in Counter(p['policy_id'] for p in policies).items() if n > 1],
        'approval_counts': {key: sum(p.get(key) is True for p in policies) for key in ('legal_validation_approved', 'approved_for_eligibility_decision', 'approved_for_embedding', 'approved_for_user_answers')},
        'evidence_results': evidence_rows, 'policy_results': policy_rows,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/legal_review/snapshot_integrity_20261027.json')
    args = parser.parse_args()
    payload = args.input.read_bytes()
    result = audit(json.loads(payload))
    result['input_sha256'] = hashlib.sha256(payload).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence_results', 'policy_results')}, ensure_ascii=False, indent=2))
