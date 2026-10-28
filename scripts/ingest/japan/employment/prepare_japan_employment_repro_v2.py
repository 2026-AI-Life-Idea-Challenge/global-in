
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = ROOT / "scripts/ingest/japan/employment"

SOURCE = SCRIPT_DIR / "structure_japan_employment_coe_documents.py"
TARGET = SCRIPT_DIR / "structure_japan_employment_coe_documents_v2.py"

TEST_OUTPUT = (
    ROOT / "_local_backup/japan_employment_repro_baseline"
)

print("===== STEP 63-32 재생성 테스트 스크립트 준비 =====")

assert SOURCE.is_file(), "기존 생성 스크립트 누락"
assert not TARGET.exists(), "v2 스크립트가 이미 존재합니다"
assert not TEST_OUTPUT.exists(), (
    "재현성 테스트 출력 폴더가 이미 존재합니다"
)

source = SOURCE.read_text(encoding="utf-8")


def replace_once(text, old, new, label):
    count = text.count(old)
    assert count == 1, (
        f"{label} 교체 위치가 예상과 다릅니다: {count}개"
    )
    return text.replace(old, new, 1)


# 1. 출력 위치를 기존 processed 폴더와 분리
source = replace_once(
    source,
    'PROCESSED_DIR = ROOT / "data/processed/japan/employment"',
    (
        'PROCESSED_DIR = ROOT / '
        '"_local_backup/japan_employment_repro_baseline"'
    ),
    "테스트 출력 경로",
)

# 2. 공식 PDF에서 확인한 수평 경계 추가
source = replace_once(
    source,
    '"output": "japan_employment_coe_common_structured.json",',
    '''"output": "japan_employment_coe_common_structured.json",
        "row_boundaries": [
            153.0, 178.2, 256.68, 330.6,
            572.04, 632.76, 778.44,
        ],''',
    "공통 서류 경계",
)

source = replace_once(
    source,
    '"output": "japan_employment_coe_category34_structured.json",',
    '''"output": "japan_employment_coe_category34_structured.json",
        "row_boundaries": [
            141.5, 271.1, 459.31, 474.43,
            531.07, 563.35, 595.66, 627.94,
            773.64,
        ],''',
    "카테고리 3·4 서류 경계",
)

# 3. 기존의 서류 번호 중간점 계산을 실제 표 경계로 교체
start_marker = "            # 각 행의 구간은 인접한 서류 번호의"
end_marker = "            row_text = page.get_text("

assert source.count(start_marker) == 1
assert source.count(end_marker) == 1

start = source.index(start_marker)
end = source.index(end_marker, start)

new_block = '''            # PDF 표의 실제 수평 경계로 행 범위 지정
            boundaries = config["row_boundaries"]

            assert len(boundaries) == len(numbers) + 1

            upper = boundaries[index]
            lower = boundaries[index + 1]

            assert upper < row_y < lower, (
                f"서류 번호가 행 경계를 벗어났습니다: {number}"
            )

            clip = fitz.Rect(
                0, upper,
                page.rect.width, lower,
            )

'''

source = source[:start] + new_block + source[end:]

# 4. 원문 추출 방식 기록
source = replace_once(
    source,
    '"raw_row_text_ja": row_text,',
    '''"raw_row_text_ja": row_text,
                "text_extraction_method": "pdf_table_horizontal_boundaries",''',
    "원문 추출 방식",
)

# 5. 문법 검사 및 저장
ast.parse(source, filename=str(TARGET))

with TARGET.open("x", encoding="utf-8") as f:
    f.write(source)

assert TARGET.read_text(encoding="utf-8") == source

print("v2 스크립트:", TARGET.relative_to(ROOT))
print("PDF 행 경계: 적용")
print("추출 방식 메타데이터: 추가")
print("테스트 출력:", TEST_OUTPUT.relative_to(ROOT))
print("기존 생성 스크립트: 변경 없음")
print("기존 processed JSON: 변경 없음")
print("Python 문법 검사: 성공")
print("STEP 63-32 준비 완료")