"""Dated rendered-page fingerprints; these are not legal approval or original-byte hashes."""
import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATE = '2026-10-28'

# Actual expanded Eligibility DOM observations (SHA-256 prefix, 64 bits).
# Normalization: remove UI Hide/Details lines and zero-width characters, collapse whitespace.
OBSERVED_TEXT = '''
subclass_186_direct_entry 303ec99c0ff3389b 3b5e44a1c6f94f82 13481329ef5fe046 62b61bc7f5c85518 303c4dcf944109fa 4430ce27cfac9afe d51532b59f7fdd04 a09587df1e9a3634 f606d42cca75979a 9be89d40c6687f58 913ad4d6e3fad4ec 5756dd1d3dce9b84
subclass_186_labour_agreement 5f6a0e5f06ca0bf7 13481329ef5fe046 f260fe82519317c4 6b90197765cf74b1 b575180737ba3ba9 d51532b59f7fdd04 a09587df1e9a3634 f606d42cca75979a 913ad4d6e3fad4ec 5756dd1d3dce9b84
subclass_186_trt d34fbb837cdf93ce 4b9f0c9fac436482 13481329ef5fe046 eaccf1f8a1b78a4d 496e2ad4c6d2861b a25ea702bb4386c9 f730a62a9c198c1d d51532b59f7fdd04 a09587df1e9a3634 d32fbb098dd8dee4 913ad4d6e3fad4ec 5756dd1d3dce9b84
subclass_189_points_tested 29f77fe321a57220 2407f7ce980e5a79 3c9968b6a264de81 fef089d53b370271 f1d369465d96c9c2 73e0264991bf0893 95968db7400a88ac 5f56cfaebc21168d e501f6a6edfff09c cac776cbf73434aa 5ac23bd1f741bdfa c35d6ab2b7d976d0
subclass_190 a27707643ba94b2c b47c54441038bb4b a6fc0c828657685d 3c9968b6a264de81 fef089d53b370271 f87fd638cbe783be 73e0264991bf0893 bc61bc5f5ec1a44e 5f56cfaebc21168d e501f6a6edfff09c cac776cbf73434aa b178c4d4f97c4aa8
subclass_191_regional_provisional c93926caa50a29e2 06fb502795a5a3a7 48413b85939ee914 64fad1aad359b542 66ac9ee2bee0da95 d318713d7340e48e 16139f04582c380f 70bf2db2745ce8ca
subclass_491 7c7d4b60da65c5bf 8626c5cad9847826 77db581907bf944a 0b0fa6e8d831722c 58d47674b2f24c13 584d6e4757d80396 12c8b7cf47b4bdc0 35b7f9790dd5818e e501f6a6edfff09c cac776cbf73434aa b178c4d4f97c4aa8
subclass_482_core_skills ac78485ef14a4a24 8812af85d9ca00b6 2367b4824868d5ef a919451ebee71ea4 967a7718752fda68 834bfaa148682636 0a39a23cce0c0e0e 557bcdac7e237e1c 49ffd62496e2b6ca 29a77e1d2224927d 8373ebe4de11bd53 eb749cc62650b0d9 1153930c01c6a0f0 c35d6ab2b7d976d0 6e04aba5cf774c3b 5996e73caf917e2d
subclass_482_specialist_skills ac78485ef14a4a24 8dc306a63711a71f 2367b4824868d5ef b94defdb673633d7 cb4975fdf0fef733 834bfaa148682636 9478375dd5b7d0c6 557bcdac7e237e1c 6cb745addfcc09c9 29a77e1d2224927d 8373ebe4de11bd53 eb749cc62650b0d9 1c0b3e564328b7ef c35d6ab2b7d976d0 6e04aba5cf774c3b 5996e73caf917e2d
subclass_482_labour_agreement cd722fb7348a6aa6 3c93fe8f5e4d3556 530ac07adb411efd 29e37a56b34f2a79 d12a48b2f70a7ebb 895154f201c1c66a 0c124b783b3ccfce e1410a35352769f3 48d46b3957338421 5756dd1d3dce9b84
subclass_494_employer_sponsored 558a931084737213 78f68b500d76d649 5cf8e2ebbe487ad0 e1a956a716bd48c0 47cc6d8ec6f7d74a 0fda7551e3293309 b39645098c551d33 48d46b3957338421 6931141663070a8c
subclass_494_labour_agreement cd722fb7348a6aa6 75a7c21b9445ba87 87012c8bccbfbc17 e7edda7926df1233 7615132a10323def 0fda7551e3293309 b4015fbe3121cff7 48d46b3957338421 6931141663070a8c
subclass_407 001db1935ce96fa9 da86379918e40a8a 172d724de126d0d8 c67bc44ae2b88928 29e37a56b34f2a79 6b6e59451c06828a 50c4f5526e4ab9f3 c19f2a6df9762f94 04a8d3591e0b18ee d32fbb098dd8dee4 0685d579e986b9f8 000b0106d6ceb788 a6c758e0ba193cb7
subclass_500 0da169f52a3ba819 6030cfb081c2e16f c43831bfaca19fe4 92197346fa4b7f0d 905de70194e94c6f d25c3f7534532269 66c6596d66200dad ce27fbb738a36265 10e4b6442476b240 c8321081f4f8a75c 501818cbd2705ac1 43fa0f989ee45be4 d32fbb098dd8dee4 0685d579e986b9f8 2d4e9ecc9bce8bc6 a6c758e0ba193cb7
subclass_417_first 573f618838d49773 835bd9aa5403c1c1 e80906fb64c7276a d97c037c8a986f6e c912cd0d1feaef2f 417a1ec1ffdeda5a 4dffa0439f7a046a 000b0106d6ceb788 9a03d623d4217f63
subclass_417_second 8a636193da93e816 3f27423bc21da2bb f99d246e300c870c be57cfb99e1bff5b 21fac40a68e2852b c912cd0d1feaef2f 417a1ec1ffdeda5a 4dffa0439f7a046a 000b0106d6ceb788 9a03d623d4217f63
subclass_417_third 8a636193da93e816 3f5a6edc753761f2 c87a27ca56e5a29c 72596ef7785b69d5 835bd9aa5403c1c1 c912cd0d1feaef2f 417a1ec1ffdeda5a 4dffa0439f7a046a 000b0106d6ceb788 9a03d623d4217f63
subclass_462_first 48363d6887e81a90 7a989fe3bd7baa7a 14e1598d4a050630 6275e3b4028f03b1 3dced11974e3162b 26f104e0256d8533 ae30f9dbe4af5667 c912cd0d1feaef2f 417a1ec1ffdeda5a 4dffa0439f7a046a dedc7ea1ebdcd252 9a03d623d4217f63
subclass_462_second 68908a32fb814b16 25342c4d479829d6 c87a27ca56e5a29c db40d66e5c026354 7a989fe3bd7baa7a c912cd0d1feaef2f 417a1ec1ffdeda5a 4dffa0439f7a046a 000b0106d6ceb788
subclass_462_third 68908a32fb814b16 b2a2cda8a335941d c87a27ca56e5a29c c93266d17951cd61 7a989fe3bd7baa7a c912cd0d1feaef2f 417a1ec1ffdeda5a 4dffa0439f7a046a 000b0106d6ceb788
'''
OBSERVED = {parts[0]: parts[1:] for line in OBSERVED_TEXT.strip().splitlines() if (parts := line.split())}

