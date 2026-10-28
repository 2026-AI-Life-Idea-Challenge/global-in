"""Store reviewed versions alongside originals, with backup and drift protection.

Default is a read-only preview. --apply changes only one metadata namespace;
original policy text, evidence links and all service/eligibility gates are kept.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'data/processed/legal_review'
NAMESPACE = 'bounded_policy_review_20261028'


def main(apply=False):
    registry_path = OUT / 'policy_content_approval_registry_20261028.json'
    registry_bytes = registry_path.read_bytes()
    registry = json.loads(registry_bytes)
    snapshot_bytes = (OUT / 'inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    assert hashlib.sha256(snapshot_bytes).hexdigest() == registry['input_sha256']
    original = {p['policy_id']: p for p in json.loads(snapshot_bytes)['policy_candidates']}
    assert set(original) == set(registry['review_queue']) and len(original) == 590
    registry_sha = hashlib.sha256(registry_bytes).hexdigest()
    for row in registry['policies'].values():
        assert hashlib.sha256(row['reviewed_policy_text'].encode()).hexdigest() == row['reviewed_policy_text_sha256']
        for ref in row['source_references']:
            assert hashlib.sha256((ROOT / ref['source_file']).read_bytes()).hexdigest() == ref['sha256']
    payloads = {pid: dict(schema_version=1, registry_sha256=registry_sha,
        review_kind='bounded_policy_wording_not_individual_or_lawyer_approval',
        decision=decision, reviewed_version=registry['policies'].get(pid),
        original_text_preserved=True, service_gates_changed=False)
        for pid, decision in registry['review_queue'].items()}
    load_dotenv(ROOT / '.env')
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL not configured; credentials are never printed')
    stamp = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%dT%H%M%S%f')
    backup_path = OUT / 'db_backups' / f'policy_review_before_{stamp}.json'
    with psycopg.connect(url, connect_timeout=10, row_factory=dict_row) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE' + ('' if apply else ', READ ONLY'))
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '5s'")
        rows = conn.execute('SELECT * FROM policy_candidates ORDER BY policy_id' + (' FOR UPDATE' if apply else '')).fetchall()
        assert {r['policy_id'] for r in rows} == set(original), 'DB policy IDs differ from reviewed snapshot'
        for row in rows:
            old = original[row['policy_id']]
            for key in ['program_id', 'country', 'policy_text', 'source_evidence_ids',
                        'legal_validation_approved', 'approved_for_user_answers',
                        'approved_for_embedding', 'approved_for_eligibility_decision']:
                assert row[key] == old[key], f'DB drift: {row["policy_id"]} {key}'
        changed = [r for r in rows if (r['metadata'] or {}).get(NAMESPACE) != payloads[r['policy_id']]]
        if apply:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(json.dumps(dict(namespace=NAMESPACE, registry_sha256=registry_sha,
                rows=rows), ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
            for row in changed:
                result = conn.execute('UPDATE policy_candidates SET metadata = COALESCE(metadata,\'{}\'::jsonb) || %s WHERE policy_id = %s',
                    (Jsonb({NAMESPACE: payloads[row['policy_id']]}), row['policy_id']))
                assert result.rowcount == 1
            after = conn.execute('SELECT * FROM policy_candidates ORDER BY policy_id').fetchall()
            for before, current in zip(rows, after):
                assert {k: v for k, v in before.items() if k != 'metadata'} == {k: v for k, v in current.items() if k != 'metadata'}
                assert current['metadata'][NAMESPACE] == payloads[current['policy_id']]
                assert {k: v for k, v in current['metadata'].items() if k != NAMESPACE} == {k: v for k, v in (before['metadata'] or {}).items() if k != NAMESPACE}
            conn.execute('''CREATE OR REPLACE VIEW policy_reviewed_for_development AS
                SELECT policy_id, program_id, country, topic, source_evidence_ids,
                       metadata #>> '{bounded_policy_review_20261028,reviewed_version,reviewed_policy_text}' AS policy_text,
                       metadata #>> '{bounded_policy_review_20261028,reviewed_version,scope}' AS review_scope,
                       metadata #>> '{bounded_policy_review_20261028,reviewed_version,version}' AS review_version,
                       metadata #> '{bounded_policy_review_20261028,reviewed_version,source_references}' AS source_references,
                       'bounded_internal_wording_review_not_individual_approval'::text AS review_kind,
                       approved_for_user_answers, approved_for_embedding, approved_for_eligibility_decision
                FROM policy_candidates
                WHERE metadata #>> '{bounded_policy_review_20261028,decision,decision}' = 'approved_bounded_wording'
            ''')
            assert conn.execute('SELECT COUNT(*) AS n FROM policy_reviewed_for_development').fetchone()['n'] == len(registry['policies'])
    # A separate transaction verifies committed values, including unchanged rows.
    if apply:
        with psycopg.connect(url, connect_timeout=10, row_factory=dict_row) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            committed = conn.execute('SELECT policy_id, metadata FROM policy_candidates').fetchall()
            assert len(committed) == 590
            assert all(r['metadata'][NAMESPACE] == payloads[r['policy_id']] for r in committed)
            view_rows = conn.execute('SELECT policy_id, policy_text FROM policy_reviewed_for_development').fetchall()
            assert {r['policy_id'] for r in view_rows} == set(registry['policies'])
            assert all(r['policy_text'] == registry['policies'][r['policy_id']]['reviewed_policy_text'] for r in view_rows)
    result = dict(mode='applied_and_verified' if apply else 'read_only_preview',
        registry_sha256=registry_sha, total=590, rows_needing_update=len(changed),
        approved_review_versions=len(registry['policies']), historical_excluded=registry['summary']['historical_notice_excluded'],
        active_holds=registry['summary']['active_legal_holds'], original_text_changed=False, service_gates_changed=False,
        additional_excluded_scope_issues=registry['summary'].get('additional_excluded_scope_issues', {}),
        embedding_run=False, backup_file=backup_path.relative_to(ROOT).as_posix() if apply else None,
        namespace=NAMESPACE, applied_at=datetime.now(ZoneInfo('Asia/Seoul')).isoformat())
    result.update(internal_content_review_complete=registry['summary'].get('internal_content_review_complete', False),
        interpretations_not_agency_rulings=registry['summary'].get('interpretations_not_agency_rulings', []),
        development_view='policy_reviewed_for_development' if apply else None)
    target = ROOT / 'docs/legal_review' / ('db_review_update_20261028.json' if apply else 'db_review_update_preview_20261028.json')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
