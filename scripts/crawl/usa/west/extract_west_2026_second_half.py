
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = (
    ROOT / "data/raw/usa/employment/west/2026_second_half"
)
OUT_DIR = (
    ROOT / "data/processed/usa/employment/west/2026_second_half"
)

PDF = RAW_DIR / "west_2026_second_half_notice.pdf"
PDF_MANIFEST = RAW_DIR / "pdf_verification_manifest.json"

PAGES_OUT = OUT_DIR / "west_2026_second_half_pages.jsonl"
BLOCKS_OUT = OUT_DIR / "west_2026_second_half_blocks.jsonl"
REPORT_OUT = OUT_DIR / "west_2026_second_half_extraction_report.json"

EXPECTED_PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

EXPECTED_MANIFEST_SHA = (
    "c708aeb7c04263262b32b650b5b4127"
    "fd856c5cc95db47aadc4cb952031014c3"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_verified(path, expected_sha):
    assert path.is_file(), f"필수 파일 없음: {path}"

    raw = path.read_bytes()
    actual = sha256(raw)

    assert actual == expected_sha, (
        f"SHA-256 불일치: {path}\n"
        f"예상: {expected_sha}\n"
        f"실제: {actual}"
    )
    return raw


def jsonl_bytes(rows):
    return "".join(
        json.dumps(
            row, ensure_ascii=False, sort_keys=True
        ) + "\n"
        for row in rows
    ).encode("utf-8")


def json_bytes(obj):
    return (
        json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def save_or_verify(path, data):
    if path.exists():
        assert path.read_bytes() == data, (
            f"기존 결과와 충돌: {path}\n"
            "자동으로 덮어쓰지 않았습니다."
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as f:
        f.write(data)

    assert path.read_bytes() == data
    return "CREATED"


print("===== STEP 64-37 하반기 WEST 원문 추출 =====")

# 1. 이전 단계 원본 검증
pdf_raw = read_verified(PDF, EXPECTED_PDF_SHA)
manifest_raw = read_verified(
    PDF_MANIFEST, EXPECTED_MANIFEST_SHA
)

manifest = json.loads(manifest_raw.decode("utf-8"))

assert manifest["pdf_sha256"] == EXPECTED_PDF_SHA
assert manifest["notice_period"] == "2026_second_half"

print("[PASS] STEP 64-36 PDF·Manifest 무결성")

# 2. PDF 물리 페이지별 추출
pages = []
blocks = []

with pymupdf.open(stream=pdf_raw, filetype="pdf") as doc:
    physical_pages = len(doc)
    assert physical_pages == 11

    for page_index, page in enumerate(doc):
        page_number = page_index + 1
        page_id = f"WEST-2026H2-P{page_number:02d}"

        # 읽기 순서를 추론하지 않고 원본 추출 순서 보존
        text = page.get_text("text", sort=False)

        raw_blocks = page.get_text("blocks", sort=False)

        page_blocks = []

        for original_index, block in enumerate(raw_blocks):
            # PyMuPDF 블록 형식:
            # x0,y0,x1,y1,text,block_no,block_type
            if len(block) < 7:
                continue

            x0, y0, x1, y1 = block[:4]
            block_text = block[4]
            block_type = block[6]

            # 0 = 텍스트 블록
            if block_type != 0:
                continue

            if not isinstance(block_text, str):
                continue

            if not block_text.strip():
                continue

            block_id = (
                f"{page_id}-B{original_index:04d}"
            )

            block_record = {
                "block_id": block_id,
                "page_id": page_id,
                "physical_pdf_page": page_number,
                "original_block_index": original_index,
                "bbox": [
                    round(float(x0), 2),
                    round(float(y0), 2),
                    round(float(x1), 2),
                    round(float(y1), 2),
                ],
                "text": block_text,
                "text_sha256": sha256(
                    block_text.encode("utf-8")
                ),
                "block_type": "text",
                "reading_order_verified": False,
                "table_cell_alignment_verified": False,
                "semantic_review_status": "needs_review",
                "approved_for_embedding": False,
                "approved_for_user_answers": False,
            }

            page_blocks.append(block_id)
            blocks.append(block_record)

        # 표와 FAQ 가능성을 찾는 것은 검토용 신호일 뿐
        # 실제 표의 셀 구조를 확정하지 않는다.
        table_hint = bool(
            re.search(
                r"지원구간|정부재정지원|어학성적|"
                r"지원자격|모집인원|지원금",
                text,
            )
        )

        faq_hint = bool(
            re.search(r"(?:FAQ|Q\d+\.|A\d+\.)", text)
        )

        page_record = {
            "page_id": page_id,
            "country": "US",
            "program_id": "US-WEST-01",
            "notice_period": "2026_second_half",
            "physical_pdf_page": page_number,
            "page_width": round(float(page.rect.width), 2),
            "page_height": round(float(page.rect.height), 2),
            "extracted_text": text,
            "text_sha256": sha256(
                text.encode("utf-8")
            ),
            "text_length": len(text),
            "text_block_count": len(page_blocks),
            "text_block_ids": page_blocks,
            "table_review_hint": table_hint,
            "faq_review_hint": faq_hint,
            "logical_page_mapping_verified": False,
            "reading_order_verified": False,
            "table_cell_alignment_verified": False,
            "source_pdf_sha256": EXPECTED_PDF_SHA,
            "semantic_review_status": "needs_review",
            "approved_for_embedding": False,
            "approved_for_user_answers": False,
            "automatic_eligibility_rules_enabled": False,
        }

        pages.append(page_record)

        print(
            f"[PAGE {page_number:02d}/{physical_pages}] "
            f"문자 {len(text):,}개 | "
            f"블록 {len(page_blocks)}개 | "
            f"표 검토 후보: {table_hint} | "
            f"FAQ 후보: {faq_hint}"
        )

assert len(pages) == 11
assert len({
    r["page_id"] for r in pages
}) == 11

assert len({
    r["block_id"] for r in blocks
}) == len(blocks)

print("[PASS] PDF 11개 물리 페이지 추출")

# 3. 기본 텍스트 검증
all_text = "\n".join(
    page["extracted_text"] for page in pages
)

assert "WEST" in all_text.upper()
assert "2026" in all_text
assert "하반기" in all_text

empty_pages = [
    p["physical_pdf_page"]
    for p in pages
    if not p["extracted_text"].strip()
]

table_candidate_pages = [
    p["physical_pdf_page"]
    for p in pages
    if p["table_review_hint"]
]

faq_candidate_pages = [
    p["physical_pdf_page"]
    for p in pages
    if p["faq_review_hint"]
]

# 4. 보고서 구성
page_bytes = jsonl_bytes(pages)
block_bytes = jsonl_bytes(blocks)

report = {
    "dataset_type": "west_pdf_extraction_report",
    "country": "US",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_path": PDF.relative_to(ROOT).as_posix(),
    "source_pdf_sha256": EXPECTED_PDF_SHA,
    "pdf_verification_manifest_sha256": (
        EXPECTED_MANIFEST_SHA
    ),
    "physical_pdf_pages": len(pages),
    "extracted_text_blocks": len(blocks),
    "extracted_characters": sum(
        p["text_length"] for p in pages
    ),
    "empty_pages": empty_pages,
    "table_candidate_pages": table_candidate_pages,
    "faq_candidate_pages": faq_candidate_pages,
    "pages_sha256": sha256(page_bytes),
    "blocks_sha256": sha256(block_bytes),
    "logical_page_mapping_verified": False,
    "reading_order_verified": False,
    "table_cell_alignment_verified": False,
    "semantic_review_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "note": (
        "Extraction preserves physical-page text "
        "and block coordinates. Detected table/FAQ "
        "hints do not verify semantic structure."
    ),
}

report_bytes = json_bytes(report)

# 5. 파일 저장
OUT_DIR.mkdir(parents=True, exist_ok=True)

planned = [
    (PAGES_OUT, page_bytes),
    (BLOCKS_OUT, block_bytes),
    (REPORT_OUT, report_bytes),
]

for path, data in planned:
    if path.exists():
        assert path.read_bytes() == data, (
            f"기존 파일 충돌: {path}"
        )

for path, data in planned:
    state = save_or_verify(path, data)

    print(
        f"[PASS] {state}: "
        f"{path.relative_to(ROOT)}"
    )
    print("SHA-256:", sha256(data))

# 6. 저장 후 재검증
saved_pages = [
    json.loads(line)
    for line in PAGES_OUT.read_text(
        encoding="utf-8"
    ).splitlines()
]

saved_blocks = [
    json.loads(line)
    for line in BLOCKS_OUT.read_text(
        encoding="utf-8"
    ).splitlines()
]

assert saved_pages == pages
assert saved_blocks == blocks

assert json.loads(
    REPORT_OUT.read_text(encoding="utf-8")
) == report

# 7. 기존 원본 불변 확인
assert sha256(PDF.read_bytes()) == EXPECTED_PDF_SHA
assert sha256(
    PDF_MANIFEST.read_bytes()
) == EXPECTED_MANIFEST_SHA

print("[PASS] 재읽기 및 기존 원본 불변")

print("\n===== STEP 64-37 최종 결과 =====")
print("물리 PDF 페이지:", len(pages))
print("텍스트 블록:", len(blocks))
print(
    "전체 추출 문자:",
    sum(p["text_length"] for p in pages)
)
print("빈 페이지:", empty_pages)
print("표 검토 후보 페이지:", table_candidate_pages)
print("FAQ 검토 후보 페이지:", faq_candidate_pages)
print("읽기 순서 검증: 미완료")
print("표 셀 구조 검증: 미완료")
print("정책 의미 검증: 미완료")
print("답변용 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("기존 상·하반기 원본 변경: 없음")
print("Git 커밋·푸시: 미실행")