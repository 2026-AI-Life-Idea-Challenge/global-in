
from pathlib import Path
from collections import Counter
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/usa/employment/west/2026_second_half"
OUT = ROOT / "data/processed/usa/employment/west/2026_second_half"

PDF = RAW / "west_2026_second_half_notice.pdf"
PAGES = OUT / "west_2026_second_half_pages.jsonl"
BLOCKS = OUT / "west_2026_second_half_blocks.jsonl"
EXTRACTION_REPORT = OUT / "west_2026_second_half_extraction_report.json"

PREVIEWS = OUT / "layout_previews"
REPORT = OUT / "west_2026_second_half_layout_audit.json"
QUEUE = OUT / "west_2026_second_half_manual_review_queue.jsonl"

EXPECTED = {
    PDF: "d04abdc458ad0a4a1f18196c9fdcb05f4ba39821183e0d77aaa5fa5f129a80e2",
    PAGES: "d968946d527bb670effe4af0d7d2e4baac782d261d22783fc193425cb5b69a7d",
    BLOCKS: "e5b8c5a1f222f5204b2cb6252ff5f57c884b635ef5691e901658319672a5cc5b",
    EXTRACTION_REPORT: "c0aafbf61172066cdd981faed71c8730e129d9aab92bb5d4ee57b2d90889afd1",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified(path):
    assert path.is_file(), f"파일 없음: {path}"
    data = path.read_bytes()
    assert digest(data) == EXPECTED[path], f"SHA-256 불일치: {path}"
    return data


def parse_jsonl(data):
    return [
        json.loads(line)
        for line in data.decode("utf-8").splitlines()
        if line.strip()
    ]


def encode_json(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def encode_jsonl(items):
    return "".join(
        json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n"
        for x in items
    ).encode("utf-8")


def save_immutable(path, data):
    if path.exists():
        assert path.read_bytes() == data, f"파일 충돌: {path}"
        return "EXISTS_VERIFIED"

    with path.open("xb") as f:
        f.write(data)

    assert path.read_bytes() == data
    return "CREATED"


print("===== STEP 64-38 하반기 WEST 페이지 구조 검사 =====")

pdf_raw = verified(PDF)
page_rows = parse_jsonl(verified(PAGES))
block_rows = parse_jsonl(verified(BLOCKS))
extraction = json.loads(verified(EXTRACTION_REPORT))

assert len(page_rows) == 11
assert len(block_rows) == 578
assert extraction["physical_pdf_pages"] == 11

pages_by_num = {
    p["physical_pdf_page"]: p for p in page_rows
}
blocks_by_page = {n: [] for n in range(1, 12)}

for block in block_rows:
    n = block["physical_pdf_page"]
    assert n in blocks_by_page

    assert digest(
        block["text"].encode("utf-8")
    ) == block["text_sha256"]

    blocks_by_page[n].append(block)

assert set(pages_by_num) == set(range(1, 12))

print("[PASS] PDF·페이지·블록·추출 보고서 무결성")

PREVIEWS.mkdir(parents=True, exist_ok=True)

layout_pages = []
manual_queue = []

with pymupdf.open(stream=pdf_raw, filetype="pdf") as doc:
    assert len(doc) == 11

    for i, page in enumerate(doc):
        n = i + 1
        info = pages_by_num[n]
        page_blocks = blocks_by_page[n]

        assert len(page_blocks) == info["text_block_count"]

        width = page.rect.width
        height = page.rect.height

        assert abs(width - info["page_width"]) < 0.1
        assert abs(height - info["page_height"]) < 0.1

        # 실제 PDF 원문과 STEP 64-37 추출 결과 대조
        text = page.get_text("text", sort=False)
        assert digest(
            text.encode("utf-8")
        ) == info["text_sha256"]

        # 페이지 중앙선을 기준으로 텍스트 분포를 조사.
        # 좌우 블록 분포만으로 2단 편집을 확정하지 않음.
        left = 0
        right = 0
        crossing = 0

        for block in page_blocks:
            x0, y0, x1, y1 = block["bbox"]

            assert 0 <= x0 <= x1 <= width + 2
            assert 0 <= y0 <= y1 <= height + 2

            if x1 < width / 2:
                left += 1
            elif x0 > width / 2:
                right += 1
            else:
                crossing += 1

        potential_two_column = (
            left >= 5 and right >= 5
            and (left + right) >= crossing
        )

        reasons = []

        if potential_two_column:
            reasons.append("possible_two_column_layout")

        if info["table_review_hint"]:
            reasons.append("table_or_policy_keyword_present")

        if info["faq_review_hint"]:
            reasons.append("faq_keyword_present")

        if info["text_length"] < 500:
            reasons.append("low_extracted_text_volume")

        # 사람이 원본 레이아웃을 확인하도록 PNG 생성
        image_path = PREVIEWS / f"page_{n:02d}.png"

        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(1.5, 1.5),
            alpha=False,
        )
        png_data = pix.tobytes("png")

        image_state = save_immutable(image_path, png_data)

        page_result = {
            "physical_pdf_page": n,
            "page_id": info["page_id"],
            "preview_path": image_path.relative_to(ROOT).as_posix(),
            "preview_sha256": digest(png_data),
            "image_state": image_state,
            "page_width": width,
            "page_height": height,
            "left_blocks": left,
            "right_blocks": right,
            "center_crossing_blocks": crossing,
            "possible_two_column_layout": potential_two_column,
            "text_length": info["text_length"],
            "review_reasons": reasons,
            "physical_to_logical_page_mapping_verified": False,
            "table_cell_alignment_verified": False,
            "reading_order_verified": False,
            "semantic_review_status": "needs_review",
        }
        # 실행 상태(CREATED/EXISTS_VERIFIED)는 데이터가 아닌
        # 콘솔 출력이므로 저장 결과에서는 제거
        page_result.pop("image_state")

        layout_pages.append(page_result)

        if reasons:
            manual_queue.append({
                "page_id": info["page_id"],
                "physical_pdf_page": n,
                "preview_path": page_result["preview_path"],
                "reasons": reasons,
                "source_pdf_sha256": EXPECTED[PDF],
                "review_status": "pending",
                "approved_for_user_answers": False,
                "approved_for_embedding": False,
            })

        print(
            f"[PAGE {n:02d}] "
            f"좌 {left} / 우 {right} / 중앙 {crossing} | "
            f"2단 후보 {potential_two_column} | "
            f"검토 사유 {len(reasons)}개"
        )

assert len(layout_pages) == 11

queue_bytes = encode_jsonl(manual_queue)

report = {
    "dataset_type": "west_2026_second_half_layout_audit",
    "source_pdf_sha256": EXPECTED[PDF],
    "source_pages_sha256": EXPECTED[PAGES],
    "source_blocks_sha256": EXPECTED[BLOCKS],
    "physical_pages": 11,
    "text_blocks": 578,
    "review_queue_count": len(manual_queue),
    "review_queue_sha256": digest(queue_bytes),
    "pages": layout_pages,
    "physical_to_logical_page_mapping_verified": False,
    "reading_order_verified": False,
    "table_cell_alignment_verified": False,
    "policy_semantics_verified": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

report_bytes = encode_json(report)

for path, payload in (
    (QUEUE, queue_bytes),
    (REPORT, report_bytes),
):
    state = save_immutable(path, payload)
    print(
        f"[PASS] {state}: {path.relative_to(ROOT)}"
    )
    print("SHA-256:", digest(payload))

assert parse_jsonl(QUEUE.read_bytes()) == manual_queue
assert json.loads(REPORT.read_text(encoding="utf-8")) == report

# 원본 파일은 아무것도 변경되지 않았는지 확인
for path, original_sha in EXPECTED.items():
    assert digest(path.read_bytes()) == original_sha

print("[PASS] 검토 자료 저장·원본 불변")

print("\n===== STEP 64-38 최종 결과 =====")
print("PDF 페이지:", len(layout_pages))
print("미리보기 PNG:", len(list(PREVIEWS.glob("page_*.png"))))
print("수동 검토 대상 페이지:", len(manual_queue))
print(
    "2단 배치 후보:",
    [
        p["physical_pdf_page"]
        for p in layout_pages
        if p["possible_two_column_layout"]
    ],
)
print("논리 페이지 매핑: 미완료")
print("표 셀 구조 확인: 미완료")
print("정책 의미 검증: 미완료")
print("답변·임베딩 승인: False")
print("Git 커밋·푸시: 미실행")