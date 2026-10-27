"""Trace missing source hashes to saved HTML, preserving snapshot approvals."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/legal_review'


def identity(url):
    parts = urlsplit(url)
    # Saved pages include tracking queries and an explicit directory index.
    return parts.scheme, parts.netloc, parts.path.removesuffix('index.html')


def main():
    snapshot_path = ROOT / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    previous = json.loads((OUT / 'evidence_followup_20261028.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(snapshot_path.read_bytes()).hexdigest() == previous['input_sha256']
    index = {e['evidence_id']: e for e in snapshot['evidence']}
    archives = {}
    for path in sorted((ROOT / 'data/raw/japan/working_holiday').glob('*.html')):
        raw = path.read_bytes()
        text = raw.decode('utf-8-sig')
        match = re.search(r'<!-- saved from url=\(\d+\)(\S+) -->', text)
        if not match:
            continue
        soup = BeautifulSoup(text, 'html.parser')
        for tag in soup(['script', 'style']):
            tag.decompose()
        archives.setdefault(identity(match[1]), []).append((path, raw, match[1], soup.get_text(' ', strip=True)))
    rows = []
    for prior in previous['provenance_results']:
        if prior['status'] != 'source_hash_missing':
            continue
        item = index[prior['evidence_id']]
        matches = archives.get(identity(item['source_url']), [])
        result = {'evidence_id': item['evidence_id'], 'source_url': item['source_url'], 'status': 'archive_not_uniquely_located'}
        if len(matches) == 1:
            path, raw, saved_url, text = matches[0]
            quote = item.get('exact_quote') or ''
            normal_quote, normal_text = ' '.join(quote.split()), ' '.join(text.split())
            if quote and normal_quote in normal_text:
                status = 'quote_reproduced_in_saved_html'
            elif quote and re.sub(r'\s+', '', quote) in re.sub(r'\s+', '', text):
                status = 'quote_reproduced_ignoring_all_whitespace'
            else:
                status = 'archive_located_quote_requires_review'
            result.update(status=status, archive_file=path.relative_to(ROOT).as_posix(),
                          saved_from_url=saved_url, archive_sha256=hashlib.sha256(raw).hexdigest(),
                          limitation='hash identifies locally saved HTML including browser serialization; not original HTTP response bytes or current legal effect')
        rows.append(result)
    assert len(rows) == 29
    report = {'review_date': '2026-10-28', 'input_sha256': previous['input_sha256'], 'database_applied': False,
              'summary': dict(Counter(r['status'] for r in rows)), 'results': rows}
    (OUT / 'japan_archive_links_20261028.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
