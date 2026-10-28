"""Read-only, credential-free export of the verified DB release."""
import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from apply_knowledge_release import TABLES,load_release,verify

ROOT=Path(__file__).resolve().parents[4]


def encode(value):
    return (json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    manifest,data=load_release()
    load_dotenv(ROOT/'.env')
    with psycopg.connect(os.environ['DATABASE_URL'],connect_timeout=10,row_factory=dict_row) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        verify(conn,manifest,data)
        tables={t:conn.execute(f'SELECT * FROM {t}').fetchall() for t in ['programs','support_programs','evidence','policy_candidates']+TABLES}
        assert conn.execute('SELECT COUNT(*) AS n FROM evidence_embeddings').fetchone()['n']==0
    files={'db_snapshot.json':encode(tables),'knowledge_release.json':encode(data),'knowledge_manifest.json':encode(manifest),
        'README.md':(ROOT/'docs/data/db_final_status_20261028.md').read_bytes(),
        'db_update_receipt.json':(ROOT/'docs/data/db_final_update_20261028.json').read_bytes(),
        'schema_additions.sql':(ROOT/'scripts/migrations/20261028_knowledge_contract.sql').read_bytes()}
    coverage=ROOT/'data/processed/knowledge/20261028/rule_coverage.json'
    if coverage.exists():
        report=json.loads(coverage.read_text(encoding='utf-8'))
        assert report['release_id']==manifest['release_id']
        files['rule_coverage.json']=coverage.read_bytes()
    files['RULE_COMPLETION_STATUS.md']=(ROOT/'docs/data/rule_completion_status_20261028.md').read_bytes()
    files['rules_runtime/app/__init__.py']=b''
    files['rules_runtime/app/rules/__init__.py']=b''
    for name in ('evaluator.py','reviews.py','contracts.py'):
        files['rules_runtime/app/rules/'+name]=(ROOT/'app/rules'/name).read_bytes()
    files['rules_runtime/scripts/evaluate/knowledge/test_evaluator.py']=(ROOT/'scripts/evaluate/knowledge/test_evaluator.py').read_bytes()
    files['rules_runtime/scripts/evaluate/knowledge/test_release_rules.py']=(ROOT/'scripts/evaluate/knowledge/test_release_rules.py').read_bytes()
    for source in (ROOT/'scripts/ingest/common/knowledge').glob('*.py'):
        if source.name not in ('apply_knowledge_release.py','export_knowledge_db.py','build_knowledge_release.py'):
            files['rules_runtime/scripts/ingest/common/knowledge/'+source.name]=source.read_bytes()
    files['rules_runtime/data/processed/knowledge/20261028/knowledge_release.json']=encode(data)
    sources={}
    for d in data['documents']:
        for ref in d['source_references']:
            path=ref.get('source_file') or ref.get('capture_file')
            expected=ref.get('sha256') or ref.get('capture_sha256')
            actual=(ROOT/path).resolve()
            assert actual.is_relative_to(ROOT/'data')
            raw=actual.read_bytes();assert digest(raw)==expected
            sources[path]=raw
    files.update({'source_files/'+path:raw for path,raw in sources.items()})
    with tempfile.TemporaryDirectory(prefix='global_in_final_db_') as directory:
        sqlite=Path(directory)/'global_in_final.sqlite'
        with closing(sqlite3.connect(sqlite)) as db:
            # Each fixed-allowlist table preserves every source column in row_json.
            for table,rows in tables.items():
                db.execute(f'CREATE TABLE {table}(export_row_id INTEGER PRIMARY KEY,row_json TEXT NOT NULL)')
                db.executemany(f'INSERT INTO {table}(row_json) VALUES(?)',[(json.dumps(r,ensure_ascii=False,default=str),) for r in rows])
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            db.commit()
        files['global_in_final.sqlite']=sqlite.read_bytes()
    counts={t:len(rows) for t,rows in tables.items()}
    files['manifest.json']=encode(dict(release_id=manifest['release_id'],files={p:digest(raw) for p,raw in files.items()},counts=counts,
        embedding_executed=False,production_release_ready=False))
    target=ROOT/'data/exports/team_db_final_20261028.zip';target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,raw in sorted(files.items()):
            archive.writestr(name,raw)
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
        verification=json.loads(archive.read('manifest.json'))
        for name,expected in verification['files'].items():
            assert digest(archive.read(name))==expected
        snapshot=json.loads(archive.read('db_snapshot.json'))
        assert {t:len(rows) for t,rows in snapshot.items()}==counts
        with tempfile.TemporaryDirectory(prefix='global_in_final_verify_') as directory:
            file=Path(directory)/'check.sqlite';file.write_bytes(archive.read('global_in_final.sqlite'))
            with closing(sqlite3.connect(file)) as db:
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                for table,count in counts.items():
                    assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]==count
        with tempfile.TemporaryDirectory(prefix='global_in_rule_runtime_check_') as directory:
            root=Path(directory).resolve()
            for name in archive.namelist():
                if name.startswith('rules_runtime/'):
                    destination=(root/name).resolve()
                    assert destination.is_relative_to(root)
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_bytes(archive.read(name))
            subprocess.run([sys.executable,str(root/'rules_runtime/scripts/evaluate/knowledge/test_evaluator.py')],check=True)
            subprocess.run([sys.executable,str(root/'rules_runtime/scripts/evaluate/knowledge/test_release_rules.py')],check=True)
    temporary.replace(target)
    receipt=dict(file=target.relative_to(ROOT).as_posix(),sha256=digest(target.read_bytes()),bytes=target.stat().st_size,counts=counts,
        release_id=manifest['release_id'],source_files=len(sources),archive_reopened_and_verified=True,packaged_rule_tests_passed=True,embedding_executed=False)
    (ROOT/'docs/data/team_db_final_export_20261028.json').write_bytes(encode(receipt))
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    main()