# Browser independently split/joined the current visible sections and reproduced these hashes.
BOUNDARIES = {
    'AU_186_TRT_POL_04': ('0e6116df07277006', 'split_current_nomination_section', ['eaccf1f8a1b78a4d']),
    'AU_186_TRT_POL_05': ('49899b6d32b5bd8c', 'split_current_nomination_section', ['eaccf1f8a1b78a4d']),
    'AU_191_REGIONAL_PROVISIONAL_POL_02': ('dc18968a6e9a0f2c', 'join_current_income_and_compliance', ['06fb502795a5a3a7', '48413b85939ee914']),
    'AU_191_REGIONAL_PROVISIONAL_POL_06': ('4f0b7e4c8ff9b2d3', 'join_current_debt_and_immigration_history', ['16139f04582c380f', '70bf2db2745ce8ca']),
    'AU_482_SPECIALIST_POL_12': ('d210ad1c8f3cade4', 'join_current_sponsorship_and_english', ['eb749cc62650b0d9', '1c0b3e564328b7ef']),
    'AU_482_SPECIALIST_POL_15': ('6deb868c5e9c079a', 'current_values_plus_old_navigation_footer', ['5996e73caf917e2d']),
}
MISSING_189 = {
    'AU_189_PT_POL_01': ('29f77fe321a57220', '호주 내 신청 시 보유 비자 요건 및 491/494 이력의 최소 보유기간 조건을 별도 검토한다.'),
    'AU_189_PT_POL_02': ('2407f7ce980e5a79', 'EOI 제출과 비자 신청을 구분하며 초청을 받아야 신청할 수 있다.'),
    'AU_189_PT_POL_03': ('3c9968b6a264de81', '기술심사 요건·심사 유효기간·Thapa 판결 관련 초청 후 취득 안내 및 직종별 대안을 함께 검토한다.'),
    'AU_189_PT_POL_04': ('fef089d53b370271', '45세 미만 여부는 초청 시점 기준이며 초청 후 45세가 되는 경우와 구분한다.'),
}


