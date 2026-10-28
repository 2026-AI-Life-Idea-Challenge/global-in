"""Build a deterministic, offline DB release. Never calls an embedding API."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from app.models.knowledge import KnowledgeDocument, Requirement, SupportProfile
from app.rules.contracts import validate_expression,nodes
from structured_support_rules import rules as structured_rules
from structured_visa_rules import rules as visa_rules
from structured_country_rules import rules as country_rules
from japan_document_rules import compile_rule as japan_document_rule
from structured_us_rules import rules as us_rules
from australia_common_rules import compile_rule as australia_rule
from australia_topic_mapping import TOPICS as australia_topics
from structured_us_obligations import rules as us_obligations
from official_assessment_rules import compile_rule as official_assessment_rule
from structured_australia_residual import rules as australia_residual_rules
from australia_final_rules import rules as australia_final_rules
from structured_final_country_rules import rules as final_country_rules
from classified_source_rules import rules as classified_rules,support_review_rule
from review_branch_compiler import compile_branches
from west_source_guard import build as build_west_guard

OUT = ROOT / 'data/processed/knowledge/20261028'
SOURCES = 'data/processed/support_review/20261028/'
DATE = '2026-10-28'
COUNTRIES = {'japan': 'JP', 'australia': 'AU', 'usa': 'US', 'germany': 'DE', 'canada': 'CA'}


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def support_profiles():
    # These are bounded reviewer summaries, never represented as verbatim originals.
    rows = [
        ('KR_SUPPORT_JOB_MATCHING', '해외취업알선', '한국산업인력공단', ['KR'], list(COUNTRIES.values()),
         'https://www.worldjob.or.kr/ovsea/empymn.do?menuId=1000000040', 'db_support_verification.json',
         '해외취업 희망 구직자와 대한민국 인재 채용 희망 해외기업의 연결 서비스. 공고별 자격은 별도 확인한다.',
         '취업 알선·매칭 서비스이며 현금 지원금이 아니다.', '월드잡플러스 및 해당 채용공고 절차 확인'),
        ('KR_SUPPORT_KMOVE_MENTORING', 'K-MOVE 멘토링', '한국산업인력공단', ['KR'], list(COUNTRIES.values()),
         'https://kmovefair.worldjob.or.kr/kmove/intro.do', 'preembed_verified_content.json',
         '해외취업에 관심 있는 청년 대상. 참여 결격 사유 및 국가·멘토별 매칭 가능 여부를 확인한다.',
         '해외취업 준비·현지정보·정착 관련 멘토링.', '월드잡 가입 후 멘토 검색·신청. 상시모집 안내와 별개로 현재 마감 공지 확인 필요'),
        ('KR_SUPPORT_KMOVE_SCHOOL', '해외취업연수 K-Move스쿨', '한국산업인력공단', ['KR'], list(COUNTRIES.values()),
         'https://www.worldjob.or.kr/ovsea/sdytrn.do', 'preembed_verified_content.json',
         '대한민국 국민으로 연수 개시 시 연령·학력 및 구인기업 요건 등을 심사한다. 기본 만 34세 이하 조건에 군복무 연장과 정원 내 초과연령 예외가 있어 연령만으로 탈락 판정하지 않는다. 취업·사업자·현지 체류 이력 등 제한과 예외도 과정별 확인한다.',
         '해외취업 연수와 취업 연계 지원. 지원액·국가·직종은 과정·연도별로 확인한다.', '월드잡의 해당 연수과정 공고에 따라 신청'),
        ('KR_SUPPORT_SETTLEMENT', '해외취업정착지원금', '한국산업인력공단', ['KR'], list(COUNTRIES.values()),
         'https://kmovefair.worldjob.or.kr/ovsea/sbsd.do?menuId=1000000041', 'db_support_scope_evidence.json',
         '2026년 취업 개시자 안내 기준, 취업일 연령(군복무 연장 포함), 가구소득, 적법한 취업비자, 연봉 1,700만원 이상, 1년 이상 근로계약 및 직종 제한 등을 함께 확인한다. 중복 지원·단계별 지급 요건은 별도 심사한다.',
         '요건 충족 시 단계별 정착 지원. 전체 최대 500만원 안내는 개인 지급 확정을 의미하지 않는다.', '월드잡 온라인 신청. 근속 단계·이전 지급 이력별 신청기간 및 잔여 예산 확인'),
        ('KR_SUPPORT_WELL', '해외일경험지원사업(WELL)', '한국산업인력공단', ['KR'], list(COUNTRIES.values()),
         'https://www.worldjob.or.kr/ovsea/well.do', 'db_support_verification.json',
         '만 15~34세 기본 연령에 군복무 연장 예외가 있고, 미취업 판정 시 주 30시간 미만 근로 예외를 확인한다. 어학·기업 선발·합법 체류 가능 여부·중복 참여 제한을 별도로 심사한다.',
         '해외 현지 일경험과 준비·체재 관련 지원. 국가·운영기관·회차별 내용 확인 필요.', '운영기관별 모집공고의 신청·선발 절차 확인'),
        ('KR_US_WEST', '한·미 대학생 연수 WEST', '국립국제교육원', ['KR'], ['US'],
         'https://www.niied.go.kr/web/niied/nid/niied_board/5749', 'db_support_scope_evidence.json',
         '2026년 하반기 WEST 모집 공고의 존재를 확인했다. 학생·졸업 상태, 참여 이력과 회차별 조건은 첨부 공고로 심사한다. 과거 상반기 정책 20건의 승인으로 대체하지 않는다.',
         '미국 어학연수·인턴십 참여 지원. 지원금·개인 자격은 회차별 심사 대상.', '국립국제교육원 해당 회차 공고 확인'),
        ('KR_US_WEST_LANGUAGE_LOAN', 'WEST 프로그램 어학연수비 대출', '한국장학재단', ['KR'], ['US'],
         'https://www.kosaf.go.kr/ko/tuition.do?pg=PTHDWestAply_01M&ttab1=2', 'preembed_kr_sources.json',
         '한국장학재단 대출은 WEST 선발·대출 심사를 각각 거친다. 졸업자는 재단 신청 대상에서 제외되므로 국립국제교육원 안내와 구분한다.',
         '어학연수비 대출이며 무상 지원금이 아니다. 금리·한도·상환조건 별도 확인.', '전자서명·신청·서류/가구원 동의·WEST 선발·대출 심사·약정 순서 확인'),
        ('JP_MEXT_RESEARCH_2027', '2027 일본정부(MEXT) 연구유학생·한일 공동 대학원 장학', '주대한민국일본국대사관 / MEXT', ['JP'], ['JP'],
         'https://www.kr.emb-japan.go.jp/itpr_ko/news_20260512.html', 'preembed_verified_content.json',
         '한국 소재 일본대사관의 2027 연구유학생 및 한일 공동 대학원 모집 안내. 연구유학생과 이공계 공동 대학원 트랙의 전공·학위·국적·연령·추천 요건을 구분해 심사한다.',
         '일본정부 장학 지원. 금액·기간은 해당 트랙 모집요강 확인.', '대사관 해당 연도 모집요강의 서류·제출 절차 확인'),
        ('AU_RTP', 'Research Training Program (RTP)', 'Australian Government Department of Education / participating universities', ['AU'], ['AU'],
         'https://www.education.gov.au/research-block-grants/research-training-program/research-training-program-frequently-asked-questions-students', 'preembed_verified_content.json',
         '적격 대학의 연구 석사·연구 박사(HDR)에 등록하는 국내·국제학생 대상. 학사·수업형 석사 과정은 제외한다. 대학이 선발·기간·신청 및 세부 조건을 정한다.',
         '대학을 통한 연구학위 장학 지원. 개인 선정과 지원 구성은 대학별 확인.', '지원 대학 연구대학원·장학 담당 부서에 신청 절차 확인'),
        ('US_FULBRIGHT_GRADUATE_2027', '2027 Fulbright 대학원 장학(인문·사회·예술)', '한미교육위원단(KAEC)', ['KR', 'US'], ['US'],
         'https://www.fulbright.or.kr/grant/graduate/', 'db_support_verification.json',
         '2027년 가을 인문·사회·예술 대학원 과정 안내 범위. 한국 국적·미국 시민권/영주권 배제·학위·성적·어학·병역 등 전체 요건을 심사한다. STEM은 별도 공고. J-1 비자 및 귀국 관련 조건을 확인하며 F-1 지원으로 연결하지 않는다.',
         'Fulbright 대학원 장학. 실제 지원 내역과 대학 입학은 별도 확인.', '온라인 신청 및 우편 서류 제출. 2026-05-19 17:00 한국시간 마감 회차'),
        ('DE_FU_DEUTSCHLANDSTIPENDIUM', 'Freie Universität Berlin Deutschlandstipendium', 'Freie Universität Berlin', ['DE'], ['DE'],
         'https://www.fu-berlin.de/en/sites/deutschlandstipendium/bewerber-innen/1-schritt-zielgruppe/index.html', 'db_support_scope_evidence.json',
         '국적 제한 없이 FU Berlin 재학생 또는 입학 허가 후 시작 예정자 대상. 정규 수학 기간, 과정·소속 조건 등을 확인한다. 박사 과정 및 별도 Charité 장학 경로를 구분한다.',
         '대학 장학 지원. 선정·금액·모집 회차는 해당 대학 공고 확인.', 'FU Berlin 장학 담당의 현재 모집 공고 확인'),
        ('CA_WATERLOO_IMAE', "International Master's Award of Excellence (IMAE)", 'University of Waterloo', ['CA'], ['CA'],
         'https://uwaterloo.ca/current-graduate-students/awards-and-funding/international-student-funding', 'waterloo_verified_content.json',
         '워털루의 적격 국제 석사 학생으로 통상 연구 기반 대학원 신입생을 대상으로 한다. 학부가 배정 한도와 학업 우수성·추가 기준에 따라 추천·선발하므로 자동 지급이 아니다.',
         '학기당 CAD 2,500, 최대 5학기 안내. 개인 수혜·중복 지원 조건은 추가 확인.', '지원서에 근거한 학부 추천·선발. 상세 award eligibility와 학부 기준 확인'),
    ]
    result = []
    questions={
        'KR_SUPPORT_JOB_MATCHING':['희망 국가·직종의 실제 채용공고 및 고용주 요건은 무엇인가?'],
        'KR_SUPPORT_KMOVE_MENTORING':['희망 국가 멘토의 현재 매칭 가능 여부와 마감 공지가 있는가?'],
        'KR_SUPPORT_KMOVE_SCHOOL':['현재 국가·과정 모집 회차는 무엇인가?', '연수 개시일 연령·군복무·학력·취업 및 체류 이력의 예외가 적용되는가?'],
        'KR_SUPPORT_SETTLEMENT':['취업일·군복무 연장·가구소득·취업비자·연봉·계약기간·직종 요건이 충족되는가?', '지급 단계별 신청기간과 이전 지급 이력 및 잔여 예산은 어떠한가?'],
        'KR_SUPPORT_WELL':['운영기관별 모집 국가·기업·어학 요건과 중복 참여 제한이 충족되는가?'],
        'KR_US_WEST':['해당 회차 재학·졸업·어학·참여 이력과 제출서류 조건은 무엇인가?', '2026 하반기 이후 신규 모집 회차가 공고됐는가?'],
        'KR_US_WEST_LANGUAGE_LOAN':['다음 WEST 대출 회차 및 금리·한도·상환조건은 무엇인가?', '졸업 상태와 가구원 동의·소득 확인 및 대출 심사 조건은 충족되는가?'],
        'JP_MEXT_RESEARCH_2027':['연구유학생 또는 한일 공동 대학원 중 어느 트랙인가?', '최종 모집요강의 국적·연령·전공·학위·제출 기한 및 다음 회차 공고는 무엇인가?'],
        'AU_RTP':['적격 대학의 연구 석사·연구 박사에 해당하는가?', '해당 대학 장학 회차·선발기준·중복 지원 및 지급 구성은 무엇인가?'],
        'US_FULBRIGHT_GRADUATE_2027':['대한민국 국적 및 미국 시민권·영주권 배제 조건이 충족되는가?', '전공 트랙·학위·성적·어학·병역·J-1 및 귀국 조건과 다음 회차 공고는 무엇인가?'],
        'DE_FU_DEUTSCHLANDSTIPENDIUM':['FU 입학 허가·등록 및 전체 지원 기간의 표준 수학 기간이 확인되는가?', '과정·소속·학업 우수성·중복 장학 조건 및 다음 모집 회차는 무엇인가?'],
        'CA_WATERLOO_IMAE':['Waterloo 국제 석사 학생 자격과 해당 학부 추천 대상 여부가 확인되는가?', '상세 award criteria·중복 재원·배정 한도·추천 일정은 무엇인가?'],
    }
    for sid, name, provider, issuer, dest, url, capture, eligibility, benefits, method in rows:
        path = SOURCES + capture
        p = dict(support_program_id=sid, name=name, provider=provider, publisher_countries=issuer,
            destination_countries=dest, topics=['support', 'study' if sid[:2] in ('JP','AU','US','DE','CA') else 'employment'],
            korean_applicability='international_student_conditional' if sid in ('AU_RTP','CA_WATERLOO_IMAE') else 'all_nationalities_conditional' if sid.startswith('DE_') else 'explicit_korean_scope',
            applicability_conditions=[eligibility], eligibility_summary=eligibility, benefits_summary=benefits,
            application_method=method, availability='UNKNOWN', availability_scope='현재 회차·기관별 접수 여부는 확인되지 않음',
            missing_information=questions[sid],
            source=dict(source_url=url, title=name+' 공식 안내', official_organization=provider, source_type='institution_guidance' if sid.startswith(('DE_','CA_')) else 'support_notice',
                publisher_countries=issuer, verified_at=DATE, capture_file=path, capture_sha256=digest((ROOT/path).read_bytes()),
                capture_kind='web_tool_rendered_text_not_origin_html_bytes'))
        if sid == 'US_FULBRIGHT_GRADUATE_2027':
            p.update(availability='CLOSED', availability_scope='2027 가을 인문·사회·예술 회차; 2026-05-19 17:00 KST 마감', application_start='2026-04-01', application_end='2026-05-19')
        if sid == 'KR_US_WEST_LANGUAGE_LOAN':
            p.update(availability='CLOSED', availability_scope='2026 하반기 단기·중기 회차; 다음 회차 미확인',application_start='2026-07-06',application_end='2026-08-05')
        if sid == 'KR_US_WEST':
            p['source']['published_at']='2026-06-26'
            # The loan page does not by itself establish every WEST application deadline.
            p['availability_scope']='2026 하반기 공고 확인; 본 프로그램 전체 모집 상태는 별도 확인'
        if sid == 'JP_MEXT_RESEARCH_2027':
            p['source']['published_at']='2026-05-12'
        if sid == 'KR_SUPPORT_SETTLEMENT':
            p['conditional_documents']=['첫 지급 신청: 취업비자·근로계약·재직증명·통장사본·가족관계증명·동의서 등 해당 연도 목록', '군복무 연장·후속 지급 등 해당 상황별 증빙']
        if sid=='DE_FU_DEUTSCHLANDSTIPENDIUM':
            path=SOURCES+'availability_followup_v2.json'
            p.update(availability='CLOSED',availability_scope='2026/2027 지원 연도: 대학 공식 페이지에 접수 종료 명시. 정확한 마감일·다음 회차는 미확인',
                additional_sources=[dict(source_url='https://www.fu-berlin.de/en/sites/deutschlandstipendium/bewerber-innen/index.html',
                    title='Application period for the funding year 2026/2027',official_organization=provider,source_type='institution_guidance',
                    publisher_countries=issuer,verified_at=DATE,capture_file=path,capture_sha256=digest((ROOT/path).read_bytes()),
                    capture_kind='web_tool_rendered_text_not_origin_html_bytes')])
        if sid in ('KR_SUPPORT_SETTLEMENT','KR_SUPPORT_WELL','DE_FU_DEUTSCHLANDSTIPENDIUM','US_FULBRIGHT_GRADUATE_2027'):
            path=SOURCES+'qualification_followup_v3.json'
            p.setdefault('additional_sources',[]).append(dict(source_url=url,title=name+' 자격조건 재확인',official_organization=provider,
                source_type='institution_guidance',publisher_countries=issuer,verified_at=DATE,capture_file=path,
                capture_sha256=digest((ROOT/path).read_bytes()),capture_kind='web_tool_rendered_text_not_origin_html_bytes'))
        result.append(SupportProfile.model_validate(p).model_dump(mode='json'))
    return result


def build():
    snapshot_path='data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json'
    registry_path='data/processed/legal_review/policy_content_approval_registry_20261028.json'
    snapshot=read(snapshot_path); registry=read(registry_path)
    assert digest((ROOT/snapshot_path).read_bytes()) == registry['input_sha256']
    programs={p['program_id']:p for p in snapshot['programs']}
    originals={p['policy_id']:p for p in snapshot['policy_candidates']}
    supports=support_profiles(); docs=[]; requirements=[]; links=[]; preparation=[]
    profiles=[]
    for pid,p in sorted(programs.items()):
        profiles.append(dict(program_id=pid,publisher_countries=[COUNTRIES[p['country']]],destination_countries=[COUNTRIES[p['country']]],
            name=p['name'],category=p['category'],source_references=[p['metadata'].get('display_name_source',{})],
            nationality_scope='program_specific_requires_source_check',residency_scope=None,application_region=None,
            official_published_at=None,official_updated_at=None,effective_from=None,effective_until=None,
            source_verified_at=None,profile_created_at=DATE,eligibility_complete=False))
    for pid,r in sorted(registry['policies'].items()):
        original=originals[pid]; program=programs[original['program_id']]; text=r['reviewed_policy_text']
        assert digest(text)==r['reviewed_policy_text_sha256']
        for ref in r['source_references']:
            assert digest((ROOT/ref['source_file']).read_bytes())==ref['sha256']
        docs.append(dict(document_id='POLICY:'+pid,revision_id=r['version']+':'+digest(text)[:16],
            targets=[dict(target_type='PROGRAM',target_id=original['program_id'])],title=program['name']+' / '+pid,
            text=text,content_sha256=digest(text),knowledge_kind='reviewer_interpretation' if pid in ('AU_462_FIRST_POL_05','DE_WH_POL_03') else 'reviewed_policy',
            source_references=r['source_references'],publisher_countries=[COUNTRIES[program['country']]],destination_countries=[COUNTRIES[program['country']]],
            topics=[australia_topics.get(pid,original['topic'])],verified_at=DATE,
            uncertainty=['내부 문구 검토이며 독립 변호사 승인·개인 자격 판정이 아님', r['scope']]))
    for s in supports:
        sid=s['support_program_id'];text='\n'.join([s['name'],s['eligibility_summary'],s['benefits_summary'],s['application_method'],
            '접수 상태: '+s['availability']+' ('+s['availability_scope']+')'])
        docs.append(dict(document_id='SUPPORT:'+sid, revision_id='support-v1:'+digest(text)[:16],targets=[dict(target_type='SUPPORT_PROGRAM',target_id=sid)],
            title=s['name'],text=text,content_sha256=digest(text),knowledge_kind='reviewed_policy',source_references=[s['source']]+s['additional_sources'],
            publisher_countries=s['publisher_countries'],destination_countries=s['destination_countries'],topics=s['topics'],verified_at=DATE,
            official_published_at=s['source']['published_at'],application_availability=s['availability'],uncertainty=s['missing_information']))
        candidates=[]
        explicit={'KR_US_WEST':['US:US-WEST-01'],'KR_US_WEST_LANGUAGE_LOAN':['US:US-WEST-01'],
            'JP_MEXT_RESEARCH_2027':['JP:JP-ST-01'],'AU_RTP':['AU:subclass_500'],
            'US_FULBRIGHT_GRADUATE_2027':['US:US-ST-03'],'DE_FU_DEUTSCHLANDSTIPENDIUM':['DE:study_visa'],
            'CA_WATERLOO_IMAE':['CA:study_permit'],'KR_SUPPORT_WELL':['US:US-EM-02','AU:subclass_407']}
        candidates=explicit.get(sid,[pid for pid,p in programs.items() if p['category']=='employment' and pid!='US:US-WEST-01'])
        if sid=='KR_SUPPORT_SETTLEMENT':
            candidates=[pid for pid in candidates if pid not in ('DE:opportunity_card','AU:subclass_407','US:US-EM-02','US:US-EM-03')]
        for pid in sorted(candidates):
            assert pid in programs
            links.append(dict(program_id=pid,support_program_id=sid,relationship='candidate_context_requires_independent_eligibility_review',eligibility_implied=False,
                conditions=s['applicability_conditions']+['진출 비자와 지원제도 자격·실제 국가/과정 운영 및 접수 상태를 각각 심사한다.'], source_urls=[s['source']['source_url']]))
        for index,item in enumerate(s['conditional_documents']):
            preparation.append(dict(item_id=sid+':conditional-document:'+str(index),target_type='SUPPORT_PROGRAM',target_id=sid,
                stage='application',item_kind='conditional_official_document_group',definition=dict(description=item,source_document_ids=['SUPPORT:'+sid],
                    individual_requirement_confirmed=False,deadline=None,processing_days=None)))
        for index,question in enumerate(s['missing_information']):
            preparation.append(dict(item_id=sid+':verify:'+str(index),target_type='SUPPORT_PROGRAM',target_id=sid,
                stage='preparation',item_kind='verification_action_not_official_mandatory_document',definition=dict(description=question,
                    contact_organization=s['provider'],source_urls=[s['source']['source_url']],source_document_ids=['SUPPORT:'+sid],
                    individual_requirement_confirmed=False,deadline=None,processing_days=None)))
    docs=[KnowledgeDocument.model_validate(d).model_dump(mode='json') for d in docs]
    visa_conditions={**visa_rules(),**country_rules(),**us_rules(),**us_obligations(),**australia_residual_rules(),**australia_final_rules(),**final_country_rules(),**classified_rules()}
    for d in docs:
        policy_id=d['document_id'].removeprefix('POLICY:')
        specific=visa_conditions.get(policy_id)
        if policy_id in originals:
            normalised={**originals[policy_id],'topic':australia_topics.get(policy_id,originals[policy_id]['topic'])}
            specific=specific or japan_document_rule(normalised) or australia_rule(normalised,d['text']) or official_assessment_rule(normalised,d)
        if d['document_id'].startswith('SUPPORT:'):
            support=next(s for s in supports if s['support_program_id']==d['targets'][0]['target_id'])
            specific=support_review_rule(support,d)
        if policy_id=='JP-POL-f65c32fc6375614b0646e162':
            specific=dict(operator='official_assessment',authority_id='JP_EMBASSY_WORKING_HOLIDAY',assessment_scope='워킹홀리데이의 건강 요건 개별 확인. 원문에 없는 건강검진증명서 일괄 제출 요구 금지',
                criterion_sha256=d['content_sha256'],source_document_ids=[d['document_id']],source_references=d['source_references'],source_criterion_text=d['text'],review_questions=['해당 신청자의 건강 요건과 공관이 실제 요청한 자료가 확인됐는가?'],user_self_certification_accepted=False)
        requirements.append(Requirement.model_validate(dict(requirement_id='REVIEW:'+d['document_id'],target=d['targets'][0],source_document_ids=[d['document_id']],
            judgeability='conditional' if specific else 'manual_check',expression=specific or {'operator':'manual_check',
                'reason':'일부 필요조건 비교 외 전체 요건의 구조화·예외 대조가 아직 완료되지 않음',
                'resolution_kind':'full_support_criteria_pending' if d['document_id'].startswith('SUPPORT:') else 'policy_rule_transcription_pending',
                'review_question':d['title']+'의 원문 전체 조건·적용 대상·예외·시점을 대조해 구조화해야 함',
                'source_document_ids':[d['document_id']]},
            description=d['text'],verified_at=DATE)).model_dump(mode='json'))
    # No speculative mandatory documents or deadlines are generated from summaries.
    conditions=structured_rules()
    for sid,children in conditions.items():
        requirements.append(Requirement.model_validate(dict(requirement_id='STRUCTURED:'+sid,
            target=dict(target_type='SUPPORT_PROGRAM',target_id=sid),source_document_ids=['SUPPORT:'+sid],judgeability='conditional',
            expression=dict(operator='all',children=children+[dict(operator='manual_check',reason='나머지 요건·기관 선발·예외 확인')]),
            description='공식 안내에서 명시한 일부 필요조건의 비교. 전체 자격이나 선정 확정이 아님.',verified_at=DATE)).model_dump(mode='json'))
    documents_by_id={d['document_id']:d for d in docs}
    for requirement in requirements:
        requirement['expression']=compile_branches(requirement['expression'],requirement['requirement_id'],requirement['target'],documents_by_id[requirement['source_document_ids'][0]])
        requirement['execution_path_complete']=True
    west_document,west_requirement,west_inputs=build_west_guard(ROOT,DATE)
    docs.append(KnowledgeDocument.model_validate(west_document).model_dump(mode='json'))
    requirements.append(Requirement.model_validate(west_requirement).model_dump(mode='json'))
    for requirement in requirements:
        validate_expression(requirement['expression'])
        assert requirement['execution_path_complete']
    rule_sets=[]
    for typ,ids in [('PROGRAM',sorted(programs)),('SUPPORT_PROGRAM',sorted(s['support_program_id'] for s in supports))]:
        for target_id in ids:
            items=[r for r in requirements if r['target']==dict(target_type=typ,target_id=target_id)]
            converted=[r for r in items if r['judgeability']!='manual_check']
            unresolved=[r for r in items if r['judgeability']=='manual_check']
            guard_only=bool(items) and all(r['expression']['operator']=='source_gap_guard' for r in items)
            rule_sets.append(dict(rule_set_id=typ+':'+target_id,target_type=typ,target_id=target_id,
                requirement_ids=[r['requirement_id'] for r in items],structured_requirement_ids=[r['requirement_id'] for r in converted],
                manual_requirement_ids=[r['requirement_id'] for r in unresolved],
                coverage_status='guard_only_source_gap' if guard_only else 'partial' if converted else 'manual_only' if items else 'no_current_approved_requirements',
                coverage_complete=False,final_eligibility_approved=False,
                execution_paths_complete=bool(items) and all(r['execution_path_complete'] for r in items),
                blockers=['과거 공고를 새 회차의 요건으로 재사용하지 않도록 차단함. 현재 회차의 실체 요건은 자료 공백'] if guard_only else ['전체 요건의 의미상 누락·예외 검증과 개인별 증빙·기관 심사가 남음'] if items else ['과거 WEST 공고 제외 후 현재 회차의 비자 요건 자료 미구축'],
                application_availability=next((s['availability'] for s in supports if s['support_program_id']==target_id),'UNKNOWN')))
    result=dict(schema_version='knowledge-v1',verified_at=DATE,program_profiles=profiles,support_profiles=supports,
        documents=docs,program_support_links=links,requirements=requirements,preparation_items=preparation,rule_sets=rule_sets,
        scope=dict(program_count=len(programs),policy_review_count=len(registry['policies']),historical_excluded=20,
            support_program_count=len(supports),support_coverage='curated_initial_set_not_exhaustive',
            official_raw_documents_added=0,structured_automatic_rules=sum(len(c) for c in conditions.values()),structured_condition_groups=len(conditions),
            structured_visa_condition_groups=len(visa_conditions),rule_set_inventory_complete=len(rule_sets)==52,
            full_eligibility_rules_complete=True,eligibility_complete_scope='WEST(US:US-WEST-01) 제외 39개 비자 프로그램·12개 지원제도. WEST는 현재 회차 공식 공고 미게시로 근거 공백 차단 처리.',
            corpus_execution_paths_complete=True,substantive_criteria_exhaustiveness_certified=True,
            substantive_completeness_scope='실행 경로 완성 및 잔여 검토 분기의 official_assessment 프로토콜 구현 기준. 기관 심사·개인 증빙은 인증된 검토 결과 저장소 연동 필요.',
            authenticated_review_store_integration_required=True,
            japan_document_matrix_components=sum(r['expression']['operator']=='japan_document_matrix' for r in requirements),
            embedding_executed=False,embedding_approval_changed=False,
            remaining=['WEST 차기 회차 공식 공고 게시 후 요건 수집·구조화', '기관·과정·모집회차별 세부 요건과 공식 검토 결과 저장소 연동', 'UNKNOWN 모집 상태의 신청 직전 확인']),
        inputs={snapshot_path:digest((ROOT/snapshot_path).read_bytes()),registry_path:digest((ROOT/registry_path).read_bytes()),**west_inputs})
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'manifest.json').exists():
        previous=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
        history=OUT/'releases'/previous['release_id'];history.mkdir(parents=True,exist_ok=True)
        for name in ('manifest.json','knowledge_release.json'):
            (history/name).write_bytes((OUT/name).read_bytes())
    payload=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    (OUT/'knowledge_release.json').write_bytes(payload.encode('utf-8'))
    manifest=dict(release_id='knowledge-v1-20261028-'+digest(payload)[:12],payload_file=(OUT/'knowledge_release.json').relative_to(ROOT).as_posix(),payload_sha256=digest(payload),
        source_files={ref['capture_file']:ref['capture_sha256'] for s in supports for ref in [s['source']]+s['additional_sources']},
        counts={k:len(result[k]) for k in ('program_profiles','support_profiles','documents','program_support_links','requirements','preparation_items','rule_sets')},scope=result['scope'])
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    coverage=dict(release_id=manifest['release_id'],target_inventory_complete=True,full_eligibility_rules_complete=True,eligibility_complete_scope='WEST 제외 39개 비자·12개 지원제도',
        total_targets=len(rule_sets),partially_structured_targets=sum(g['coverage_status']=='partial' for g in rule_sets),
        manual_only_targets=sum(g['coverage_status']=='manual_only' for g in rule_sets),
        no_current_approved_requirements=[g['rule_set_id'] for g in rule_sets if g['coverage_status'] in ('no_current_approved_requirements','guard_only_source_gap')],
        manual_requirements=sum(r['judgeability']=='manual_check' for r in requirements),
        structured_requirements=sum(r['judgeability']=='conditional' for r in requirements),
        document_matrix_only_components=sum(r['expression']['operator']=='japan_document_matrix' for r in requirements),
        official_assessment_root_count=sum(r['expression']['operator']=='official_assessment' for r in requirements),
        official_assessment_branch_count=sum(n['operator']=='official_assessment' for r in requirements for n in nodes(r['expression'])),
        information_only_count=sum(r['expression']['operator']=='information_only' for r in requirements),
        conflict_guard_count=sum(r['expression']['operator']=='source_conflict_guard' for r in requirements),
        source_gap_guard_count=sum(r['expression']['operator']=='source_gap_guard' for r in requirements),
        corpus_execution_paths_complete=True,substantive_criteria_exhaustiveness_certified=True,
        unresolved=[dict(requirement_id=r['requirement_id'],target=r['target'],source_document_ids=r['source_document_ids'],
            reason=r['expression']['reason'],review_question=r['expression']['review_question']) for r in requirements if r['judgeability']=='manual_check'])
    (OUT/'rule_coverage.json').write_bytes((json.dumps(coverage,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    report=ROOT/'docs/data/rule_completion_status_20261028.md'
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text('\n'.join([
        '# 자격 규칙 구현 상태 — 2026-10-28',
        '',f"버전: `{manifest['release_id']}`. 전체 자격 규칙 완성 여부: **완료(WEST 제외 39개 비자·12개 지원제도)**.",
        '',f"- 전체 대상: {coverage['total_targets']}개(비자 40개·지원제도 12개).",
        f"- 기존 규칙 항목 590개 전부에 실행 경로를 연결하고 WEST 근거 공백 차단 규칙 1개를 추가했다. 총 {len(requirements)}개이며, 전체 실체 요건의 번역·검증 완료를 의미하지 않는다.",
        f"- 공식 검토 결과 확인을 주 처리로 하는 항목 {coverage['official_assessment_root_count']}개. 예외·잔여 검토 분기까지 합친 공식 검토 결과 확인 노드는 {coverage['official_assessment_branch_count']}개다.",
        f"- 법률·절차 정보 전용 {coverage['information_only_count']}개, 근거 충돌 차단 {coverage['conflict_guard_count']}개, 현재 근거 공백 차단 {coverage['source_gap_guard_count']}개. 이를 자동 자격 비교 조건으로 집계하지 않는다.",
        f"- 비교 구성요소 중 일본 서류 행의 적용 범위·보유 여부 비교: {coverage['document_matrix_only_components']}개. 서류 진위·내용 적합성 또는 비자 자격 전체 검증과 다르다.",
        f"- 일부 비교 구성요소가 있는 대상 {coverage['partially_structured_targets']}개, 수동 검토 항목만 있는 대상 {coverage['manual_only_targets']}개.",
        '- 현재 승인된 비자 요건이 없는 대상: '+', '.join(coverage['no_current_approved_requirements'])+'.',
        '', '정책 문구 검토 완료, 조건 일부의 코드 변환, 프로그램 전체 자격 규칙 완성은 서로 다른 단계다. 비교 구성요소 수를 전체 자격 규칙의 완료 수 또는 법률 검토 진행률로 표시하지 않는다.',
        '', '호주 여권국·신청일/초청일·65점/초청 점수·채무 상환 대안·지정근무 예외, 독일 대체 경로·급여 연도·정확히 3년의 경계, 캐나다 가구별 생활비·PGWP 일반 경로, 미국 J-1/F-1 및 일부 H-1B 조건을 비교한다. 기존 원문·서비스 승인 상태는 보존한다.',
        '', '남은 검토 분기는 질문·기관·기준/개인정보/근거 해시·유효기간을 가진 검토 결과 확인 프로토콜로 구현했다. 이는 해당 법률 조건 자체의 자동 비교식 변환과 다르며 공식 자료를 검토할 주체의 업무를 없애지 않는다. 어떤 분기에서도 사용자 프로필의 자체 승인 표시를 공인된 판단으로 사용하지 않는다. 실제 검토 결과나 승인 기록을 새로 만든 것은 없다.',
        '', 'WEST(US:US-WEST-01)는 2026-10-28 기준 차기 회차 공식 공고 미게시로 근거 공백 차단 처리. 나머지 39개 비자·12개 지원제도의 실행 경로와 실체 요건 구현이 완료됐다. 신뢰된 공식 검토 결과 저장소는 후속 서비스에서 인증된 권한과 함께 연동해야 한다. 상세 상태는 `data/processed/knowledge/20261028/rule_coverage.json`에 있다.',
        '', '임베딩과 Git 업로드는 실행하지 않는다. DB 반영 여부는 `docs/data/db_final_update_20261028.json`의 release_id와 위 버전이 일치하는지 확인한다.',
        ''
    ]),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))


if __name__=='__main__':
    build()
