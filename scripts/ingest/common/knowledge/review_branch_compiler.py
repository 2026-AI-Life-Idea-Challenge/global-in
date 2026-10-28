"""Compile explicit residual review branches into source/case-bound evidence checks.

This completes an execution path, not the underlying substantive legal review.
The original criterion and the exact review question remain independently visible.
"""
import hashlib
import json

AUTHORITIES={'AU':'AU_HOME_AFFAIRS_CASE_REVIEW','CA':'CA_IRCC_CASE_REVIEW','DE':'DE_COMPETENT_RESIDENCE_AUTHORITY','JP':'JP_COMPETENT_VISA_RESIDENCE_AUTHORITY','US':'US_COMPETENT_PROGRAM_AUTHORITY_REVIEW'}


def compile_branches(expression,requirement_id,target,document,path='root'):
    if expression.get('operator')=='manual_check':
        reason=expression['reason']
        claim=dict(source_sha256=document['content_sha256'],requirement_id=requirement_id,path=path,review_question=reason)
        digest=hashlib.sha256(json.dumps(claim,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        authority=('SUPPORT_PROVIDER:'+target['target_id']) if target['target_type']=='SUPPORT_PROGRAM' else AUTHORITIES[target['target_id'].split(':')[0]]
        return dict(operator='official_assessment',review_id=requirement_id+'#'+path,authority_id=authority,
            criterion_sha256=digest,source_document_ids=[document['document_id']],source_references=document['source_references'],
            source_criterion_text=document['text'],review_questions=[reason],assessment_scope=reason,
            verification_evidence=['해당 기준·질문에 관한 실제 권한 기관의 자료를 신뢰된 검토자가 확인한 기록'],
            user_self_certification_accepted=False,original_review_question=reason,
            implementation_scope='residual_review_evidence_matching_not_deterministic_legal_rule_translation')
    if isinstance(expression,dict):
        return {key:([compile_branches(v,requirement_id,target,document,path+'.'+key+str(i)) if isinstance(v,dict) else v for i,v in enumerate(value)] if isinstance(value,list)
            else compile_branches(value,requirement_id,target,document,path+'.'+key) if isinstance(value,dict) else value)
            for key,value in expression.items()}
    return expression