def fingerprint(text):
    text = re.sub(r'^(Hide|Details)[ \t\u00a0]*$', '', text, flags=re.M)
    text = ' '.join(re.sub('[\u200b\u200c\u200d\ufeff]', '', text).split())
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def attach_official_review(record):
    program = record['program']
    if program not in OBSERVED:
        raise ValueError(f'Unobserved program: {program}')
    sources = record.get('official_sources') or record.get('source_tabs') or {}
    source = sources.get('eligibility') or next(iter(sources.values()), {})
    source_url = source.get('source_url') or source.get('url') or record.get('source_url')
    if not source_url:
        raise ValueError(f'Missing source URL: {program}')
    for policy in record.get('policy_candidates', []):
        if policy.get('legal_validation_approved') or policy.get('approved_for_eligibility_decision'):
            raise ValueError('Refuse to overwrite approved policy')
        pid, digest = policy['policy_id'], fingerprint(policy.get('source_text') or '')
        review = {'reviewed_at': DATE, 'source_url': source_url,
                  'comparison_method': 'expanded_eligibility_DOM_normalized_SHA256_prefix_64bit',
                  'local_text_fingerprint': digest, 'legal_validation_completed': False,
                  'pending_items': ['현행 법령·위임명령·예외·적용 범위 확인'],
                  'source_snapshot_replaced': False}
        if digest in OBSERVED[program]:
            review['status'] = 'normalized_section_fingerprint_match'
        elif pid in BOUNDARIES and digest == BOUNDARIES[pid][0]:
            _, method, hashes = BOUNDARIES[pid]
            assert all(h in OBSERVED[program] for h in hashes)
            review.update(status='section_boundary_or_navigation_difference_verified', boundary_method=method, current_section_fingerprints=hashes)
        elif pid in MISSING_189 and len((policy.get('source_text') or '').splitlines()) == 1:
            current_hash, summary = MISSING_189[pid]
            assert current_hash in OBSERVED[program]
            review.update(status='archived_detail_missing_live_summary_added', current_section_fingerprint=current_hash,
                          reviewed_policy_text=summary, text_kind='reviewer_summary_not_source_quote')
            review['pending_items'].append('현재 세부 본문의 정식 원문 보관·Evidence 연결 보강')
        else:
            review['status'] = 'changed_source_requires_new_review'
        policy['official_review'] = review
    record['official_review_summary'] = {'reviewed_at': DATE, 'policy_count': len(record['policy_candidates']),
        'observed_live_section_count': len(OBSERVED[program]), 'legal_validation_completed_count': 0}
    return record


def strip_review(record):
    value = deepcopy(record)
    value.pop('official_review_summary', None)
    for policy in value.get('policy_candidates', []):
        policy.pop('official_review', None)
    return value


def refresh_reviews(check=False, programs=None):
    prepared = []
    for path in sorted((ROOT / 'data/processed/australia').rglob('*_evidence_draft.json')):
        old = json.loads(path.read_text(encoding='utf-8-sig'))
        if programs is not None and old.get('program') not in programs:
            continue
        new = attach_official_review(deepcopy(old))
        assert strip_review(new) == strip_review(old)
        assert attach_official_review(deepcopy(new)) == new
        prepared.append((path, old, new))
    counts = Counter()
    rows = []
    for path, old, new in prepared:
        if check:
            assert old == new, f'Missing or stale review: {path}'
        elif old != new:
            path.write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for p in new['policy_candidates']:
            counts[p['official_review']['status']] += 1
            rows.append({'policy_id': p['policy_id'], 'program': new['program'], **p['official_review']})
    if not check and programs is None:
        target = ROOT / 'docs/legal_review/australia_policy_review_20261028.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({'reviewed_at': DATE, 'program_count': len(prepared), 'policy_count': len(rows),
            'observed_section_fingerprints': OBSERVED, 'summary': dict(counts), 'legal_validation_completed': 0,
            'limitation': '64-bit normalized section fingerprints; not raw-page hashes or legal approval',
            'database_applied': False, 'policy_reviews': rows}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'AU {"CHECK" if check else "APPLIED"}: {len(prepared)} files, {len(rows)} policies; {dict(counts)}')
