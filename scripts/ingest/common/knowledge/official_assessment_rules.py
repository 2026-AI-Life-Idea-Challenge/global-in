"""Only inherently official assessments; never a fallback for unconverted law."""
import hashlib


def compile_rule(original,document):
    topic=original['topic']
    if original['country']!='australia':return None
    definitions={
        'health':('AU_HOME_AFFAIRS_HEALTH','건강 기준의 해당 PIC와 주·부신청자/가족 범위를 적용한 공식 판단',
            ['해당 비자·스트림의 PIC 4005 또는 4007은 무엇인가?', '검사 요청·의견 유효성과 해당 가족 범위를 확인했는가?', '법정 비용 예외 또는 허용되는 건강 면제의 실제 적용이 결정됐는가?']),
        'health_requirement':('AU_HOME_AFFAIRS_HEALTH','건강 기준의 해당 PIC와 주·부신청자/가족 범위를 적용한 공식 판단',
            ['해당 비자·스트림의 건강 PIC와 적용 대상은 누구인가?', '공식 건강 판단과 적용 가능한 예외의 증빙이 확인됐는가?']),
        'character':('AU_HOME_AFFAIRS_CHARACTER','해당 비자·신청자 범위의 인성 기준 공식 판단',
            ['해당 신청자·가족의 기준 적용 범위가 확인됐는가?', '관련 요청·경찰증명과 공식 심사 결과가 확인됐는가?', '과거 기록을 근거 없이 영구 부적격으로 단정하지 않았는가?']),
        'character_requirement':('AU_HOME_AFFAIRS_CHARACTER','해당 비자·신청자 범위의 인성 기준 공식 판단',
            ['해당 신청자·가족의 적용 범위와 공식 심사 근거가 확인됐는가?']),
        'genuine_student':('AU_HOME_AFFAIRS_GENUINE_STUDENT','Genuine Student 기준의 실제 사정에 대한 기관 심사',
            ['실제 학업 목적·사정·공식 질문 및 증빙을 검토했는가?', '해당 기준의 공식 심사 결과가 확인됐는가?']),
        'genuine_temporary_entrant':('AU_HOME_AFFAIRS_GTE','해당 비자 GTE 기준의 개별 사정에 대한 기관 심사',
            ['해당 비자에 적용되는 기준과 체류 목적·사정의 공식 심사 결과가 확인됐는가?']),
        'best_interests_of_child':('AU_HOME_AFFAIRS_CHILD_INTERESTS','해당 미성년자의 최선의 이익에 대한 기관 심사',
            ['실제 미성년 신청자에게 해당 기준이 적용되는가?', '개인별 사정과 공식 심사 판단이 확인됐는가?']),
    }
    if topic not in definitions:return None
    authority,scope,questions=definitions[topic]
    return dict(operator='official_assessment',authority_id=authority,assessment_scope=scope,
        criterion_sha256=hashlib.sha256(document['text'].encode()).hexdigest(),
        source_document_ids=[document['document_id']],source_references=document['source_references'],
        review_questions=questions,source_criterion_text=document['text'],
        verification_evidence=['해당 기준에 관한 공식 요청·판단 자료가 존재하는 경우 출처·발행일·적용 대상·원본 해시 확인'],
        missing_or_conflicting_evidence_result='추가 확인 필요',user_self_certification_accepted=False,
        implementation_scope='trusted_official_result_matching_not_medical_or_legal_judgment_by_ai')
