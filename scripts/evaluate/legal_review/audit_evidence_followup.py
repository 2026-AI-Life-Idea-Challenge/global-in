"""Read-only source tracing; writes a separate review ledger, never approvals."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf as fitz
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/legal_review'


def norm(text):
    return ' '.join(str(text).split())


def compact(text):
    return re.sub(r'\s+', '', str(text))


def run():
    snapshot_path = ROOT / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    baseline = json.loads((OUT / 'snapshot_integrity_20261027.json').read_text(encoding='utf-8'))
    assert baseline['input_sha256'] == hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    evidence = {e['evidence_id']: e for e in snapshot['evidence']}
    raw_hashes = {}
    for path in sorted((ROOT / 'data/raw').rglob('*')):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            raw_hashes.setdefault(digest, []).append(path.relative_to(ROOT).as_posix())
    pdf_cache, html_cache = {}, {}
    quotes, tables, provenance = [], [], []
    for row in baseline['evidence_results']:
        item = evidence[row['evidence_id']]
        path = ROOT / item['source_file']
        quote = item.get('exact_quote')
        metadata = item.get('metadata') or {}
        if 'quote_not_found_verbatim' in row['issues']:
            result = {'evidence_id': item['evidence_id'], 'source_file': item['source_file'], 'source_location': item.get('source_location'), 'status': 'unresolved'}
            candidates = []
            if path.suffix.lower() == '.pdf':
                if path not in pdf_cache:
                    with fitz.open(path) as doc:
                        pages = []
                        for n, page in enumerate(doc):
                            pages.append((f'page:{n + 1}:sorted', page.get_text(sort=True)))
                            pages.append((f'page:{n + 1}:source_order', page.get_text(sort=False)))
                            middle = page.rect.width / 2
                            for side, bounds in [('left', (0, 0, middle, page.rect.height)), ('right', (middle, 0, page.rect.width, page.rect.height))]:
                                pages.append((f'page:{n + 1}:column:{side}', page.get_text(clip=fitz.Rect(bounds), sort=True)))
                        pdf_cache[path] = pages
                candidates = pdf_cache[path]
            elif path.suffix.lower() in ('.html', '.htm'):
                if path not in html_cache:
                    soup = BeautifulSoup(path.read_bytes(), 'html.parser')
                    for tag in soup(['script', 'style']):
                        tag.decompose()
                    html_cache[path] = soup
                candidates = [('html', html_cache[path].get_text(' ', strip=True))]
            else:
                candidates = [('text', path.read_text(encoding='utf-8-sig'))]
            for location, text in candidates:
                if norm(quote) in norm(text):
                    result.update(status='matched_extracted_whitespace', matched_location=location)
                    break
                if compact(quote) in compact(text):
                    result.update(status='matched_ignoring_all_whitespace', matched_location=location)
                    break
            if result['status'] == 'unresolved':
                result['quote_preview'] = quote[:240]
                result['reason'] = 'extracted_text_does_not_contain_quote; inspect extraction/version/context'
            quotes.append(result)
        if 'quote_missing' in row['issues']:
            original = metadata.get('original_evidence') or {}
            result = {'evidence_id': item['evidence_id'], 'source_file': item['source_file'], 'status': 'unresolved'}
            soup = BeautifulSoup(path.read_bytes(), 'html.parser')
            all_tables = soup.find_all('table')
            table_index = original.get('html_table_index')
            if metadata.get('prose_exact_quote_not_applicable') and isinstance(table_index, int) and 1 <= table_index <= len(all_tables):
                table = all_tables[table_index - 1]
                actual_rows = [[norm(cell.get_text(' ', strip=True)) for cell in tr.find_all(['th', 'td'])] for tr in table.find_all('tr')]
                actual_rows = [r for r in actual_rows if r]
                expected_rows = original.get('rows')
                if expected_rows:
                    expected = [[norm(c) for c in r] for r in expected_rows]
                    header = [norm(c) for c in original.get('header', [])]
                    # Require exact ordered table values, including header, not a bag of cells.
                    if actual_rows == [header] + expected:
                        result['status'] = 'structured_table_exact_match'
                    else:
                        result['reason'] = 'table_header_or_ordered_rows_differ'
                    result.update(expected_rows=len(expected), actual_rows=len(actual_rows) - 1)
                else:
                    header = next((r for r in actual_rows if 'CIP Code' in r), [])
                    code_column = header.index('CIP Code') if 'CIP Code' in header else None
                    data_rows = [r for r in actual_rows if code_column is not None and len(r) > code_column and re.match(r'^\d{2}\.\d{4}$', r[code_column])]
                    codes = {r[code_column] for r in data_rows}
                    result.update(actual_data_rows=len(data_rows), actual_unique_cip_codes=len(codes))
                    if len(data_rows) == original.get('data_row_count') and len(codes) == original.get('unique_cip_count'):
                        result['status'] = 'table_inventory_counts_match_only'
                        result['reason'] = 'stored record contains counts only; individual code eligibility not verified'
                    else:
                        result['reason'] = 'table_inventory_counts_differ'
                result['html_table_index'] = table_index
            else:
                result['reason'] = 'structured_table_metadata_or_source_table_unavailable'
            tables.append(result)
        if 'official_source_hash_requires_separate_verification' in row['issues']:
            expected = item.get('source_sha256')
            matches = raw_hashes.get(expected, [])
            result = {'evidence_id': item['evidence_id'], 'official_source_url': item.get('source_url'), 'expected_source_sha256': expected, 'raw_file_matches': matches, 'status': 'archived_raw_hash_matched' if matches else ('source_hash_missing' if not expected else 'raw_hash_not_located')}
            # Also verify that the processed file explicitly links this hash and URL.
            processed = json.loads(path.read_text(encoding='utf-8-sig'))
            source = processed.get('source') or processed
            result['processed_source_metadata_agrees'] = bool(expected) and source.get('source_sha256') == expected and source.get('source_url') == item.get('source_url')
            result['limitation'] = 'local archive identity only; current official publication and legal effect not verified'
            provenance.append(result)
    report = {
        'review_date': '2026-10-28', 'input_sha256': baseline['input_sha256'],
        'scope': 'local archive quote/table/provenance follow-up; not legal validation approval',
        'quote_summary': dict(Counter(r['status'] for r in quotes)),
        'table_summary': dict(Counter(r['status'] for r in tables)),
        'provenance_summary': dict(Counter(r['status'] for r in provenance)),
        'quote_results': quotes, 'table_results': tables, 'provenance_results': provenance,
        'legal_validation_completed': 0, 'total_policy_candidates': len(snapshot['policy_candidates']),
    }
    target = OUT / 'evidence_followup_20261028.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if not k.endswith('_results')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
