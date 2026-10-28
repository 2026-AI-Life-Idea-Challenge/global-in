
from pathlib import Path
import hashlib
import json
import re
import os
import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"

SAFE_ROOT = (ROOT / "_local_backup").resolve()

DEFAULT_BASELINE = (
    SAFE_ROOT / "japan_employment_repro_baseline"
)

DEFAULT_OUTPUT = (
    SAFE_ROOT / "japan_employment_repro_education"
)

BASELINE = Path(
    os.environ.get(
        "JP_EM_COE_BASELINE_DIR",
        str(DEFAULT_BASELINE),
    )
).resolve()

OUTPUT_DIR = Path(
    os.environ.get(
        "JP_EM_COE_EDUCATION_OUTPUT_DIR",
        str(DEFAULT_OUTPUT),
    )
).resolve()

# 입력·출력 경로를 로컬 테스트 폴더로 제한
assert SAFE_ROOT in BASELINE.parents, (
    "입력 경로는 _local_backup 하위여야 합니다."
)

assert SAFE_ROOT in OUTPUT_DIR.parents, (
    "출력 경로는 _local_backup 하위여야 합니다."
)

assert BASELINE != OUTPUT_DIR, (
    "입력과 출력 폴더가 같을 수 없습니다."
)

FILENAME = "japan_employment_coe_category34_structured.json"

SOURCE = BASELINE / FILENAME
OUTPUT = OUTPUT_DIR / FILENAME
PDF = RAW / "japan_employment_coe_pdfs/001437254.pdf"
HASHES = RAW / "japan_employment_coe_pdf_hashes.json"

EXPECTED_BASELINE_SHA = (
    "dd0aebe3aed025e83f60e4907e60074eb7bdd37dfa7ceb1f8b6ffd85dcf52e00"
)

EXPECTED_FINAL_SHA = (
    "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text):
    return "".join(text.split())


print("===== STEP 63-38 학력·경력 증빙 재현성 검증 =====")

for path in [SOURCE, PDF, HASHES]:
    assert path.is_file(), f"파일 누락: {path}"

assert not OUTPUT.exists(), "테스트 파일이 이미 존재합니다"
assert sha256(SOURCE) == EXPECTED_BASELINE_SHA, (
    "기본 재생성 JSON SHA-256 불일치"
)

hash_data = json.loads(HASHES.read_text(encoding="utf-8"))

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF.name
)

pdf_hash = sha256(PDF)
assert pdf_hash == record["sha256"], "PDF SHA-256 불일치"

dataset = json.loads(SOURCE.read_text(encoding="utf-8"))

assert dataset["route_id"] == "JP-EM"
assert dataset["document_count"] == 8

# 1. 기본 재생성 JSON의 필드 순서를 최종본과 맞춤
for row in dataset["documents"]:
    assert "text_extraction_method" in row
    method = row.pop("text_extraction_method")

    assert method == "pdf_table_horizontal_boundaries"
    row["text_extraction_method"] = method

row8 = next(
    row for row in dataset["documents"]
    if row["document_id"] == "JP_EM_COE_DOC_008"
)

assert "education_evidence" not in row8

# 2. 최초 구조화 때와 같은 방식으로 원문 조항 분리
sections = {
    "resume": [],
    "alternatives_intro": [],
    "a": [],
    "b": [],
    "c": [],
    "d": [],
}

current = None
found_markers = []

for line in row8["raw_row_text_ja"].splitlines():
    stripped = line.strip()
    cleaned = re.sub(r"^8\s+", "", stripped)

    if cleaned.startswith("（１）"):
        current = "resume"
        found_markers.append("1")

    elif cleaned.startswith("（２）"):
        current = "alternatives_intro"
        found_markers.append("2")

    else:
        match = re.match(
            r"^([アイウエ])[\s　]+",
            cleaned,
        )

        if match:
            current = {
                "ア": "a",
                "イ": "b",
                "ウ": "c",
                "エ": "d",
            }[match.group(1)]
            found_markers.append(match.group(1))

    if current is not None:
        sections[current].append(cleaned)

assert found_markers == ["1", "2", "ア", "イ", "ウ", "エ"], (
    f"조항 구분 실패: {found_markers}"
)

texts = {
    key: "\n".join(lines).strip()
    for key, lines in sections.items()
}

checks = {
    "resume": ["履歴書"],
    "alternatives_intro": ["いずれか"],
    "a": ["卒業証明書", "DOEACC"],
    "b": ["在職証明書", "期間"],
    "c": ["情報処理", "５の資料"],
    "d": ["３年以上", "翻訳・通訳"],
}

for key, keywords in checks.items():
    for keyword in keywords:
        assert keyword in normalize(texts[key]), (
            f"{key}: {keyword} 누락"
        )

