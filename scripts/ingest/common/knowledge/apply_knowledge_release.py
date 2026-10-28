"""Preview or atomically apply the bounded knowledge release; no embeddings."""
import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[4]
DIRECTORY = ROOT/'data/processed/knowledge/20261028'
NS = 'knowledge_v1_20261028'
TABLES = ['knowledge_releases','program_profiles','support_program_profiles','program_support_links',
          'knowledge_documents','knowledge_document_targets','eligibility_requirements','eligibility_rule_sets','preparation_items','knowledge_chunks']
COUNTRIES = {'JP':'japan','AU':'australia','US':'usa','DE':'germany','CA':'canada'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')


def load_release():
    manifest=json.loads((DIRECTORY/'manifest.json').read_text(encoding='utf-8'))
    raw=(ROOT/manifest['payload_file']).read_bytes()
    assert sha(raw)==manifest['payload_sha256']
    data=json.loads(raw)
    for path,expected in {**data['inputs'],**manifest['source_files']}.items():
        resolved=(ROOT/path).resolve()
        assert resolved.is_relative_to(ROOT/'data')
        assert sha(resolved.read_bytes())==expected,path
    return manifest,data


def verify(conn, manifest, data):
    release=manifest['release_id']
    actual=conn.execute('SELECT * FROM knowledge_releases WHERE release_id=%s',(release,)).fetchone()
    assert actual['manifest_sha256']==sha((DIRECTORY/'manifest.json').read_bytes())
    checks={'program_profiles':len(data['program_profiles']),'support_program_profiles':len(data['support_profiles']),
            'program_support_links':len(data['program_support_links']),'knowledge_documents':len(data['documents']),
            'eligibility_requirements':len(data['requirements']),'eligibility_rule_sets':len(data['rule_sets']),'preparation_items':len(data['preparation_items'])}
    for table,count in checks.items():
        assert conn.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE release_id=%s',(release,)).fetchone()['n']==count,table
    docs=conn.execute('SELECT document_id,revision_id,body,metadata FROM knowledge_documents WHERE release_id=%s',(release,)).fetchall()
    assert {(d['document_id'],d['revision_id']):d['body'] for d in docs}=={(d['document_id'],d['revision_id']):d['text'] for d in data['documents']}
    assert all(not d['metadata']['embedding_approved'] and not d['metadata']['answer_approved'] and not d['metadata']['eligibility_decision_approved'] for d in docs)
    profiles=conn.execute('SELECT support_program_id,profile FROM support_program_profiles WHERE release_id=%s',(release,)).fetchall()
    assert {p['support_program_id']:p['profile'] for p in profiles}=={p['support_program_id']:p for p in data['support_profiles']}
    actual_rules=conn.execute('SELECT requirement_id,definition FROM eligibility_requirements WHERE release_id=%s',(release,)).fetchall()
    assert {r['requirement_id']:r['definition'] for r in actual_rules}=={r['requirement_id']:r for r in data['requirements']}
    actual_sets=conn.execute('SELECT rule_set_id,definition FROM eligibility_rule_sets WHERE release_id=%s',(release,)).fetchall()
    assert {r['rule_set_id']:r['definition'] for r in actual_sets}=={r['rule_set_id']:r for r in data['rule_sets']}
    return checks


def main(apply=False):
    manifest,data=load_release();release=manifest['release_id']
    original=json.loads((ROOT/'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json').read_text(encoding='utf-8'))
    baseline={p['policy_id']:p for p in original['policy_candidates']}
    registry=json.loads((ROOT/'data/processed/legal_review/policy_content_approval_registry_20261028.json').read_text(encoding='utf-8'))
    load_dotenv(ROOT/'.env');url=os.environ['DATABASE_URL']
    backup=ROOT/'data/processed/legal_review/db_backups'/('knowledge_before_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json')
    with psycopg.connect(url,connect_timeout=10,row_factory=dict_row) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE'+('' if apply else ', READ ONLY'))
        conn.execute("SET LOCAL lock_timeout='5s'")
        conn.execute("SET LOCAL statement_timeout='60s'")
        policies=conn.execute('SELECT * FROM policy_candidates ORDER BY policy_id'+(' FOR SHARE' if apply else '')).fetchall()
        assert set(baseline)=={p['policy_id'] for p in policies}
        for p in policies:
            old=baseline[p['policy_id']]
            for key in ['program_id','policy_text','source_evidence_ids','approved_for_embedding','approved_for_user_answers','approved_for_eligibility_decision','legal_validation_approved']:
                assert p[key]==old[key],(p['policy_id'],key)
            assert p['metadata']['bounded_policy_review_20261028']['reviewed_version']==registry['policies'].get(p['policy_id'])
        programs=conn.execute('SELECT * FROM programs ORDER BY program_id').fetchall()
        assert {p['program_id'] for p in programs}=={p['program_id'] for p in data['program_profiles']}
        evidence=conn.execute('SELECT * FROM evidence ORDER BY evidence_id').fetchall()
        vector_before=conn.execute('SELECT COUNT(*) AS n FROM evidence_embeddings').fetchone()['n']
        supports=conn.execute('SELECT * FROM support_programs ORDER BY support_program_id'+(' FOR UPDATE' if apply else '')).fetchall()
        assert {p['support_program_id'] for p in original['support_programs']} <= {p['support_program_id'] for p in supports}
        existing={}
        for table in TABLES:
            if conn.execute('SELECT to_regclass(%s) AS name',(table,)).fetchone()['name']:
                existing[table]=conn.execute(f'SELECT * FROM {table}').fetchall()
        if apply:
            save(backup,dict(support_programs=supports,normalized_tables=existing,vector_count=vector_before,
                policy_rows_sha256=sha(json.dumps(policies,sort_keys=True,default=str).encode()),release_id=release))
            conn.execute((ROOT/'scripts/migrations/20261028_knowledge_contract.sql').read_text(encoding='utf-8'))
            old_release=conn.execute('SELECT manifest_sha256 FROM knowledge_releases WHERE release_id=%s',(release,)).fetchone()
            manifest_sha=sha((DIRECTORY/'manifest.json').read_bytes())
            assert not old_release or old_release['manifest_sha256']==manifest_sha,'Release ID collision'
            conn.execute('INSERT INTO knowledge_releases(release_id,manifest_sha256,verified_at,metadata) VALUES(%s,%s,%s,%s) ON CONFLICT(release_id) DO NOTHING',
                (release,manifest_sha,data['verified_at'],Jsonb(manifest)))
            for p in data['program_profiles']:
                conn.execute('INSERT INTO program_profiles VALUES(%s,%s,%s,%s,%s) ON CONFLICT(program_id) DO UPDATE SET publisher_countries=EXCLUDED.publisher_countries,destination_countries=EXCLUDED.destination_countries,profile=EXCLUDED.profile,release_id=EXCLUDED.release_id',
                    (p['program_id'],p['publisher_countries'],p['destination_countries'],Jsonb(p),release))
            for p in data['support_profiles']:
                metadata=dict(source_url=p['source']['source_url'],source_verification='official_content_checked_scope_limited',
                    eligibility_validation='manual_check_required',recruitment_status=p['availability'],content_capture_archived=True,
                    raw_source_archived=False,**{NS:dict(release_id=release,profile=p,automatic_eligibility_approved=False)})
                country=COUNTRIES[p['destination_countries'][0]] if len(p['destination_countries'])==1 else 'multi_country'
                conn.execute('''INSERT INTO support_programs(support_program_id,country,name,provider,source_file,review_status,metadata)
                    VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(support_program_id) DO UPDATE SET
                    review_status=EXCLUDED.review_status,metadata=support_programs.metadata || EXCLUDED.metadata,updated_at=now()''',
                    (p['support_program_id'],country,p['name'],p['provider'],p['source']['capture_file'],'official_content_checked_scope_limited',Jsonb(metadata)))
                conn.execute('''INSERT INTO support_program_profiles VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(support_program_id) DO UPDATE SET publisher_countries=EXCLUDED.publisher_countries,destination_countries=EXCLUDED.destination_countries,
                    korean_applicability=EXCLUDED.korean_applicability,availability=EXCLUDED.availability,source_verified_at=EXCLUDED.source_verified_at,profile=EXCLUDED.profile,release_id=EXCLUDED.release_id''',
                    (p['support_program_id'],p['publisher_countries'],p['destination_countries'],p['korean_applicability'],p['availability'],p['source']['verified_at'],Jsonb(p),release))
            for link in data['program_support_links']:
                conn.execute('''INSERT INTO program_support_links VALUES(%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(program_id,support_program_id) DO UPDATE SET relationship=EXCLUDED.relationship,eligibility_implied=EXCLUDED.eligibility_implied,conditions=EXCLUDED.conditions,source_urls=EXCLUDED.source_urls,release_id=EXCLUDED.release_id''',
                    (link['program_id'],link['support_program_id'],link['relationship'],False,Jsonb(link['conditions']),Jsonb(link['source_urls']),release))
            for d in data['documents']:
                conn.execute('UPDATE knowledge_documents SET active=FALSE WHERE document_id=%s AND revision_id<>%s',(d['document_id'],d['revision_id']))
                conn.execute('UPDATE knowledge_chunks SET active=FALSE WHERE document_id=%s AND revision_id<>%s',(d['document_id'],d['revision_id']))
                conn.execute('''INSERT INTO knowledge_documents VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(document_id,revision_id) DO UPDATE SET metadata=EXCLUDED.metadata,active=EXCLUDED.active,release_id=EXCLUDED.release_id''',
                    (d['document_id'],d['revision_id'],d['content_sha256'],d['knowledge_kind'],d['title'],d['text'],Jsonb(d),True,release))
                for target in d['targets']:
                    conn.execute('INSERT INTO knowledge_document_targets VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',(d['document_id'],d['revision_id'],target['target_type'],target['target_id']))
            for r in data['requirements']:
                conn.execute('''INSERT INTO eligibility_requirements VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(requirement_id) DO UPDATE SET
                    definition=EXCLUDED.definition,judgeability=EXCLUDED.judgeability,release_id=EXCLUDED.release_id''',
                    (r['requirement_id'],r['target']['target_type'],r['target']['target_id'],r['judgeability'],Jsonb(r),release))
            for item in data['preparation_items']:
                conn.execute('''INSERT INTO preparation_items VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(item_id) DO UPDATE SET definition=EXCLUDED.definition,release_id=EXCLUDED.release_id''',
                    (item['item_id'],item['target_type'],item['target_id'],item['stage'],item['item_kind'],Jsonb(item['definition']),release))
            for item in data['rule_sets']:
                conn.execute('''INSERT INTO eligibility_rule_sets VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(rule_set_id) DO UPDATE SET
                    coverage_complete=EXCLUDED.coverage_complete,definition=EXCLUDED.definition,release_id=EXCLUDED.release_id''',
                    (item['rule_set_id'],item['target_type'],item['target_id'],item['coverage_complete'],Jsonb(item),release))
            verify(conn,manifest,data)
            assert conn.execute('SELECT * FROM policy_candidates ORDER BY policy_id').fetchall()==policies
            assert conn.execute('SELECT * FROM programs ORDER BY program_id').fetchall()==programs
            assert conn.execute('SELECT * FROM evidence ORDER BY evidence_id').fetchall()==evidence
            assert conn.execute('SELECT COUNT(*) AS n FROM evidence_embeddings').fetchone()['n']==vector_before
    if apply:
        with psycopg.connect(url,connect_timeout=10,row_factory=dict_row) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            verify(conn,manifest,data)
            assert conn.execute('SELECT * FROM policy_candidates ORDER BY policy_id').fetchall()==policies
            assert conn.execute('SELECT COUNT(*) AS n FROM evidence_embeddings').fetchone()['n']==vector_before
    result=dict(mode='applied_and_verified' if apply else 'read_only_preview',release_id=release,counts=manifest['counts'],
        embedding_executed=False,vector_count_before=vector_before,vector_count_after=vector_before,
        original_programs_policies_evidence_unchanged=True,service_gates_changed=False,
        backup_file=backup.relative_to(ROOT).as_posix() if apply else None,scope=data['scope'],verified_at=datetime.now().isoformat())
    save(ROOT/'docs/data'/('db_final_update_20261028.json' if apply else 'db_final_update_preview_20261028.json'),result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true')
    main(parser.parse_args().apply)
