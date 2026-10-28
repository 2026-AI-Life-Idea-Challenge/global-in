"""Batch-update review annotations only; all original data must round-trip unchanged."""
import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.ingest.canada.review_support import SPECS, SOURCES, attach_official_review

FILES = [
    'employment/employer_specific_evidence_draft.json',
    'employment/pgwp_evidence_draft.json',
    'study/study_permit_evidence_draft.json',
    'working_holiday/iec_working_holiday_evidence_draft.json',
]


def strip_review(record):
    record = deepcopy(record)
    record.pop('official_review_summary', None)
    for policy in record['policy_candidates']:
        policy.pop('official_review', None)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Verify saved annotations, do not write')
    args = parser.parse_args()
    prepared, ids = [], []
    for relative in FILES:
        path = ROOT / 'data/processed/canada' / relative
        raw = path.read_bytes()
        old = json.loads(raw.decode('utf-8-sig'))
        new = attach_official_review(deepcopy(old))
        assert strip_review(old) == strip_review(new), f'Original data changed: {path}'
        assert attach_official_review(deepcopy(new)) == new, 'Review must be idempotent'
        for p in new['policy_candidates']:
            assert p.get('eligibility_rule') is None
            assert p.get('legal_validation_approved') is False
            assert p.get('approved_for_eligibility_decision') is False
            assert not p['official_review']['legal_validation_completed']
            assert p['official_review']['pending_items']
            ids.append(p['policy_id'])
        prepared.append((path, raw, old, new))
    assert len(ids) == len(set(ids)) == 21 and set(ids) == set(SPECS)
    ledger = {'reviewed_at': '2026-10-28', 'source_catalog': SOURCES,
              'policy_count': len(ids), 'legal_validation_completed': 0, 'database_applied': False,
              'files': [], 'policy_reviews': []}
    for path, raw, old, new in prepared:
        if args.check:
            assert old == new, f'Saved review missing or stale: {path}'
        else:
            path.write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            assert json.loads(path.read_text(encoding='utf-8')) == new
        ledger['files'].append({'path': path.relative_to(ROOT).as_posix(), 'before_sha256': hashlib.sha256(raw).hexdigest(),
                                'after_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'original_content_preserved': True})
        for policy in new['policy_candidates']:
            ledger['policy_reviews'].append({'policy_id': policy['policy_id'], 'original_source_evidence_ids': policy.get('source_evidence_ids', []), **policy['official_review']})
    if not args.check:
        target = ROOT / 'docs/legal_review/canada_policy_review_20261028.json'
        target.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{"CHECK" if args.check else "APPLIED"}: 4 files, 21 review annotations; original content and approval flags preserved; DB unchanged')


if __name__ == '__main__':
    main()
