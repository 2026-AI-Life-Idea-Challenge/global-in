
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
LAYOUT = OUT / "west_2026_second_half_layout_audit.json"

HALVES = OUT / "logical_page_previews"
CANDIDATES = OUT / "west_2026_second_half_logical_candidates.jsonl"
REPORT = OUT / "west_2026_second_half_logical_split_report.json"

EXPECTED = {
    PDF: "d04abdc458ad0a4a1f18196c9fdcb05f4ba39821183e0d77aaa5fa5f129a80e2",
    PAGES: "d968946d527bb670effe4af0d7d2e4baac782d261d22783fc193425cb5b69a7d",
    BLOCKS: "e5b8c5a1f222f5204b2cb6252ff5f57c884b635ef5691e901658319672a5cc5b",
    LAYOUT: "ead02ad262ae41373019e0b3481782c780814ce28e4db0ce3ce2a6062a82411f",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verified_read(path):
    assert path.is_file(), f"파일 없음: {path}"
    raw = path.read_bytes()
    assert sha256(raw) == EXPECTED[path], (
        f"SHA-256 불일치: {path}"
    )
    return raw


def parse_jsonl(raw):
    return [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]


def jsonl_bytes(rows):
    return "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
        for r in rows
    ).encode("utf-8")


def json_bytes(obj):
    return (
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def save_or_verify(path, raw):
    if path.exists():
        assert path.read_bytes() == raw, (
            f"기존 파일과 충돌: {path}"
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as f:
        f.write(raw)

    assert path.read_bytes() == raw
    return "CREATED"


print("===== STEP 64-39 하반기 WEST 좌우 페이지 분리 =====")

# 1. 기존 데이터 무결성 확인
pdf_raw = verified_read(PDF)
pages = parse_jsonl(verified_read(PAGES))
blocks = parse_jsonl(verified_read(BLOCKS))
layout = json.loads(verified_read(LAYOUT))

assert len(pages) == 11
assert len(blocks) == 578
assert layout["physical_pages"] == 11

page_by_number = {
    p["physical_pdf_page"]: p for p in pages
}

blocks_by_page = {
    n: [] for n in range(1, 12)
}

for block in blocks:
    n = block["physical_pdf_page"]
    assert n in blocks_by_page
    blocks_by_page[n].append(block)

print("[PASS] PDF·원본 청크·배치 보고서 검증")

# 2. 후보 논리 페이지 생성
HALVES.mkdir(parents=True, exist_ok=True)

candidates = []
all_assigned_block_ids = []
center_crossing_blocks = []

with pymupdf.open(stream=pdf_raw, filetype="pdf") as doc:
    assert len(doc) == 11

    for page_idx, page in enumerate(doc):
        physical_page = page_idx + 1
        mid_x = page.rect.width / 2

        original_blocks = blocks_by_page[physical_page]

        left_blocks = []
        right_blocks = []
        crossing = []

        for block in original_blocks:
            x0, _, x1, _ = block["bbox"]

            if x1 <= mid_x:
                left_blocks.append(block)
            elif x0 >= mid_x:
                right_blocks.append(block)
            else:
                crossing.append(block["block_id"])

        # 걸친 블록은 버리지 않고 보고서에 남김
        center_crossing_blocks.extend(crossing)

        for side, selected, clip in (
            (
                "L",
                left_blocks,
                pymupdf.Rect(
                    0, 0, mid_x, page.rect.height
                ),
            ),
            (
                "R",
                right_blocks,
                pymupdf.Rect(
                    mid_x, 0,
                    page.rect.width, page.rect.height
                ),
            ),
        ):
            logical_number_candidate = (
                (physical_page - 1) * 2
                + (1 if side == "L" else 2)
            )

            candidate_id = (
                f"WEST-2026H2-LP"
                f"{logical_number_candidate:02d}"
            )

            png_path = (
                HALVES / f"page_"
                f"{logical_number_candidate:02d}_{side}.png"
            )

            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                clip=clip,
                alpha=False,
            )

            png_raw = pix.tobytes("png")
            save_or_verify(png_path, png_raw)

            # 텍스트 순서를 새로 추론하지 않고
            # 원본 블록 인덱스 순서를 유지
            selected = sorted(
                selected,
                key=lambda b: b["original_block_index"]
            )

            selected_ids = [
                b["block_id"] for b in selected
            ]
            all_assigned_block_ids.extend(selected_ids)

            text = "\n".join(
                b["text"] for b in selected
            )

            candidate = {
                "candidate_id": candidate_id,
                "program_id": "US-WEST-01",
                "notice_period": "2026_second_half",
                "physical_pdf_page": physical_page,
                "side": side,
                "logical_page_number_candidate": (
                    logical_number_candidate
                ),
                "image_path": (
                    png_path.relative_to(ROOT).as_posix()
                ),
                "image_sha256": sha256(png_raw),
                "block_ids": selected_ids,
                "block_count": len(selected_ids),
                "text": text,
                "text_sha256": sha256(
                    text.encode("utf-8")
                ),
                "source_pdf_sha256": EXPECTED[PDF],
                "logical_page_mapping_verified": False,
                "reading_order_verified": False,
                "table_cell_alignment_verified": False,
                "semantic_review_status": "needs_review",
                "approved_for_user_answers": False,
                "approved_for_embedding": False,
                "automatic_eligibility_rules_enabled": False,
            }

            candidates.append(candidate)

        print(
            f"[PDF {physical_page:02d}] "
            f"왼쪽 {len(left_blocks)}블록 / "
            f"오른쪽 {len(right_blocks)}블록 / "
            f"중앙 걸침 {len(crossing)}블록"
        )

assert len(candidates) == 22

# 원본 텍스트 블록 578개 중 누락·중복 배정 여부 확인
assert len(set(all_assigned_block_ids)) == len(
    all_assigned_block_ids
)

unassigned = set(
    b["block_id"] for b in blocks
) - set(all_assigned_block_ids)

assert unassigned == set(center_crossing_blocks)

print("[PASS] 좌우 후보 22개 생성")
print("[PASS] 텍스트 블록 배정·누락 검사")

# 3. 결과 보고서
candidate_raw = jsonl_bytes(candidates)

report = {
    "dataset_type": "west_2026_h2_logical_split_candidates",
    "source_pdf_sha256": EXPECTED[PDF],
    "source_layout_sha256": EXPECTED[LAYOUT],
    "physical_pdf_pages": 11,
    "logical_page_candidates": len(candidates),
    "original_text_blocks": len(blocks),
    "assigned_text_blocks": len(all_assigned_block_ids),
    "center_crossing_block_ids": center_crossing_blocks,
    "unassigned_block_ids": sorted(unassigned),
    "candidate_file_sha256": sha256(candidate_raw),
    "logical_page_mapping_verified": False,
    "reading_order_verified": False,
    "table_cell_alignment_verified": False,
    "human_visual_review_status": "pending",
    "semantic_review_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

report_raw = json_bytes(report)

# 4. 저장
for path, raw in (
    (CANDIDATES, candidate_raw),
    (REPORT, report_raw),
):
    state = save_or_verify(path, raw)
    print(f"[PASS] {state}: {path.relative_to(ROOT)}")
    print("SHA-256:", sha256(raw))

assert parse_jsonl(CANDIDATES.read_bytes()) == candidates
assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == report

# 5. 원본 불변 확인
for path, expected in EXPECTED.items():
    assert sha256(path.read_bytes()) == expected

print("[PASS] 모든 기존 원본 불변")

print("\n===== STEP 64-39 최종 결과 =====")
print("물리 PDF 페이지:", 11)
print("좌우 논리 페이지 후보:", len(candidates))
print("원본 텍스트 블록:", len(blocks))
print("배정된 블록:", len(all_assigned_block_ids))
print("중앙 걸침 블록:", len(center_crossing_blocks))
print("미리보기 이미지:", len(candidates))
print("논리 페이지 최종 확정: False")
print("표 셀 구조 검증: False")
print("정책 의미 검증: 미완료")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")