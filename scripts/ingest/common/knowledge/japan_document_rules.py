"""Retain exact PDF matrix row, school, application and conditional text."""
def compile_rule(original):
    if original['country']!='japan' or original['topic'] not in ('school_specific_document','application_document'):
        return None
    meta=original['metadata'];record=meta.get('source_record',{})
    if not record.get('document_id'):
        return None
    return dict(operator='japan_document_matrix',document_id=record['document_id'],
        application_type=meta.get('application_type'),school_category=meta.get('school_category'),
        school_classification=meta.get('school_classification'),source_record=record,
        scope='document_presence_and_matrix_applicability_only_not_substantive_eligibility',
        conditional_text=record.get('condition_original_ja'),source_url=meta.get('source_url'))
