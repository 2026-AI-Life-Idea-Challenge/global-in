# 보완 STEP 22. 자격요건과 제출서류 데이터 정합성 검증

import json
from pathlib import Path

# 현재 파일 기준 프로젝트 최상위 폴더
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 자격요건 JSON
RULES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "japan_working_holiday_rules.json"
)

# 제출서류 JSON
DOCUMENTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "japan_working_holiday_documents_structured.json"
)

# 두 파일 읽기
with open(RULES_PATH, "r", encoding="utf-8") as f:
    rules_data = json.load(f)

with open(DOCUMENTS_PATH, "r", encoding="utf-8") as f:
    documents_data = json.load(f)

# 상위 경로와 프로그램 ID가 동일한지 비교
route_matches = (
    rules_data.get("route_id")
    == documents_data.get("route_id")
)

program_matches = (
    rules_data.get("program_id")
    == documents_data.get("program_id")
)

# 두 데이터셋의 대상 국적 비교
nationality_matches = (
    rules_data.get("target_nationality")
    == documents_data.get("target_nationality")
)

# 자격요건 및 제출서류 개수
rule_count = len(rules_data.get("requirements", []))
document_count = len(documents_data.get("documents", []))

print("\n===== 보완 STEP 22: 데이터 정합성 검증 =====")

print("상위 경로 ID 일치:", route_matches)
print("프로그램 ID 일치:", program_matches)
print("대상 국적 일치:", nationality_matches)
print("자격요건 규칙 수:", rule_count)
print("제출서류 수:", document_count)

print(
    "전체 정합성 검증:",
    route_matches
    and program_matches
    and nationality_matches
    and rule_count == 11
    and document_count == 14
)