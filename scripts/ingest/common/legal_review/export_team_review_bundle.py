"""Export a verified, credential-free development snapshot from the live DB."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import zipfile

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'data/exports/team_review_20261028'
NS = 'bounded_policy_review_20261028'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def main():
    registry_path = ROOT / 'data/processed/legal_review/policy_content_approval_registry_20261028.json'
    registry_raw = registry_path.read_bytes()
    registry = json.loads(registry_raw)
    registry_sha = sha(registry_raw)
    load_dotenv(ROOT / '.env')
    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10, row_factory=dict_row) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        conn.execute("SET LOCAL statement_timeout = '30s'")
        tables = {}
        for table, key in [('programs','program_id'), ('support_programs','support_program_id'),
                           ('evidence','evidence_id'), ('policy_candidates','policy_id')]:
            # Identifiers are a fixed allowlist, never user input.
            tables[table] = conn.execute(f'SELECT * FROM {table} ORDER BY {key}').fetchall()
    policies = tables['policy_candidates']
    assert len(policies) == 590
    evidence = {r['evidence_id']: r for r in tables['evidence']}
    for row in policies:
        payload = row['metadata'][NS]
        assert payload['registry_sha256'] == registry_sha
        assert payload['decision'] == registry['review_queue'][row['policy_id']]
        assert payload['reviewed_version'] == registry['policies'].get(row['policy_id'])
        for eid in row['source_evidence_ids']:
            assert evidence[eid]['program_id'] == row['program_id']
            assert evidence[eid]['source_url'].startswith(('http://','https://'))
        assert not any(row[k] for k in ['approved_for_embedding','approved_for_user_answers','approved_for_eligibility_decision'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Build in an isolated temporary folder; no partial bundle is published.
    with tempfile.TemporaryDirectory(prefix='global_in_team_') as temporary:
        work = Path(temporary)
        save(work/'db_snapshot.json', tables)
        save(work/'policy_registry.json', registry)
        save(work/'review_status.json', dict(summary=registry['summary'],
            development_data_ready=True, internal_content_review_complete=registry['summary']['internal_content_review_complete'],
            independent_legal_opinion_complete=False,
            production_release_ready=False,
            unresolved_policies=[k for k,r in registry['review_queue'].items()
                if not r['legal_validation_approved'] and not r.get('lifecycle_disposition')],
            additional_excluded_scope_issues=registry['summary'].get('additional_excluded_scope_issues', {}),
            database_registry_sha256=registry_sha))
        source_files = {}
        for row in registry['policies'].values():
            assert sha(row['reviewed_policy_text'].encode()) == row['reviewed_policy_text_sha256']
            for ref in row['source_references']:
                source = (ROOT/ref['source_file']).resolve()
                assert source.is_relative_to(ROOT/'data'), ref['source_file']
                assert sha(source.read_bytes()) == ref['sha256']
                source_files[ref['source_file']] = source
        for relative, source in source_files.items():
            dest = work/'evidence_files'/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        db = sqlite3.connect(work/'global_in_review.sqlite')
        for table, key in [('programs','program_id'), ('support_programs','support_program_id'),
                           ('evidence','evidence_id'), ('policy_candidates','policy_id')]:
            db.execute(f'CREATE TABLE {table} ({key} TEXT PRIMARY KEY, row_json TEXT NOT NULL)')
            db.executemany(f'INSERT INTO {table} VALUES (?,?)',
                [(r[key], json.dumps(r, ensure_ascii=False, default=str)) for r in tables[table]])
        db.execute('CREATE TABLE reviewed_policies (policy_id TEXT PRIMARY KEY, program_id TEXT NOT NULL, country TEXT NOT NULL, policy_text TEXT NOT NULL, review_scope TEXT NOT NULL, version TEXT NOT NULL, source_references TEXT NOT NULL, approved_for_user_answers INTEGER NOT NULL CHECK(approved_for_user_answers=0), approved_for_embedding INTEGER NOT NULL CHECK(approved_for_embedding=0), approved_for_eligibility_decision INTEGER NOT NULL CHECK(approved_for_eligibility_decision=0))')
        originals = {r['policy_id']:r for r in policies}
        for pid, row in registry['policies'].items():
            old = originals[pid]
            db.execute('INSERT INTO reviewed_policies VALUES (?,?,?,?,?,?,?,?,?,?)',
                (pid,old['program_id'],old['country'],row['reviewed_policy_text'],row['scope'],row['version'],
                 json.dumps(row['source_references'], ensure_ascii=False),0,0,0))
        db.execute('CREATE TABLE policy_dispositions (policy_id TEXT PRIMARY KEY, decision_json TEXT NOT NULL)')
        db.executemany('INSERT INTO policy_dispositions VALUES (?,?)',
            [(pid,json.dumps(row,ensure_ascii=False)) for pid,row in registry['review_queue'].items()])
        db.commit()
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT COUNT(*) FROM reviewed_policies').fetchone()[0] == len(registry['policies'])
        db.close()
        shutil.copyfile(ROOT/'scripts/evaluate/legal_review/verify_team_review_bundle.py', work/'verify_bundle.py')
        shutil.copyfile(ROOT/'docs/legal_review/team_data_quickstart_20261028.md', work/'README.md')
        shutil.copyfile(ROOT/'docs/legal_review/team_completion_status_20261028.md', work/'REVIEW_REPORT.md')
        manifest = {p.relative_to(work).as_posix():sha(p.read_bytes()) for p in sorted(work.rglob('*')) if p.is_file()}
        save(work/'manifest.json', dict(registry_sha256=registry_sha, files=manifest,
            database_counts={k:len(v) for k,v in tables.items()}, approved_versions=len(registry['policies']),
            source_files=len(source_files), production_release_ready=False))
        import subprocess
        import sys
        subprocess.run([sys.executable, str(work/'verify_bundle.py'), str(work)], check=True)
        zip_path = OUT.with_suffix('.zip')
        temp_zip = OUT.with_suffix('.zip.tmp')
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(work.rglob('*')):
                if file.is_file():
                    archive.write(file, file.relative_to(work).as_posix())
        # Test the actual archive via independent extraction and verification.
        with tempfile.TemporaryDirectory(prefix='global_in_bundle_check_') as extracted:
            with zipfile.ZipFile(temp_zip) as archive:
                assert archive.testzip() is None
                archive.extractall(extracted)
            subprocess.run([sys.executable, str(Path(extracted)/'verify_bundle.py'), extracted], check=True)
        temp_zip.replace(zip_path)
        save(ROOT/'docs/legal_review/team_export_receipt_20261028.json',
            dict(file=zip_path.relative_to(ROOT).as_posix(), sha256=sha(zip_path.read_bytes()),
                bytes=zip_path.stat().st_size, registry_sha256=registry_sha,
                counts={k:len(v) for k,v in tables.items()}, approved_versions=len(registry['policies']),
                source_files=len(source_files), archive_reopened_and_verified=True,
                development_data_ready=True, internal_content_review_complete=registry['summary']['internal_content_review_complete'], independent_legal_opinion_complete=False, production_release_ready=False))
        print(json.dumps(dict(file=str(zip_path), bytes=zip_path.stat().st_size,
            approved_versions=len(registry['policies']), source_files=len(source_files))))


if __name__ == '__main__':
    main()
