"""Current DB catalog metadata and original sources, without static legal claims."""
from app.services import db


def _sources(profile):
    records = profile.get('source_references') or ([profile.get('source') or {}] + (profile.get('additional_sources') or []))
    seen, result = set(), []
    for record in records:
        if not isinstance(record, dict):
            continue
        url = record.get('source_url')
        if not isinstance(url, str) or not url.startswith(('https://', 'http://')) or url in seen:
            continue
        seen.add(url)
        result.append(dict(title=record.get('title') or '공식 원문', source_url=url,
                           organization=record.get('official_organization'), verified_at=record.get('verified_at') or record.get('checked_at')))
    return result


def load_catalog():
    with db.get_conn() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        programs = conn.execute('''SELECT p.program_id AS id,p.name,p.country,p.category,k.profile,k.release_id
            FROM programs p LEFT JOIN program_profiles k USING(program_id) ORDER BY p.country,p.program_id''').fetchall()
        supports = conn.execute('''SELECT s.support_program_id AS id,s.name,s.country,s.provider,k.profile,k.release_id,
            k.availability,k.destination_countries,k.source_verified_at
            FROM support_programs s LEFT JOIN support_program_profiles k USING(support_program_id)
            ORDER BY s.support_program_id''').fetchall()
    items = []
    for kind, records in (('program', programs), ('support', supports)):
        for row in records:
            profile = row.get('profile') or {}
            items.append(dict(id=row['id'], kind=kind, name=row['name'], country=row['country'],
                              category=row.get('category'), provider=row.get('provider'),
                              destination_countries=row.get('destination_countries') or profile.get('destination_countries', []),
                              availability=row.get('availability') or 'UNKNOWN',
                              source_verified_at=str(row.get('source_verified_at') or profile.get('source_verified_at') or '') or None,
                              sources=_sources(profile), release_id=row.get('release_id'),
                              eligibility_complete=False, final_eligibility=False))
    return dict(items=items, counts=dict(programs=len(programs), supports=len(supports)),
                scope='stored_official_catalog_not_current_eligibility_or_application_approval')


def load_catalog_detail(target_id):
    item=next((row for row in load_catalog()['items'] if row['id']==target_id),None)
    if item is None:return None
    with db.get_conn() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        rows=conn.execute('''SELECT d.document_id,d.revision_id,d.title,d.metadata,c.chunk_id,c.body,c.ordinal
            FROM knowledge_document_targets t JOIN knowledge_documents d USING(document_id,revision_id)
            JOIN knowledge_chunks c USING(document_id,revision_id)
            WHERE t.target_type=%s AND t.target_id=%s AND d.active AND c.active
            ORDER BY d.document_id,c.ordinal,c.chunk_id''',
            ('PROGRAM' if item['kind']=='program' else 'SUPPORT_PROGRAM',target_id)).fetchall()
    sections=[]
    for row in rows:
        metadata=row['metadata'] or {}
        sources=_sources(metadata)
        body=row['body'].strip()
        if not body:continue
        sections.append(dict(id=row['chunk_id'],title=body.splitlines()[0][:180],body=body,
            document_title=row['title'],sources=sources,
            verified_at=metadata.get('verified_at'),effective_from=metadata.get('effective_from'),
            effective_until=metadata.get('effective_until'),review_status=metadata.get('content_review_status')))
    return dict(**item,sections=sections,content_scope='stored_dataset_text_not_personal_eligibility_approval')
