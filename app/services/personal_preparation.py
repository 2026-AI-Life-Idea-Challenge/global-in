"""Read-only, rule-based personal preparation. No invented documents or deadlines."""
import hashlib

from app.services.consultation_catalog import load_catalog_detail
from app.agent.eligibility_review import run as review


# These labels describe preparation actions, not new legal requirements.
_ACTIONS = [
    (('labour agreement', 'labor agreement', '노동협약'), '고용주에게 노동협약 적용 여부 문의하기', '지원할 직무에 적용되는 노동협약과 본인이 확인할 조건을 고용주에게 문의하고 답변을 기록하세요.'),
    (('licensing', 'registration or membership', '면허', '등록'), '근무 지역의 직업 면허·등록 필요 여부 확인하기', '예정 직무와 근무 지역을 정한 뒤 해당 직업의 면허·등록이 필요한지 관할 기관에 확인하세요.'),
    (('age', 'years old', '연령', '나이'), '생년월일과 신청 예정일로 연령 조건 확인하기', '프로필의 생년월일을 확인하고, 신청 예정일에 적용되는 연령 기준과 예외 여부를 공식 안내에서 대조하세요.'),
    (('passport', 'nationality', 'citizenship', '여권', '국적'), '신청에 사용할 국적·여권 정보 확인하기', '신청에 사용할 여권의 국적과 유효기간을 확인하고 해당 경로의 대상 국가 목록과 대조하세요.'),
    (('english', 'language', '영어', '언어'), '보유한 언어 성적과 인정 기준 대조하기', '보유한 시험·성적·응시일을 정리하세요. 해당 경로에서 인정하는 성적과 면제 조건을 공식 안내와 비교하세요.'),
    (('skills assessment', '기술심사'), '기술심사 필요 여부와 요청 시점 확인하기', '본인의 직무·경로에 기술심사가 필요한지 확인하세요. 기관이 요청할 때만 진행하도록 명시된 경우 먼저 심사를 신청하지 마세요.'),
    (('work experience', 'experience', '경력'), '관련 경력 기간과 담당 업무 정리하기', '본인의 근무 기간·직무·담당 업무를 정리해 공식 경력 기준과 대조하세요. 부족한 정보는 프로필에 보완하세요.'),
    (('nomination', 'sponsor', '고용주', '지명'), '고용주의 지명·후원 진행 상태 확인하기', '고용주에게 본인 경로의 지명·후원 필요 여부와 현재 진행 상태, 다음에 전달할 정보를 문의하세요.'),
    (('health', '건강'), '건강 관련 요구 사항과 안내 확인하기', '공식 신청 안내에서 본인에게 필요한 건강 관련 절차와 통지 여부를 확인하세요. 검사 항목이나 시점은 임의로 확정하지 마세요.'),
    (('character', '품행', '범죄'), '품행 관련 질문과 제출 요청 확인하기', '신청서의 품행 관련 질문을 확인하고 본인에게 요청되는 자료가 있는지 공식 안내에서 확인하세요.'),
    (('fund', 'financial', '재정', '자금'), '본인의 준비 자금과 재정 기준 비교하기', '본인이 사용할 수 있는 자금과 증빙 가능 내역을 정리하고 공식 재정 기준과 대조하세요.'),
    (('education', 'qualification', '학력', '학위'), '학력·자격 정보와 인정 기준 대조하기', '본인의 학력·전공·취득 자격을 정리하고 해당 경로에서 요구하는 인정 기준과 대조하세요.'),
    (('visa', '비자', '체류'), '현재 비자와 신청 위치 조건 확인하기', '현재 비자·체류 상태와 신청 예정 위치를 정리해 해당 경로의 신청 조건과 대조하세요.'),
]


def action_for(text):
    # Match the original requirement heading before unrelated exception footnotes.
    heading = text.split('적용 범위')[0].lower()
    for words, title, action in _ACTIONS:
        if any(word in heading for word in words):
            return title, action
    return '담당 기관에 본인에게 적용되는 신청 조건 문의하기', '공식 원문의 해당 조건을 담당 기관에 전달하고 본인 상황에 적용되는지 문의한 뒤 답변을 기록하세요.'


def build_preparation(target_id, profile):
    detail = load_catalog_detail(target_id)
    if detail is None:
        return None
    kind = detail['kind']
    state = dict(user_profile=profile, candidate_programs=[], candidate_support_programs=[])
    state['candidate_programs' if kind == 'program' else 'candidate_support_programs'] = [
        {'program_id' if kind == 'program' else 'support_program_id': target_id}]
    reviews = review(state)['eligibility_results']
    sources = detail.get('sources', [])
    groups = {}
    for result in reviews:
        for condition in result.get('condition_results', []):
            original = condition.get('description') or condition['requirement_id']
            title, action = action_for(original)
            group = groups.setdefault(title, dict(action=action, conditions=[]))
            group['conditions'].append(condition)
    if not groups:
        groups['본인 경로의 신청 절차와 필요 정보 정리하기'] = dict(
            action='공식 신청 안내에서 본인 경로를 선택하고 신청 순서와 기관이 요구하는 정보를 확인해 기록하세요.', conditions=[])
    items = []
    for title, group in groups.items():
        conditions = group['conditions']
        outcomes = {c.get('status') for c in conditions}
        status = 'blocked' if '조건 미충족' in outcomes else 'check_needed' if not conditions or '추가 확인 필요' in outcomes else 'todo'
        context = []
        if '생년월일' in title:
            context.append('등록된 생년월일: ' + str(profile.get('date_of_birth') or '미입력 — 프로필에 입력하세요.'))
        if '국적' in title:
            context.append('등록된 국적: ' + ', '.join(profile.get('nationalities') or ['미입력 — 신청 여권 국적을 입력하세요.']))
        if status == 'blocked':
            context.append('현재 입력값으로 미충족 조건이 있습니다. 아래 근거와 대조해 보완 가능 여부를 확인하세요.')
        items.append(dict(id='action:' + target_id + ':' + hashlib.sha256(title.encode()).hexdigest()[:12], program_id=target_id,
            title=title, description=' '.join([group['action'], *context]), done=False, status=status,
            task_version=2, citations=sources, evidence=[dict(text=c.get('description') or c['requirement_id'],
                outcome=c.get('status'), reason=c.get('reason')) for c in conditions]))
    return dict(target_id=target_id, items=items, profile_fields=sorted(k for k,v in profile.items() if v is not None),
        scope='profile_rule_comparison_not_final_approval')
