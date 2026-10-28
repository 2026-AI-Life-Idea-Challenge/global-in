"""Inspect live DB source-URL coverage in an explicitly read-only transaction."""
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]


def valid_url(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlsplit(value.strip())
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname)
    except ValueError:
        return False


def main():
    load_dotenv(ROOT / '.env')
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL is not configured; value is not printed')
    with psycopg.connect(url, connect_timeout=10) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        conn.execute("SET LOCAL statement_timeout = '15s'")
        read_only = conn.execute('SHOW transaction_read_only').fetchone()[0]
        evidence = conn.execute('SELECT evidence_id, program_id, country, source_url FROM evidence').fetchall()
        policies = conn.execute('SELECT policy_id, program_id, source_evidence_ids FROM policy_candidates').fetchall()
        programs = conn.execute("SELECT program_id, metadata #>> '{display_name_source,source_url}' FROM programs").fetchall()
        supports = conn.execute("SELECT support_program_id, metadata ->> 'source_url' FROM support_programs").fetchall()
    index = {row[0]: row for row in evidence}
    missing, invalid, country_counts = [], [], {}
    for eid, _, country, source in evidence:
        stats = country_counts.setdefault(country, {'total': 0, 'with_valid_url': 0})
        stats['total'] += 1
        if not source or not source.strip():
            missing.append(eid)
        elif not valid_url(source):
            invalid.append(eid)
        else:
            stats['with_valid_url'] += 1
    bad_policies = []
    for pid, program, refs in policies:
        issues = []
        if not refs:
            issues.append('no_evidence_reference')
        for ref in refs or []:
            item = index.get(ref)
            if item is None:
                issues.append('evidence_reference_missing')
            elif item[1] != program:
                issues.append('evidence_program_mismatch')
            elif not valid_url(item[3]):
                issues.append('linked_evidence_url_missing_or_invalid')
        if issues:
            bad_policies.append({'policy_id': pid, 'issues': sorted(set(issues))})
    result = {
        'checked_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        'scope': 'live DB URL presence and HTTP(S) syntax; not link availability or source-content correctness',
        'transaction_read_only': read_only,
        'evidence': {'total': len(evidence), 'with_valid_url': sum(s['with_valid_url'] for s in country_counts.values()),
                     'missing_ids': missing, 'invalid_ids': invalid, 'by_country': country_counts},
        'policies': {'total': len(policies), 'with_complete_source_url_chain': len(policies) - len(bad_policies), 'issues': bad_policies},
        'program_display_name_sources': {'total': len(programs), 'with_valid_url': sum(valid_url(r[1]) for r in programs),
                                         'missing_or_invalid_ids': [r[0] for r in programs if not valid_url(r[1])]},
        'support_programs': {'total': len(supports), 'with_valid_url': sum(valid_url(r[1]) for r in supports),
                             'missing_or_invalid_ids': [r[0] for r in supports if not valid_url(r[1])]},
        'evidence_url_domains': dict(Counter(urlsplit(row[3].strip()).hostname for row in evidence if valid_url(row[3]))),
        'examples': [{'evidence_id': row[0], 'source_url': row[3]} for row in sorted(evidence)[:3]],
    }
    target = ROOT / 'docs/legal_review/db_source_url_audit_20261028.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
