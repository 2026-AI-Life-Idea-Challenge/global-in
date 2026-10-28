"""Create validated quote corrections without changing archived input or the DB."""
import ast
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'docs/legal_review'


def load_extractor():
    # Historical generator has top-level writes. Load only its pure extraction code.
    path = ROOT / 'scripts/ingest/usa/shared/evidence/build_usa_program_source_content.py'
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    names = {'SKIP_TAGS', 'HEADING_TAGS'}
    nodes = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)) or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in names for target in node.targets)]
    scope = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope['heading_sections']


def main():
    snapshot_path = ROOT / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    followup = json.loads((OUT / 'evidence_followup_20261028.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(snapshot_path.read_bytes()).hexdigest() == followup['input_sha256']
    index = {e['evidence_id']: e for e in snapshot['evidence']}
    extract = load_extractor()
    replacements, spans = [], []
    cache = {}
    headings = {'US:US-EM-02': 'Intern', 'US:US-EM-03': 'Trainee', 'US:US-ST-03': 'College and University Student', 'US:US-WH-01': 'Summer Work Travel'}
    for row in followup['quote_results']:
        if row['status'] != 'unresolved':
            continue
        item = index[row['evidence_id']]
        raw = (ROOT / item['source_file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['source_sha256']
        if item['country'] == 'usa':
            if item['source_file'] not in cache:
                soup = BeautifulSoup(raw, 'html.parser')
                sections = extract(soup, headings[item['program_id']])
                cache[item['source_file']] = (sections, ' '.join(soup.get_text(' ', strip=True).split()))
            sections, visible_text = cache[item['source_file']]
            original = item['metadata']['original_evidence']
            section = sections[original['section_index']]
            assert section['heading'] == original['heading']
            quote = section['raw_text']
            assert quote and quote in visible_text
            assert not any(token in quote for token in ('get_facebook_share()', 'end tab ', '<a class='))
            replacements.append({
                'evidence_id': item['evidence_id'], 'program_id': item['program_id'],
                'source_file': item['source_file'], 'source_url': item['source_url'],
                'source_sha256': item['source_sha256'], 'section_index': original['section_index'],
                'heading': section['heading'], 'previous_quote': item['exact_quote'],
                'replacement_quote': quote,
                'replacement_quote_sha256': hashlib.sha256(quote.encode('utf-8')).hexdigest(),
                'status': 'corrected_quote_reproduced_from_archived_html',
                'scope_review_required': True, 'legal_validation_approved': False,
            })
        elif item['evidence_id'] == 'DE_OPP_OFFICIAL_PATHWAY_02':
            ranges = [(int(a), int(b)) for a, b in re.findall(r'(\d+)-(\d+)', item['source_location'])]
            assert ranges == [(31, 36), (52, 66)]
            lines = raw.decode('utf-8-sig').splitlines()
            parts = ['\n'.join(lines[a-1:b]) for a, b in ranges]
            reconstructed = '\n\n'.join(parts)
            assert reconstructed == item['exact_quote']
            spans.append({'evidence_id': item['evidence_id'], 'source_file': item['source_file'], 'source_sha256': item['source_sha256'], 'line_ranges': ranges, 'quote_segments': parts, 'status': 'exact_multi_span_quote_reproduced', 'legal_validation_approved': False})
    assert len(replacements) == 17 and len(spans) == 1
    result = {'review_date': '2026-10-28', 'input_sha256': followup['input_sha256'],
              'scope': 'local quote extraction corrections; source snapshot and DB unchanged',
              'replacement_count': len(replacements), 'verified_multi_span_count': len(spans),
              'replacements': replacements, 'multi_span_verifications': spans,
              'database_applied': False, 'legal_validation_completed': 0}
    (OUT / 'quote_corrections_20261028.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Corrected HTML quotes: {len(replacements)}; exact multi-span quotes: {len(spans)}; DB unchanged')


if __name__ == '__main__':
    main()
