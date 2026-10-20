
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]

PROCESSED = ROOT / "data/processed/japan/employment"

SOURCE = (
    PROCESSED
    / "japan_employment_change_category34_structured.json"
)

OUTPUT = (
    PROCESSED
    / "japan_employment_change_education_evidence.json"
)

EXPECTED_SOURCE_SHA = (
    "489ae6144f2f52b8af26092ccd44713ec91220583ceb3640127bb2fbad2517d0"
)

print("===== STEP 63-58 No.8 학력·경력 증빙 구조화 =====")

# 1. 원본 데이터 보호 및 무결성 확인
assert SOURCE.is_file(), "변경 신청 JSON 누락"
assert not OUTPUT.exists(), "출력 파일이 이미 존재합니다."

source_bytes = SOURCE.read_bytes()
source_sha = hashlib.sha256(source_bytes).hexdigest()

assert source_sha == EXPECTED_SOURCE_SHA, (
    "원본 JSON SHA-256 불일치"
)

data = json.loads(source_bytes.decode("utf-8"))

assert data["route_id"] == "JP-EM"
assert data["application_type"] == "change"

doc = next(
    row for row in data["documents"]
    if row["row_number"] == 8
)

assert doc["document_id"] == "JP_EM_CHANGE_DOC_008"

raw = doc["raw_row_text_ja"]

# 2. 최상위 (1), (2) 구분
resume_marker = "（１）申請に係る"
alternatives_marker = "（２）学歴又は職歴等を証明する"

resume_start = raw.find(resume_marker)
alternatives_start = raw.find(alternatives_marker)

assert 0 <= resume_start < alternatives_start, (
    "(1) 이력서와 (2) 증빙 구간 구분 실패"
)

resume_text = raw[
    resume_start:alternatives_start
].strip()

alternatives_text = raw[alternatives_start:]

assert "履歴書" in resume_text

# 3. (2)의 ア・イ・ウ・エ 선택지 분리
# 각 선택지의 행 시작에 있는 가나 기호만 인식한다.
pattern = re.compile(
    r"(?m)^[ \t\u3000]*([アイウエ])[ \t\u3000]+"
)

matches = list(pattern.finditer(alternatives_text))

assert [m.group(1) for m in matches] == [
    "ア", "イ", "ウ", "エ"
], "학력·경력 증빙의 선택지 구조 불일치"

prefix = alternatives_text[:matches[0].start()].strip()

assert "次のいずれかの文書" in "".join(prefix.split())

option_types = {
    "ア": "education",
    "イ": "employment_history",
    "ウ": "it_exam_or_qualification",
    "エ": "international_services_experience",
}

expected_phrases = {
    "ア": ["卒業証明書", "DOEACC"],
    "イ": ["在職証明書", "期間"],
    "ウ": ["IT技術者", "情報処理", "※５"],
    "エ": ["外国の文化", "３年以上", "翻訳・通訳"],
}

options = []

for index, match in enumerate(matches):
    end = (
        matches[index + 1].start()
        if index + 1 < len(matches)
        else len(alternatives_text)
    )

    segment = alternatives_text[
        match.start():end
    ].strip()

    clause = match.group(1)
    normalized = "".join(segment.split())

    for phrase in expected_phrases[clause]:
        assert phrase in normalized, (
            f"{clause} 원문 핵심 문구 누락: {phrase}"
        )

    note_ja = None

    if clause == "ウ":
        note_marker = "※５の資料を提出している場合は不要"

        assert note_marker in normalized

        # 주석은 증빙 원문에도 남겨두고 별도 필드에 보존
        note_ja = (
            "※５の資料を提出している場合は不要"
        )

    options.append({
        "option_id": (
            f"JP_EM_CHANGE_DOC_008_OPT_{index + 1:02d}"
        ),
        "source_clause": clause,
        "evidence_type": option_types[clause],
        "evidence_text_ja": segment,
        "source_note_ja": note_ja,
        "validation_status": "needs_review",
    })

# 4. 조건을 검토 없이 자동 규칙으로 확정하지 않는다.
result = {
    "route_id": "JP-EM",
    "application_type": "change",
    "parent_document_id": "JP_EM_CHANGE_DOC_008",
    "source_row_number": 8,
    "source_json_sha256": source_sha,
    "resume_evidence": {
        "source_clause": "(1)",
        "evidence_text_ja": resume_text,
        "validation_status": "needs_review",
    },
    "alternative_evidence": {
        "source_clause": "(2)",
        "selection_type": "source_stated_alternatives",
        "source_intro_ja": prefix,
        "option_count": len(options),
        "options": options,
    },
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

assert len(options) == 4
assert len({o["option_id"] for o in options}) == 4

# 5. 출력 파일 신규 생성 — 덮어쓰기 금지
with OUTPUT.open("x", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2,
    )

saved = json.loads(
    OUTPUT.read_text(encoding="utf-8")
)

assert saved == result

output_sha = hashlib.sha256(
    OUTPUT.read_bytes()
).hexdigest()

print("\n[학력·경력 증빙 구조화 결과]")
print("(1) 이력서:", len(resume_text), "자")
print("(2) 대체 증빙 선택지:", len(options), "개")

for option in options:
    print(
        option["source_clause"],
        "|",
        option["evidence_type"],
        "|",
        len(option["evidence_text_ja"]),
        "자",
    )

print("\n===== STEP 63-58 최종 결과 =====")
print("부모 서류:", result["parent_document_id"])
print("(1) 이력서: 분리 성공")
print("(2) 선택지: 4개")
print("IT 자격 주석: 보존")
print("자동 자격 판정 규칙: 비활성화")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", output_sha)
print("기존 변경 신청 JSON: 변경 없음")
print("기존 COE JSON: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")