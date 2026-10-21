
from pathlib import Path
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_renewal_pdfs/001367009.pdf"
SOURCE = PROCESSED / "japan_employment_renewal_structured.json"
OUTPUT = PROCESSED / "japan_employment_renewal_tax_evidence.json"

EXPECTED_PDF_SHA = (
    "472a27d772b1649e61fb99a2ec569e8eb48ee8cc6811789160cf1160a17fa622"
)
EXPECTED_JSON_SHA = (
    "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def compact(text):
    return "".join(text.split())


def split_at_markers(text, markers):
    positions = [text.find(marker) for marker in markers]

    assert all(p >= 0 for p in positions), (
        f"구분자 누락: {markers}"
    )
    assert positions == sorted(positions), (
        f"구분자 순서 오류: {markers}"
    )
    assert len(set(positions)) == len(positions)

    introduction = text[:positions[0]].strip()
    segments = []

    for index, start in enumerate(positions):
        end = (
            positions[index + 1]
            if index + 1 < len(positions)
            else len(text)
        )
        segments.append(text[start:end].strip())

    assert compact(text) == compact(
        introduction + "".join(segments)
    ), "원문 분리 후 복원 실패"

    return introduction, segments


print("===== STEP 63-81 No.13 원천징수 증빙 구조화 =====")

# 1. 기존 파일 및 원본 무결성 검증
assert PDF_PATH.is_file(), "원본 PDF 누락"
assert SOURCE.is_file(), "기본 JSON 누락"
assert not OUTPUT.exists(), "출력 파일이 이미 존재합니다."

pdf_bytes = PDF_PATH.read_bytes()
source_bytes = SOURCE.read_bytes()

assert sha256(pdf_bytes) == EXPECTED_PDF_SHA
assert sha256(source_bytes) == EXPECTED_JSON_SHA

dataset = json.loads(source_bytes.decode("utf-8"))

assert dataset["route_id"] == "JP-EM"
assert dataset["application_type"] == "renewal"

parent = next(
    d for d in dataset["documents"]
    if d["row_number"] == 13
)

assert parent["document_id"] == "JP_EM_RENEWAL_DOC_013"
assert parent["page"] == 2

requirements = parent["category_requirements"]

assert requirements["3"]["symbol"] is None
assert requirements["4"]["symbol"] == "○"

scope_note = dataset["additional_submission_note_ja"]
assert "提出資料１３は不要" in compact(scope_note)
assert "転職後の初回の更新許可申請" in compact(scope_note)

# 2. PDF에서 No.13 본문 열만 추출
with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 2
    page = pdf[1]

    words = [
        w for w in page.get_text("words", sort=False)
        if 55 <= w[0] < 415
        and 576.34 <= (w[1] + w[3]) / 2 <= 716.02
    ]

    assert words, "No.13 본문 단어 누락"

    words.sort(key=lambda w: (w[5], w[6], w[7]))

    groups = {}

    for w in words:
        key = (w[5], w[6])
        groups.setdefault(key, []).append(w)

    lines = []

    for line_words in groups.values():
        line_words.sort(key=lambda w: w[0])
        lines.append("".join(w[4] for w in line_words))

    raw_text = "\n".join(lines).strip()

assert "法定調書合計表" in compact(raw_text)
assert "提出できない理由" in compact(raw_text)

# 3. 최상위 (1) / (2) 분기
intro, branches = split_at_markers(
    raw_text,
    ["（１）", "（２）"],
)

assert "いずれかの資料" in compact(intro)
assert "源泉徴収の免除" in compact(branches[0])
assert "免除証明書" in compact(branches[0])

# 4. (2) 안의 ア / イ 분리
# 일반 공백·전각 공백·탭을 모두 허용
import re

item_pattern = re.compile(
    r"(?m)^[ \t\u3000]+([アイ])(?=[^\r\n])"
)

matches = list(item_pattern.finditer(branches[1]))

assert [m.group(1) for m in matches] == ["ア", "イ"], (
    "No.13 ア/イ 구분자 확인 실패: "
    + repr(branches[1])
)

branch2_intro = branches[1][:matches[0].start()].strip()

second_level = [
    branches[1][matches[0].start():matches[1].start()].strip(),
    branches[1][matches[1].start():].strip(),
]

# 원문 누락·중복 확인
assert compact(branches[1]) == compact(
    branch2_intro + "".join(second_level)
)

print("ア/イ 분리: PASS")

assert "上記（１）を除く機関" in compact(branch2_intro)
assert "給与支払事務所等の開設届書" in compact(
    second_level[0]
)

# 5. イ 안의 （ア）/（イ） 선택지 분리
option_intro, nested_options = split_at_markers(
    second_level[1],
    ["（ア）", "（イ）"],
)

assert "次のいずれかの資料" in compact(option_intro)
assert "直近３か月分" in compact(nested_options[0])
assert "所得税徴収" in compact(nested_options[0])
assert "納期の特例" in compact(nested_options[1])
assert "承認" in compact(nested_options[1])

# 6. 계층형 JSON 생성
result = {
    "route_id": "JP-EM",
    "application_type": "renewal",
    "parent_document_id": "JP_EM_RENEWAL_DOC_013",
    "source_row_number": 13,
    "source_page": 2,
    "source_pdf_sha256": EXPECTED_PDF_SHA,
    "source_json_sha256": EXPECTED_JSON_SHA,
    "raw_body_text_ja": raw_text,
    "source_intro_ja": intro,
    "category_requirements": requirements,
    "applicability_scope": "additional_documents_after_job_change",
    "applicability_note_ja": scope_note,
    "branch_count": 2,
    "branches": [
        {
            "branch_id": "JP_EM_RENEWAL_DOC_013_BRANCH_01",
            "source_clause": "（１）",
            "branch_type": "withholding_tax_exempt_institution",
            "source_text_ja": branches[0],
            "validation_status": "needs_review",
        },
        {
            "branch_id": "JP_EM_RENEWAL_DOC_013_BRANCH_02",
            "source_clause": "（２）",
            "branch_type": "other_institution",
            "source_text_ja": branches[1],
            "source_intro_ja": branch2_intro,
            "components": [
                {
                    "source_clause": "ア",
                    "component_type": "payroll_office_notification",
                    "source_text_ja": second_level[0],
                },
                {
                    "source_clause": "イ",
                    "component_type": "tax_payment_evidence",
                    "source_text_ja": second_level[1],
                    "selection_type": "source_stated_alternatives",
                    "source_intro_ja": option_intro,
                    "options": [
                        {
                            "source_clause": "（ア）",
                            "source_text_ja": nested_options[0],
                        },
                        {
                            "source_clause": "（イ）",
                            "source_text_ja": nested_options[1],
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

# 7. 원문 및 항목 수 검증
assert len(result["branches"]) == 2
assert len(result["branches"][1]["components"]) == 2
assert len(
    result["branches"][1]["components"][1]["options"]
) == 2

assert compact(raw_text) == compact(
    intro + "".join(
        b["source_text_ja"] for b in result["branches"]
    )
)

# 8. 신규 JSON 저장 — 덮어쓰기 방지
output_bytes = json.dumps(
    result,
    ensure_ascii=False,
    indent=2,
).encode("utf-8")

with OUTPUT.open("xb") as f:
    f.write(output_bytes)

assert OUTPUT.read_bytes() == output_bytes
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == result

print("\n[구조화 결과]")
print("상위 분기:", len(result["branches"]), "개")
print("  (1) 원천징수 면제 기관")
print("  (2) 그 외 기관")
print("      ア 급여지급사무소 개설 신고")
print("      イ 세금 관련 자료")
print("          （ア） 최근 3개월분 계산서")
print("          （イ） 납기 특례 승인 증빙")

print("\n===== STEP 63-81 최종 결과 =====")
print("부모 서류: JP_EM_RENEWAL_DOC_013")
print("상위 분기: 2개")
print("하위 구성요소: 2개")
print("중첩 선택지: 2개")
print("원문 복원 검증: 성공")
print("Category 4 제출 표시: 확인")
print("Category 3 제외 관련 주석: 보존")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", sha256(output_bytes))
print("기존 PDF·JSON: 변경 없음")
print("자동 자격 판정: 비활성화")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")