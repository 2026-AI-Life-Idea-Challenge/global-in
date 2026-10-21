
from pathlib import Path
from collections import Counter
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[5]

RAW = ROOT / "data/raw/usa/employment/west"
WEST = ROOT / "data/processed/usa/employment/west"
SHARED = ROOT / "data/processed/usa/shared"

PDF = RAW / "west_2026_first_half_notice.pdf"
QUEUE = SHARED / "usa_review_queue.jsonl"
PREVIOUS = WEST / "west_2026_first_half_reviewed_data.json"
FULL = WEST / "west_2026_first_half_full_review_data.json"
CHUNKS = WEST / "retrieval_chunks.jsonl"

OUTPUT = SHARED / "west_table_review_report.json"

EXPECTED = {
    PDF: "6f11ae189a6ec58bde63eb52c2e7eba80b6ec4ffde1f0620f1dca95200542c31",
    QUEUE: "b2fbb611dd05363060ac099355e7f1c11fdcbee602dd0d2130fcb964961b1241",
    PREVIOUS: "c26e6d1b8295709062fd2b1df142764375569ad5d9784145d3f12bf9b126c67d",
    FULL: "b3e781e89880996cc88a93a3618cc164794fdba9914ade9499111390bc108bc2",
    CHUNKS: "9b500df68439376d3d67d3a9245025b03881e34f69932962f8b5e6c18a8ab06c",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_verified(path):
    assert path.is_file(), f"파일 없음: {path}"
    raw = path.read_bytes()
    assert sha256(raw) == EXPECTED[path], (
        f"SHA-256 불일치: {path}"
    )
    return raw


def read_jsonl(raw):
    return [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]


def json_bytes(obj):
    return (
        json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


print("===== STEP 64-24 WEST 표 근거 검토 =====")

# 1. 기존 파일 검증
originals = {
    path: read_verified(path)
    for path in EXPECTED
}

queue = read_jsonl(originals[QUEUE])
chunks = read_jsonl(originals[CHUNKS])
previous = json.loads(originals[PREVIOUS])
full = json.loads(originals[FULL])

assert len(queue) == 201
assert len(chunks) == 29

assert previous["program_id"] == "US-WEST-01"
assert full["program_id"] == "US-WEST-01"

assert previous["automatic_eligibility_rules_enabled"] is False
assert full["automatic_eligibility_rules_enabled"] is False

print("[PASS] PDF·검토 대기열·검수 JSON 무결성")

# 2. WEST P0 청크 추출
p0 = [
    item for item in queue
    if item["review_priority"] == "P0_table_layout"
]

assert len(p0) == 7
assert all(
    item["program_id"] == "US-WEST-01"
    for item in p0
)

chunks_by_id = {
    item["chunk_id"]: item
    for item in chunks
}

assert len(chunks_by_id) == len(chunks)

review_items = []

with pymupdf.open(
    stream=originals[PDF],
    filetype="pdf",
) as doc:

    assert len(doc) == 11

    for item in p0:
        chunk_id = item["chunk_id"]

        assert chunk_id in chunks_by_id

        original = chunks_by_id[chunk_id]

        assert item["text"] == original["text"]
        assert item["text_sha256"] == (
            original["text_sha256"]
        )

        assert sha256(
            item["text"].encode("utf-8")
        ) == item["text_sha256"]

        page_number = item["physical_pdf_page"]
        side = item["side"]

        assert isinstance(page_number, int)
        assert 1 <= page_number <= 11
        assert side in ("left", "right")

        printed_page = (
            2 * page_number - 1
            if side == "left"
            else 2 * page_number
        )

        assert printed_page == (
            item["printed_page_candidate"]
        )

        page = doc[page_number - 1]
        half_width = page.rect.width / 2

        if side == "left":
            clip = pymupdf.Rect(
                0, 0, half_width, page.rect.height
            )
        else:
            clip = pymupdf.Rect(
                half_width, 0,
                page.rect.width, page.rect.height
            )

        pdf_side_text = page.get_text(
            "text", clip=clip, sort=True
        )

        assert pdf_side_text.strip(), (
            f"PDF 인쇄 페이지 텍스트 없음: {printed_page}"
        )

        review_items.append({
            "chunk_id": chunk_id,
            "program_id": "US-WEST-01",
            "printed_page": printed_page,
            "physical_pdf_page": page_number,
            "side": side,
            "source_pdf_sha256": EXPECTED[PDF],
            "chunk_text_sha256": item["text_sha256"],
            "chunk_preview": item["text"][:220],
            "pdf_side_text_sha256": sha256(
                pdf_side_text.encode("utf-8")
            ),
            "chunk_provenance_verified": True,
            "pdf_page_exists": True,
            "table_cell_alignment_verified_by_code": False,
            "human_semantic_review": "pending",
            "approved_for_user_answers": False,
            "approved_for_embedding": False,
        })

print("[PASS] WEST P0 청크 7개 원본·PDF 페이지 연결")

# 3. 검수된 단기·중기 재정지원금 대조
short_support = previous["short_term_financial_support"]
mid_support = full["mid_term_financial_support"]

assert short_support["base_participation_fee_usd"] == 7045
assert mid_support["participation_fee_usd"] == 8912

assert len(short_support["brackets"]) == 4
assert len(mid_support["brackets"]) == 4

support_summary = {}

for label, support, fee, printed_page in (
    ("short_term", short_support, 7045, 6),
    ("mid_term", mid_support, 8912, 7),
):
    rows = []

    for bracket in support["brackets"]:
        government = bracket["fee_government_usd"]
        self_payment = bracket["fee_self_usd"]

        assert government + self_payment == fee
        assert bracket["living_support_usd"] >= 0
        assert bracket[
            "maximum_total_support_1000krw"
        ] > 0

        rows.append({
            "label": bracket["label"],
            "fee_government_usd": government,
            "fee_self_usd": self_payment,
            "living_support_usd": (
                bracket["living_support_usd"]
            ),
            "maximum_total_support_1000krw": (
                bracket[
                    "maximum_total_support_1000krw"
                ]
            ),
        })

    support_summary[label] = {
        "printed_page": printed_page,
        "participation_fee_usd": fee,
        "brackets": rows,
        "fee_split_arithmetic": "pass",
        "source_document": (
            PDF.relative_to(ROOT).as_posix()
        ),
        "source_reviewed_json": (
            PREVIOUS.relative_to(ROOT).as_posix()
            if label == "short_term"
            else FULL.relative_to(ROOT).as_posix()
        ),
        "current_amounts_verified": False,
        "automatic_eligibility_rules_enabled": False,
    }

print("[PASS] 단기·중기 지원금 8개 구간 분담 합계")

# 4. 원본 보존형 검토 보고서
report = {
    "dataset_type": "west_table_review_report",
    "country": "US",
    "program_id": "US-WEST-01",
    "notice_period": "2026_first_half",
    "historical_notice": True,
    "source_pdf_sha256": EXPECTED[PDF],
    "review_queue_sha256": EXPECTED[QUEUE],
    "reviewed_data_sha256": EXPECTED[PREVIOUS],
    "full_review_data_sha256": EXPECTED[FULL],
    "retrieval_chunks_sha256": EXPECTED[CHUNKS],
    "p0_chunk_count": len(review_items),
    "p0_printed_pages": sorted({
        item["printed_page"]
        for item in review_items
    }),
    "p0_chunks": review_items,
    "financial_support": support_summary,
    "scope": (
        "P0 provenance and PDF page verification; "
        "previously reviewed financial table values "
        "are linked without approving raw PDF chunks."
    ),
    "table_cell_alignment_verified_by_code": False,
    "all_policy_claims_verified": False,
    "validation_status": "needs_review",
    "human_semantic_review_completed": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "database_loaded": False,
}

payload = json_bytes(report)

assert payload == json_bytes(report)
assert OUTPUT.parent.is_dir()
assert not OUTPUT.exists(), (
    f"기존 보고서 존재: {OUTPUT}"
)

# 5. 저장 및 검증
with OUTPUT.open("xb") as file:
    file.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == report

for path, raw in originals.items():
    assert path.read_bytes() == raw

print("[PASS] 보고서 저장·재읽기")
print("[PASS] 기존 원본 파일 불변")

print("\n[검토 대상 PDF 페이지]")
print(
    "인쇄 페이지:",
    report["p0_printed_pages"]
)

for item in review_items:
    print(
        item["chunk_id"],
        "| 페이지:", item["printed_page"],
        "| 원본 연결: PASS",
    )

print("\n===== STEP 64-24 최종 결과 =====")
print("P0 원본 청크:", len(review_items))
print("지원금 구간:", 8)
print("참가비 분담 합계: PASS")
print("PDF 원본·페이지 연결: PASS")
print("보고서:", OUTPUT.relative_to(ROOT))
print("SHA-256:", sha256(payload))
print("표 전체 셀 자동 검증: 미실행")
print("원본 청크 답변 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("원본 파일 변경: 없음")
print("Git 커밋·푸시: 미실행")