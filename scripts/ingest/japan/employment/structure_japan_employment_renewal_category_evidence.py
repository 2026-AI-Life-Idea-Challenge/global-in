
from pathlib import Path
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_renewal_pdfs/001367009.pdf"
HASH_PATH = RAW / "japan_employment_renewal_pdf_hashes.json"
SOURCE = PROCESSED / "japan_employment_renewal_structured.json"

OUTPUT = (
    PROCESSED
    / "japan_employment_renewal_category_evidence.json"
)

EXPECTED_PDF_SHA = (
    "472a27d772b1649e61fb99a2ec569e8eb48ee8cc6811789160cf1160a17fa622"
)
EXPECTED_JSON_SHA = (
    "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef"
)

COLUMN_RANGES = {
    "1": (265.0, 330.0),
    "2": (330.0, 396.0),
    "3": (396.0, 461.0),
    "4": (461.0, 535.0),
}

Y_TOP = 270.94
Y_BOTTOM = 520.78

EXPECTED_COUNTS = {
    "1": 4,
    "2": 2,
    "3": 1,
    "4": 0,
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def compact(text):
    return "".join(text.split())


def extract_lines(words, left, right):
    selected = [
        w for w in words
        if left <= w[0] < right
        and Y_TOP <= (w[1] + w[3]) / 2 <= Y_BOTTOM
    ]

    selected.sort(key=lambda w: (w[5], w[6], w[7]))

    groups = {}

    for w in selected:
        key = (w[5], w[6])
        groups.setdefault(key, []).append(w)

    lines = []

    for line_words in groups.values():
        line_words.sort(key=lambda w: w[0])
        lines.append("".join(w[4] for w in line_words))

    return lines


def split_bullet_options(lines):
    options = []
    current = []

    for line in lines:
        if line.startswith("○"):
            if current:
                options.append("\n".join(current))
            current = [line[1:]]
        else:
            assert current, (
                "증빙 항목 시작 표시 ○ 없이 나타난 문장"
            )
            current.append(line)

    if current:
        options.append("\n".join(current))

    return options


print("===== STEP 63-78 No.4 증빙자료 구조화 =====")

# 1. 파일 보호 및 해시 검증
assert PDF_PATH.is_file()
assert HASH_PATH.is_file()
assert SOURCE.is_file()
assert not OUTPUT.exists(), (
    "출력 JSON이 이미 존재합니다. 덮어쓰지 않습니다."
)

pdf_bytes = PDF_PATH.read_bytes()
source_bytes = SOURCE.read_bytes()

assert sha256(pdf_bytes) == EXPECTED_PDF_SHA
assert sha256(source_bytes) == EXPECTED_JSON_SHA

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))
assert hash_data["application_type"] == "renewal"

assert any(
    item["filename"] == PDF_PATH.name
    and item["sha256"] == EXPECTED_PDF_SHA
    for item in hash_data["files"]
)

dataset = json.loads(source_bytes.decode("utf-8"))

assert dataset["route_id"] == "JP-EM"
assert dataset["application_type"] == "renewal"

parent = next(
    d for d in dataset["documents"]
    if d["row_number"] == 4
)

assert parent["document_id"] == "JP_EM_RENEWAL_DOC_004"

# 2. PDF의 각 열을 원문 그대로 추출
category_evidence = {}

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 2
    words = pdf[0].get_text("words", sort=False)

    for category, (left, right) in COLUMN_RANGES.items():
        lines = extract_lines(words, left, right)
        full_text = "\n".join(lines)

        if category in {"1", "2"}:
            texts = split_bullet_options(lines)
        elif category == "3":
            texts = [full_text] if full_text else []
        else:
            texts = []
            assert not full_text, (
                "Category 4에 예상하지 못한 문구 존재"
            )

        assert len(texts) == EXPECTED_COUNTS[category], (
            f"Category {category} 항목 수 불일치"
        )

        # 분리한 항목을 연결하면 원문과 같아야 함
        reconstructed = "".join(
            compact(text) for text in texts
        )
        assert reconstructed == compact(
            full_text.replace("○", "")
        ), f"Category {category} 원문 복원 실패"

        options = []

        for index, text in enumerate(texts, start=1):
            options.append({
                "option_id": (
                    f"JP_EM_RENEWAL_DOC_004"
                    f"_CAT{category}_OPT_{index:02d}"
                ),
                "source_text_ja": text,
                "validation_status": "needs_review",
            })

        category_evidence[category] = {
            "source_column": f"カテゴリー{category}",
            "source_text_ja": full_text,
            "option_count": len(options),
            "options": options,
            "no_separate_evidence_text": not bool(full_text),
            "validation_status": "needs_review",
        }

        print(
            f"Category {category}: "
            f"{len(options)}개 증빙, "
            f"원문 {len(full_text)}자"
        )

# 3. 핵심 문구 검사
assert "四季報" in compact(
    category_evidence["1"]["source_text_ja"]
)
assert "在留申請オンライン" in compact(
    category_evidence["2"]["source_text_ja"]
)
assert "法定調書合計表" in compact(
    category_evidence["3"]["source_text_ja"]
)
assert category_evidence["4"]["option_count"] == 0

# 4. 결과 JSON 작성
result = {
    "route_id": "JP-EM",
    "application_type": "renewal",
    "parent_document_id": "JP_EM_RENEWAL_DOC_004",
    "source_row_number": 4,
    "source_pdf_sha256": EXPECTED_PDF_SHA,
    "source_json_sha256": EXPECTED_JSON_SHA,
    "selection_type": "category_specific_evidence",
    "category_evidence": category_evidence,
    "category_4_interpretation": (
        "No separate evidence text in the source column; "
        "this does not establish a submission exemption."
    ),
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

assert sum(
    item["option_count"]
    for item in category_evidence.values()
) == 7

# OS별 줄바꿈 차이를 피하기 위해 UTF-8 LF로 저장
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

print("\n===== STEP 63-78 최종 결과 =====")
print("부모 서류: JP_EM_RENEWAL_DOC_004")
print("Category 1: 4개")
print("Category 2: 2개")
print("Category 3: 1개")
print("Category 4: 별도 증빙 문구 없음")
print("총 증빙 선택지: 7개")
print("원문 구간 검증: 성공")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", sha256(output_bytes))
print("기존 JSON 및 PDF: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")