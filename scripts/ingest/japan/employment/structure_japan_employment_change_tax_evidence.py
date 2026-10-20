
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]
PROCESSED = ROOT / "data/processed/japan/employment"

SOURCE = PROCESSED / "japan_employment_change_category34_structured.json"
OUTPUT = PROCESSED / "japan_employment_change_tax_evidence.json"

EXPECTED_SOURCE_SHA = (
    "489ae6144f2f52b8af26092ccd44713ec91220583ceb3640127bb2fbad2517d0"
)

print("===== STEP 63-59 No.14 원천징수 증빙 구조화 =====")

assert SOURCE.is_file(), "기존 변경 신청 JSON 누락"
assert not OUTPUT.exists(), "출력 파일이 이미 존재합니다. 덮어쓰지 않습니다."

source_bytes = SOURCE.read_bytes()
source_sha = hashlib.sha256(source_bytes).hexdigest()
assert source_sha == EXPECTED_SOURCE_SHA, "원본 JSON SHA-256 불일치"

source = json.loads(source_bytes.decode("utf-8"))
assert source["route_id"] == "JP-EM"
assert source["application_type"] == "change"

doc = next(
    d for d in source["documents"]
    if d["row_number"] == 14
)

assert doc["document_id"] == "JP_EM_CHANGE_DOC_014"

requirements = doc["category_requirements"]
assert requirements["3"]["symbol"] is None
assert requirements["4"]["symbol"] == "○"

raw = doc["raw_row_text_ja"]

def compact(text):
    return "".join(text.split())

def split_between(text, start, end=None):
    a = text.find(start)
    assert a >= 0, f"시작 표시 누락: {start}"
    if end is None:
        return text[a:].strip()
    b = text.find(end, a + len(start))
    assert b > a, f"종료 표시 누락: {end}"
    return text[a:b].strip()

# 1. 원문의 최상위 분기
m1 = "（１）源泉徴収の免除を受ける機関の場合"
m2 = "（２）上記（１）を除く機関の場合"

assert 0 <= raw.find(m1) < raw.find(m2)
intro = raw[:raw.find(m1)].strip()
branch1 = split_between(raw, m1, m2)
branch2 = split_between(raw, m2)

assert "法定調書合計表" in compact(intro)
assert "免除証明書" in compact(branch1)

# 2. (2)의 ア, イ 구분
a_marker = "ア 給与支払事務所等の開設届書の写し"
i_marker = "イ 次のいずれかの資料"

assert 0 <= branch2.find(a_marker) < branch2.find(i_marker)

branch2_intro = branch2[:branch2.find(a_marker)].strip()
a_text = split_between(branch2, a_marker, i_marker)
i_text = split_between(branch2, i_marker)

# 3. イ 안의 (ア), (イ) 선택지
sub_a = "（ア）直近３か月分"
sub_i = "（イ）納期の特例を受けている場合"

assert 0 <= i_text.find(sub_a) < i_text.find(sub_i)

i_intro = i_text[:i_text.find(sub_a)].strip()
sub_a_text = split_between(i_text, sub_a, sub_i)
sub_i_text = split_between(i_text, sub_i)

assert "次のいずれかの資料" in compact(i_intro)
assert "所得税徴収高計算書" in compact(sub_a_text)
assert "承認" in compact(sub_i_text)

# 4. 원문 분할이 누락 없이 복원되는지 확인
assert compact(raw) == compact(
    intro + branch1 + branch2_intro
    + a_text + i_intro + sub_a_text + sub_i_text
), "원문 구간 누락 또는 중복 발생"

result = {
    "route_id": "JP-EM",
    "application_type": "change",
    "parent_document_id": "JP_EM_CHANGE_DOC_014",
    "source_row_number": 14,
    "source_json_sha256": source_sha,
    "source_intro_ja": intro,
    "category_requirements": requirements,
    "branches": [
        {
            "branch_id": "JP_EM_CHANGE_DOC_014_BRANCH_01",
            "source_clause": "(1)",
            "condition_type": "withholding_exempt_institution",
            "source_text_ja": branch1,
            "validation_status": "needs_review",
        },
        {
            "branch_id": "JP_EM_CHANGE_DOC_014_BRANCH_02",
            "source_clause": "(2)",
            "condition_type": "other_institution",
            "source_intro_ja": branch2_intro,
            "items": [
                {
                    "source_clause": "ア",
                    "evidence_type": "payroll_office_notification",
                    "source_text_ja": a_text,
                },
                {
                    "source_clause": "イ",
                    "selection_type": "source_stated_alternatives",
                    "source_intro_ja": i_intro,
                    "options": [
                        {
                            "source_clause": "(ア)",
                            "evidence_type": "recent_tax_payment_statements",
                            "source_text_ja": sub_a_text,
                        },
                        {
                            "source_clause": "(イ)",
                            "evidence_type": "special_payment_deadline_approval",
                            "source_text_ja": sub_i_text,
                        },
                    ],
                },
            ],
            "validation_status": "needs_review",
        },
    ],
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

assert len(result["branches"]) == 2
assert len(result["branches"][1]["items"]) == 2
assert len(result["branches"][1]["items"][1]["options"]) == 2

# 5. 신규 JSON 저장 (기존 파일 덮어쓰기 금지)
with OUTPUT.open("x", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

saved = json.loads(OUTPUT.read_text(encoding="utf-8"))
assert saved == result

output_sha = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()

print("\n[구조화 결과]")
print("(1) 원천징수 면제 기관:", len(branch1), "자")
print("(2) 기타 기관:", len(branch2), "자")
print("(2)-ア 급여지급사무소 개설 신고:", len(a_text), "자")
print("(2)-イ 대체 증빙 선택지: 2개")
print("  (ア):", len(sub_a_text), "자")
print("  (イ):", len(sub_i_text), "자")

print("\n===== STEP 63-59 최종 결과 =====")
print("최상위 분기: 2개")
print("하위 대체 증빙: 2개")
print("원문 구간 복원 검증: 성공")
print("No.14 Category 3 미표시: 보존")
print("No.14 Category 4 ○: 보존")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", output_sha)
print("자동 자격 판정 규칙: 비활성화")
print("기존 변경 신청 JSON: 변경 없음")
print("기존 COE JSON: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")