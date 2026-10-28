
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

SOURCE = BASE / "japan_employment_renewal_structured.json"
OUTPUT = BASE / "japan_employment_renewal_dispatch_evidence.json"

EXPECTED_SOURCE_SHA = (
    "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def compact(text):
    return "".join(text.split())


print("===== STEP 63-79 No.5 파견근로 증빙 구조화 =====")

# 1. 기존 파일 보호
assert SOURCE.is_file(), "기본 renewal JSON 누락"
assert not OUTPUT.exists(), "출력 JSON이 이미 존재합니다."

source_bytes = SOURCE.read_bytes()

assert sha256(source_bytes) == EXPECTED_SOURCE_SHA, (
    "원본 JSON SHA-256 불일치"
)

dataset = json.loads(source_bytes.decode("utf-8"))

assert dataset["route_id"] == "JP-EM"
assert dataset["application_type"] == "renewal"

doc = next(
    d for d in dataset["documents"]
    if d["row_number"] == 5
)

assert doc["document_id"] == "JP_EM_RENEWAL_DOC_005"

assert all(
    doc["category_requirements"][c]["symbol"] == "△"
    for c in ("1", "2", "3", "4")
)

raw = doc["raw_row_text_ja"]

# 2. PDF의 표 기호는 보존하되,
#    증빙 본문을 분리할 때만 제거한다.
clean_lines = []

for line in raw.splitlines():
    # 원문 중간에 있는 △ 표 기호 열 제거
    cleaned = re.sub(r"(?:\s+△){4}\s*$", "", line)
    clean_lines.append(cleaned.rstrip())

clean_text = "\n".join(clean_lines).strip()

assert "△" not in clean_text, (
    "No.5 본문에 제출 기호가 남아 있습니다."
)

# 3. 최상위 (1), (2) 구분
marker_1 = "（１）申請人の派遣労働に関する誓約書"
marker_2 = "（２）申請人の派遣先での活動内容"

pos_1 = clean_text.find(marker_1)
pos_2 = clean_text.find(marker_2)

assert 0 <= pos_1 < pos_2, (
    "최상위 분기 위치 불일치"
)

condition_text = clean_text[:pos_1].strip()
pledge_text = clean_text[pos_1:pos_2].strip()
activity_text = clean_text[pos_2:].strip()

assert "派遣契約に基づいて就労する場合" in compact(
    condition_text
)

# 4. (1)의 서약서 2개 분리
pledge_a = "ア　所属機関（派遣元）用"
pledge_i = "イ　派遣先用"

assert pledge_a in pledge_text
assert pledge_i in pledge_text

pledge_items = [
    {
        "source_clause": "ア",
        "source_text_ja": pledge_a,
    },
    {
        "source_clause": "イ",
        "source_text_ja": pledge_i,
    },
]

# 5. (2)의 증빙 목록 5개 분리
expected_items = [
    ("ア", "労働条件通知書（雇用契約書）"),
    ("イ", "労働者派遣個別契約書"),
    ("ウ", "派遣元管理台帳"),
    ("エ", "派遣先管理台帳"),
    ("オ", "就業状況報告書"),
]

activity_items = []

for clause, phrase in expected_items:
    pattern = rf"(?m)^\s*{clause}\s+{re.escape(phrase)}\s*$"

    matches = list(re.finditer(pattern, activity_text))
    assert len(matches) == 1, (
        f"증빙 항목 검증 실패: {clause} {phrase}"
    )

    activity_items.append({
        "source_clause": clause,
        "source_text_ja": phrase,
    })

# (2)에 기재된 최근 재류기간 관련 주석 보존
note = "※直近の在留期間中の資料も提出してください。"

assert note in compact(activity_text)

# 6. 결과 JSON 구성
result = {
    "route_id": "JP-EM",
    "application_type": "renewal",
    "parent_document_id": "JP_EM_RENEWAL_DOC_005",
    "source_row_number": 5,
    "source_json_sha256": EXPECTED_SOURCE_SHA,
    "applicability_condition_ja": condition_text,
    "category_requirements": doc["category_requirements"],
    "pledge_documents": {
        "source_clause": "(1)",
        "source_text_ja": pledge_text,
        "item_count": len(pledge_items),
        "items": pledge_items,
    },
    "dispatch_activity_documents": {
        "source_clause": "(2)",
        "source_text_ja": activity_text,
        "source_note_ja": note,
        "item_count": len(activity_items),
        "items": activity_items,
        "selection_type": "source_listed_documents",
    },
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

assert len(pledge_items) == 2
assert len(activity_items) == 5

# 원문 보존 확인
for _, phrase in expected_items:
    assert phrase in compact(activity_text)

# 7. 신규 JSON 저장 — UTF-8 LF, 덮어쓰기 금지
output_bytes = json.dumps(
    result,
    ensure_ascii=False,
    indent=2,
).encode("utf-8")

with OUTPUT.open("xb") as f:
    f.write(output_bytes)

assert OUTPUT.read_bytes() == output_bytes
assert json.loads(OUTPUT.read_text(encoding="utf-8")) == result

print("\n[구조화 결과]")
print("적용 조건:", condition_text)
print("(1) 서약서 항목:", len(pledge_items))

for item in pledge_items:
    print(" ", item["source_clause"], item["source_text_ja"])

print("(2) 활동 관련 자료:", len(activity_items))

for item in activity_items:
    print(" ", item["source_clause"], item["source_text_ja"])

print("\n===== STEP 63-79 최종 결과 =====")
print("No.5 부모 서류 연결: 성공")
print("Category 1~4 △ 표시: 일치")
print("서약서: 2개")
print("활동 관련 증빙: 5개")
print("최근 재류기간 관련 주석: 보존")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", sha256(output_bytes))
print("원본 PDF·기존 JSON: 변경 없음")
print("자동 자격 판정: 비활성화")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")