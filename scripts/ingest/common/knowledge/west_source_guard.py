"""A real source gap is a guard, not an invented current eligibility rule."""
import hashlib
import json


def build(root,date):
    path='data/processed/usa/employment/west/2026_second_half/west_2026_second_half_structured_draft.json'
    data=json.loads((root/path).read_text(encoding='utf-8'))
    pdf='data/raw/usa/employment/west/2026_second_half/west_2026_second_half_notice.pdf'
    sha=hashlib.sha256((root/pdf).read_bytes()).hexdigest()
    assert sha==data['source_pdf_sha256'] and data['historical_notice'] is True
    text='WEST 2026년 하반기 보관 공고는 과거 회차 자료다. 이 자료나 제외된 2026년 상반기 정책을 새 회차의 신청 자격으로 재사용하지 않는다. 새 회차를 검토하려면 국립국제교육원의 해당 모집 공고와 실제 스폰서·비자 조건을 먼저 확인해야 한다. 현재 자격 판정은 추가 확인 필요로 차단한다.'
    digest=hashlib.sha256(text.encode()).hexdigest()
    document=dict(document_id='STATUS:US-WEST-01:HISTORICAL_SOURCE',revision_id='source-guard-v1:'+digest[:16],
        targets=[dict(target_type='PROGRAM',target_id='US:US-WEST-01')],title='WEST 과거 공고·현재 요건 공백 차단',text=text,content_sha256=digest,
        knowledge_kind='reviewed_policy',source_references=[dict(source_url=data['official_notice_url'],source_file=pdf,sha256=sha,source_kind='archived_official_notice_pdf'),
            dict(source_url=data['official_notice_url'],source_file=path,sha256=hashlib.sha256((root/path).read_bytes()).hexdigest(),source_kind='derived_historical_status_not_official_eligibility_approval')],
        publisher_countries=['KR'],destination_countries=['US'],topics=['historical_notice','current_source_gap'],verified_at=date,
        uncertainty=['현재 회차 비자·선발 요건의 완전한 자료가 없어 실제 자격을 확정할 수 없음'])
    requirement=dict(requirement_id='GUARD:US:US-WEST-01:HISTORICAL_SOURCE',target=document['targets'][0],source_document_ids=[document['document_id']],
        judgeability='conditional',expression=dict(operator='source_gap_guard',reason=text,scope='historical_notice_is_not_a_current_eligibility_source'),description=text,verified_at=date,execution_path_complete=True)
    return document,requirement,{path:hashlib.sha256((root/path).read_bytes()).hexdigest(),pdf:sha}
