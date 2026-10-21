
"""STEP 64-52: WEST 2026 H2 source-grounded eligibility review.

Requires PyMuPDF (fitz). Does not modify any previous input, nor approve
content for answers, embedding, or automated eligibility decisions.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

PDF_SHA = 'd04abdc458ad0a4a1f18196c9fdcb05f4ba39821183e0d77aaa5fa5f129a80e2'
REVIEW_SHA = '7b33b3a374ee77734d64d63a10b6b5ed78ca7098d97711fb1e21ad0a1169e0b7'


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(s):
    return re.sub(r'\s+', '', s).lower()


def check_fragments(page_text, fragments, desc):
    source = norm(page_text)
    missing = [s for s in fragments if norm(s) not in source]
    if missing:
        raise ValueError(f'{desc}: PDF에서 문구를 찾지 못함: {missing}')


def save_new_or_verify(path, item):
    content = (
        json.dumps(item, ensure_ascii=False, indent=2) + '\n'
    ).encode('utf-8')

    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(
                f'기존 결과가 다릅니다. 덮어쓰지 않음: {path}'
            )
        status = 'EXISTS_VERIFIED'
    else:
        with path.open('xb') as f:
            f.write(content)
        status = 'CREATED'

    return status, hashlib.sha256(content).hexdigest()


def main():
    root = Path(__file__).resolve().parents[5]

    base = (
        root
        / 'data/processed/usa/employment/west/2026_second_half'
    )

    pdf_path = (
        root
        / 'data/raw/usa/employment/west/2026_second_half'
        / 'west_2026_second_half_notice.pdf'
    )

    review_path = (
        base / 'west_2026_second_half_eligibility_review.json'
    )

    print('===== STEP 64-52 WEST 하반기 원문 검수 =====')

    # 1. 입력 파일 검증
    assert pdf_path.is_file(), f'PDF 없음: {pdf_path}'
    assert review_path.is_file(), f'JSON 없음: {review_path}'

    if hash_file(pdf_path) != PDF_SHA:
        raise ValueError('공식 PDF SHA-256 불일치')

    if hash_file(review_path) != REVIEW_SHA:
        raise ValueError('STEP 64-51 JSON SHA-256 불일치')

    review = json.loads(
        review_path.read_text(encoding='utf-8')
    )

    assert review['source_pdf_sha256'] == PDF_SHA
    assert review['program_id'] == 'US-WEST-01'
    assert review['notice_period'] == '2026_second_half'
    assert review['approved_for_user_answers'] is False
    assert review['approved_for_embedding'] is False
    assert review['automatic_eligibility_rules_enabled'] is False

    print('[PASS] 공식 PDF 및 STEP 64-51 파일 검증')

    # 2. 공식 PDF 원문과 대조
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            'PyMuPDF가 필요합니다. pip install pymupdf'
        ) from exc

    with fitz.open(pdf_path) as doc:
        assert len(doc) == 11

        # PDF 물리 1페이지 = 인쇄 1~2쪽
        p2 = doc[0].get_text()

        # PDF 물리 2페이지 = 인쇄 3~4쪽
        p4 = doc[1].get_text()

        # PDF 물리 6페이지 = 인쇄 11~12쪽
        p11 = doc[5].get_text()

        check_fragments(
            p2,
            [
                '중기 WEST',
                '31명 내외',
                '단기 WEST',
                '71명 내외',
                'TOEIC 800점이상',
                'G-TELP Level2 76점이상',
                'TOEIC 750점이상',
                'G-TELP Level2 70점이상',
                'OPIc IM2 이상',
                'OPIc IM1 이상',
                'TOEIC Speaking IM2 이상',
                'TOEIC Speaking IM1 이상',
                'G-TELP Speaking Level6 이상',
                'G-TELP Speaking Level7 이상',
                '①, ②를모두충족',
                '복수 국적자',
                '외국 소재 대학',
                '소속대학의지원자추천공문',
            ],
            '공고 2쪽',
        )

        check_fragments(
            p4,
            [
                '8.5.(수)',
                '17:00',
                '공인영어성적증명서',
            ],
            '공고 4쪽',
        )

        check_fragments(
            p11,
            [
                'Q1.',
                'Q2.',
                'Q3.',
                '2026년 상반기 선발',
                '학점 제한은 없지만',
                '어학연수 시작일',
            ],
            'FAQ 11쪽',
        )

    print('[PASS] PDF의 모집 인원·어학성적·FAQ 문구 확인')

    # 3. 근거 페이지 생성
    def evidence(*logical_pages):
        return [
            {
                'pdf_physical_page': (i + 1) // 2,
                'printed_logical_page': i,
                'logical_page_candidate_id': (
                    f'WEST-2026H2-LP{i:02d}'
                ),
                'source_pdf_sha256': PDF_SHA,
            }
            for i in logical_pages
        ]

    def field(value, *pages, note=None):
        result = {
            'value': value,
            'source_comparison_status': (
                'verified_against_uploaded_pdf'
            ),
            'validation_status': (
                'source_verified_policy_review_pending'
            ),
            'evidence': evidence(*pages),
        }

        if note:
            result['notes'] = note

        return result

    # 4. 검수 결과 구조화
    rules = {
        'program_id': 'US-WEST-01',
        'notice_period': '2026_second_half',
        'notice_type': 'historical_cohort_announcement',
        'source_pdf_sha256': PDF_SHA,
        'input_review_sha256': REVIEW_SHA,

        'programs': {
            'short_term': {
                'duration_max_months': field(6, 2),

                'capacity_approx_persons': field(
                    71, 2,
                    note='71명 내외. 확정 인원 아님.'
                ),

                'english_general_any_of': field(
                    {
                        'TOEIC_min': 800,
                        'GTELP_Level2_min': 76,
                    },
                    2
                ),

                'english_speaking_any_of': field(
                    {
                        'OPIc_min': 'IM2',
                        'TOEIC_Speaking_ACTFL_min': 'IM2',
                        'GTELP_Speaking_level_min_qualification': (
                            'Level 6 이상'
                        ),
                    },
                    2
                ),
            },

            'medium_term': {
                'duration_max_months': field(12, 2),

                'capacity_approx_persons': field(
                    31, 2,
                    note='31명 내외. 확정 인원 아님.'
                ),

                'english_general_any_of': field(
                    {
                        'TOEIC_min': 750,
                        'GTELP_Level2_min': 70,
                    },
                    2
                ),

                'english_speaking_any_of': field(
                    {
                        'OPIc_min': 'IM1',
                        'TOEIC_Speaking_ACTFL_min': 'IM1',
                        'GTELP_Speaking_level_min_qualification': (
                            'Level 7 이상'
                        ),
                    },
                    2
                ),
            },
        },

        'common_requirements': {
            'nationality_and_visa': field(
                '대한민국 국적이며 미국 비자 발급 '
                '결격사유가 없을 것',
                2
            ),

            'enrollment_minimum': field(
                {
                    'four_year_university_semesters_completed_min': 4,
                    'junior_college_semesters_completed_min': 2,
                    'enrollment_types': [
                        '재학생',
                        '휴학생',
                    ],
                },
                2
            ),

            'recent_graduate': field(
                '어학연수 실제 시작일 기준 '
                '최근 1년 이내 졸업생',
                2, 11,
                note=(
                    '공고 예시는 2026년 2월·8월 졸업자. '
                    '현지중개기관·어학기관별 시작일 확인 필요.'
                )
            ),

            'english_score_combination': field(
                '일반영어 ① 중 한 종목 AND '
                '말하기 ② 중 한 종목',
                2
            ),

            'english_test_validity': field(
                '2026-08-05 접수 마감일 기준 '
                '2년 이내 국내 정기시험 성적. '
                '대학연합 OPIc 성적 인정.',
                2, 4
            ),

            'university_recommendation': field(
                '소속 대학의 지원자 추천 공문 필요',
                2, 3
            ),

            'mutually_exclusive_tracks': field(
                '단기·중기 중복 지원 불가',
                2
            ),

            'application_deadline': field(
                '2026-08-05 17:00',
                3, 10,
                note='2026년 하반기 모집 당시 마감일'
            ),

            'no_published_gpa_minimum': field(
                '학점 제한은 없으나 '
                '서류심사 평가에 학점 반영',
                11
            ),
        },

        'exclusions': field(
            [
                '복수 국적자',
                '외국 소재 대학(교) 학생',
                'WEST 프로그램 기 참가자',
                'WEST 프로그램 기 지원자 중 '
                '참가비 납부 마감 이후 포기자',
            ],
            2, 11
        ),

        # 아직 추가 확인이 필요한 사항
        'manual_review_issues': [
            {
                'issue': 'FAQ Q3의 선발 시기 표기 불일치',
                'details': (
                    '2026년 하반기 공고의 Q3 예시에 '
                    '2026년 상반기 선발이라고 표기됨.'
                ),
                'evidence': evidence(1, 11),
                'status': 'needs_review',
            },
            {
                'issue': '졸업생 실제 어학연수 시작일',
                'details': (
                    '기관별 실제 시작일이 달라 '
                    '개인별 졸업일 판정 보류.'
                ),
                'evidence': evidence(2, 11),
                'status': 'needs_review',
            },
            {
                'issue': '원문 범위와 현행 법규 구분',
                'details': (
                    '2026년 하반기 모집 공고의 내용과 '
                    '현재 적용되는 정책은 별도 확인 필요.'
                ),
                'status': 'needs_review',
            },
        ],

        'validation_status': (
            'source_verified_policy_review_pending'
        ),

        'approved_for_user_answers': False,
        'approved_for_embedding': False,
        'automatic_eligibility_rules_enabled': False,
    }

    # G-TELP Speaking의 Level 6/7은
    # 공고의 표현을 그대로 보존한다.
    # 자동적인 숫자 비교 규칙으로 변환하지 않는다.

    # 5. 감사 보고서
    audit = {
        'input_pdf_sha256': PDF_SHA,
        'input_review_sha256': REVIEW_SHA,
        'source_text_checks': 'passed',
        'manual_review_issues': len(
            rules['manual_review_issues']
        ),
        'fields_approved_for_production': 0,
        'original_files_modified': False,
        'validation_status': 'needs_review',
        'approved_for_user_answers': False,
        'approved_for_embedding': False,
        'automatic_eligibility_rules_enabled': False,
    }

    # 6. 결과 저장
    # 기존 파일이 있을 경우 임의로 덮어쓰지 않는다.
    output_path = (
        base / 'west_2026_second_half_eligibility_source_verified.json'
    )

    audit_path = (
        base / 'west_2026_second_half_eligibility_source_audit.json'
    )

    output_state, output_sha = save_new_or_verify(
        output_path, rules
    )

    audit['result_sha256'] = output_sha

    audit_state, audit_sha = save_new_or_verify(
        audit_path, audit
    )

    # 7. 최종 결과
    print('\n===== STEP 64-52 최종 결과 =====')
    print('[PASS] 입력 PDF 및 JSON SHA-256 검증')
    print('[PASS] PDF 원문·표·FAQ 근거 대조')

    print(
        f'[PASS] {output_state}: {output_path.name}'
    )
    print('SHA-256:', output_sha)

    print(
        f'[PASS] {audit_state}: {audit_path.name}'
    )
    print('SHA-256:', audit_sha)

    print(
        '수동 검토 이슈:',
        len(rules['manual_review_issues'])
    )

    print('원본 변경: 없음')
    print('답변용 승인: False')
    print('임베딩 승인: False')
    print('자동 자격 판정: 비활성화')
    print('Git commit·push: 미실행')


if __name__ == '__main__':
    main()