# 3. PDF 본문 열에서 경력 증빙 イ를 다시 추출
with pymupdf.open(PDF) as pdf:
    assert len(pdf) == 1

    body = pdf[0].get_text(
        "text",
        clip=pymupdf.Rect(100, 271.1, 370, 459.31),
        sort=True,
    )

start = re.search(
    r"(?m)^[ \t\u3000]*イ[ \t\u3000]+",
    body,
)
end = re.search(
    r"(?m)^[ \t\u3000]*ウ[ \t\u3000]+",
    body,
)

assert start is not None and end is not None
assert start.start() < end.start()

clean_work = body[start.start():end.start()].strip()

assert not re.search(r"[○●△□]", clean_work)

original_work = normalize(texts["b"])
assert original_work.count("○○□") == 1
assert original_work.replace("○○□", "", 1) == normalize(clean_work)

# 4. 학력·경력 증빙 상세 구조 재생성
evidence = {
    "resume": {
        "evidence_id": "JP_EM_COE_DOC_008_RESUME",
        "original_text_ja": texts["resume"],
        "role": "separate_document_group",
        "validation_status": "needs_review",
    },
    "alternative_group": {
        "group_id": "JP_EM_COE_DOC_008_ALTERNATIVES",
        "intro_original_ja": texts["alternatives_intro"],
        "source_relation": "いずれか",
        "application_note": (
            "공식 PDF의 대체 증빙 목록. "
            "각 조항의 적용 조건과 예외는 별도 판단 필요."
        ),
        "options": [
            {
                "evidence_id": "JP_EM_COE_DOC_008_A",
                "clause": "ア",
                "type": "education",
                "original_text_ja": texts["a"],
            },
            {
                "evidence_id": "JP_EM_COE_DOC_008_B",
                "clause": "イ",
                "type": "work_experience",
                "original_text_ja": texts["b"],
                "clean_text_ja": clean_work,
                "clean_text_source": {
                    "pdf_filename": PDF.name,
                    "page": 1,
                    "extraction_method": "body_column_clip",
                    "clip_rect": [100, 271.1, 370, 459.31],
                    "source_sha256": pdf_hash,
                },
                "text_cleaning_status": "needs_review",
            },
            {
                "evidence_id": "JP_EM_COE_DOC_008_C",
                "clause": "ウ",
                "type": "designated_it_exam_or_qualification",
                "original_text_ja": texts["c"],
                "exception_original_ja": (
                    "※５の資料を提出している場合は不要"
                ),
                "exception_target": "document_5",
                "exception_interpretation_status": "needs_review",
            },
            {
                "evidence_id": "JP_EM_COE_DOC_008_D",
                "clause": "エ",
                "type": "international_services_experience",
                "original_text_ja": texts["d"],
                "exception_original_ja": (
                    "大学を卒業した者が翻訳・通訳又は"
                    "語学の指導に従事する場合を除く"
                ),
                "exception_interpretation_status": "needs_review",
            },
        ],
        "validation_status": "needs_review",
    },
    "source_pdf": PDF.name,
    "source_sha256": pdf_hash,
    "validation_status": "needs_review",
}

# 예외 문구의 출처 확인
for option in evidence["alternative_group"]["options"]:
    exception = option.get("exception_original_ja")

    if exception:
        assert exception in normalize(option["original_text_ja"])

row8["education_evidence"] = evidence

# 5. 기존 최종 JSON의 Windows CRLF 형식 재현
json_text = json.dumps(
    dataset,
    ensure_ascii=False,
    indent=2,
)

encoded = json_text.replace("\n", "\r\n").encode("utf-8")
actual_sha = hashlib.sha256(encoded).hexdigest()

print("전체 제출서류:", len(dataset["documents"]))
print("이력서 증빙: 1개")
print("대체 증빙: 4개")
print("명시적 예외: 2개")
print("정제된 경력 증빙:", len(clean_work), "자")
print("표 기호 혼입: 없음")
print("PDF SHA-256: 일치")

print("\n[재현성 비교]")
print("재생성 SHA-256:", actual_sha)
print("기존 최종 SHA-256:", EXPECTED_FINAL_SHA)
print("바이트 단위 일치:", actual_sha == EXPECTED_FINAL_SHA)

# 비교 결과가 달라도 테스트 결과는 보존
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("xb") as f:
    f.write(encoded)

assert sha256(OUTPUT) == actual_sha

print("\n테스트 출력:", OUTPUT.relative_to(ROOT))
print("기존 processed JSON: 변경 없음")
print("정책 검증: needs_review")

assert actual_sha == EXPECTED_FINAL_SHA, (
    "재생성 파일의 SHA-256이 최종본과 다릅니다. "
    "테스트 파일은 보존되며 차이 분석이 필요합니다."
)

print("STEP 63-38 완전 재현성 검증: 성공")