"""Validate executable DSL paths separately from substantive legal completeness."""
OPERATORS={'official_assessment','information_only','source_conflict_guard','source_gap_guard','oews_selection_weight','h1b_additional_fee','dated_rule','switch','within_calendar_years','four_skill_minimum','de_wh_financial_comparison','score_matrix','passport_nationality_match','date_gte','date_lt','gte_field','japan_document_matrix','canada_living_funds','age_range','all','any','equals','in','contains','not_contains','gte','lte','lt','gt'}


def nodes(expression):
    yield expression
    op=expression['operator']
    if op in ('all','any'):
        for child in expression['children']:yield from nodes(child)
    elif op=='switch':
        for child in expression['cases'].values():yield from nodes(child)
    elif op=='dated_rule':yield from nodes(expression['condition'])


def validate_expression(expression):
    for node in nodes(expression):
        if node['operator'] not in OPERATORS:raise ValueError('Unsupported or pending expression: '+str(node['operator']))
        if node['operator'] in ('all','any') and not node['children']:raise ValueError('Empty Boolean rule')
        if node['operator']=='switch' and not node['cases']:raise ValueError('Empty case table')
        if node['operator']=='official_assessment':
            for field in ('authority_id','criterion_sha256','source_document_ids','source_references','review_questions','source_criterion_text'):
                if not node.get(field):raise ValueError('Incomplete review protocol: '+field)
            if node.get('user_self_certification_accepted') is not False:raise ValueError('User claims cannot be authenticated reviews')
    return True
