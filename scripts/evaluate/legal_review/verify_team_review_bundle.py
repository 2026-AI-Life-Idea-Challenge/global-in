"""Verify a team export offline using only Python's standard library."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main(root):
    root = root.resolve()
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    assert actual_files == set(manifest['files']), 'Missing or unexpected files'
    for relative, expected in manifest['files'].items():
        path = (root/relative).resolve()
        assert path.is_relative_to(root) and sha(path.read_bytes()) == expected, relative
    registry_raw = (root/'policy_registry.json').read_bytes()
    assert sha(registry_raw) == manifest['registry_sha256']
    registry = json.loads(registry_raw)
    assert registry['summary']['internal_content_review_complete'] is True
    assert registry['summary']['active_legal_holds'] == 0
    assert registry['summary']['interpretations_not_agency_rulings'] == ['AU_462_FIRST_POL_05','DE_WH_POL_03']
    snapshot = json.loads((root/'db_snapshot.json').read_text(encoding='utf-8'))
    originals = {r['policy_id']:r for r in snapshot['policy_candidates']}
    assert len(originals) == 590 and set(originals) == set(registry['review_queue'])
    evidence = {r['evidence_id']:r for r in snapshot['evidence']}
    for pid, old in originals.items():
        for eid in old['source_evidence_ids']:
            assert evidence[eid]['program_id'] == old['program_id']
            assert evidence[eid]['source_url'].startswith(('http://','https://'))
        assert old['metadata']['bounded_policy_review_20261028']['reviewed_version'] == registry['policies'].get(pid)
    for pid,row in registry['policies'].items():
        assert sha(row['reviewed_policy_text'].encode()) == row['reviewed_policy_text_sha256']
        assert sha((originals[pid]['policy_text'] or '').encode()) == row['original_policy_text_sha256']
        for ref in row['source_references']:
            assert sha((root/'evidence_files'/ref['source_file']).read_bytes()) == ref['sha256']
    db = sqlite3.connect(f'file:{(root/"global_in_review.sqlite").as_posix()}?mode=ro', uri=True)
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert db.execute('SELECT COUNT(*) FROM policy_candidates').fetchone()[0] == 590
    rows = db.execute('SELECT policy_id,policy_text,source_references,approved_for_user_answers,approved_for_embedding,approved_for_eligibility_decision FROM reviewed_policies').fetchall()
    assert {r[0] for r in rows} == set(registry['policies'])
    for pid,text,refs,*gates in rows:
        assert text == registry['policies'][pid]['reviewed_policy_text']
        assert json.loads(refs) == registry['policies'][pid]['source_references']
        assert gates == [0,0,0]
    db.close()
    print(json.dumps(dict(status='passed', original_policies=590,
        reviewed_versions=len(rows), all_packaged_hashes_verified=True,
        internal_content_review_complete=registry['summary']['internal_content_review_complete'],
        independent_legal_opinion_complete=False, production_release_ready=False)))


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent)
