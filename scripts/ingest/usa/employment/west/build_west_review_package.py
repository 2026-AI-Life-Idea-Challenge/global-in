
from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa/employment/west"
PROCESSED = ROOT / "data/processed/usa/employment/west"

PDF = RAW / "west_2026_first_half_notice.pdf"
LAYOUT = PROCESSED / "west_2026_first_half_layout_audit.json"
INVENTORY = PROCESSED / "west_2026_first_half_evidence_inventory.json"

OUTPUT = PROCESSED / "west_2026_first_half_review_package.json"
PREVIEW_DIR = RAW / "logical_page_previews"

EXPECTED = {
    PDF: "6f11ae189a6ec58bde63eb52c2e7eba80b6ec4ffde1f0620f1dca95200542c31",
    LAYOUT: "296bd49de37aaeb35525f4939078bea63900fae0633ad661c491c35255cd3043",
    INVENTORY: "0312dffcc92914630f8b597b70efdb7fbbffc3b2cc222ed7d312ebff01343cdd",
}

CATEGORIES = (
    "eligibility",
    "documents",
    "application",
    "cost_and_support",
    "program",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def serialize(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def short(text, length=180):
    return " ".join(text.split())[:length]


print("===== STEP 64-10 WEST 근거 검토 패키지 =====")

# 1. 입력 파일 무결성 검증
originals = {}

for path, expected_hash in EXPECTED.items():
    raw = path.read_bytes()
    assert sha256(raw) == expected_hash, (
        f"기존 파일 SHA-256 불일치: {path}"
    )
    originals[path] = raw

layout = json.loads(originals[LAYOUT].decode("utf-8"))
inventory = json.loads(originals[INVENTORY].decode("utf-8"))

assert layout["page_count"] == 11
assert inventory["physical_pdf_page_count"] == 11
assert inventory["logical_page_candidate_count"] == 22
assert inventory["source_block_count"] == 577
assert inventory["evidence_block_count"] == 241
assert inventory["source_layout_sha256"] == EXPECTED[LAYOUT]

print("[PASS] 원본 PDF / Layout / Inventory SHA-256")

# 2. 근거 블록의 원문 및 좌표를 Layout과 대조
page_by_number = {
    page["page"]: page
    for page in layout["pages"]
}

assert len(page_by_number) == 11

category_records = defaultdict(list)
seen_ids = set()

for item in inventory["evidence"]:
    evidence_id = item["evidence_id"]

    assert evidence_id not in seen_ids
    seen_ids.add(evidence_id)

    page_no = item["physical_pdf_page"]
    block_index = item["original_block_index"]
    page = page_by_number[page_no]

    original_block = page["blocks"][block_index]

    assert original_block["text"] == item["source_text"]
    assert original_block["bbox"] == item["bbox"]
    assert original_block["position"] == item["side"]

    side = item["side"]

    same_side = [
        (index, block)
        for index, block in enumerate(page["blocks"])
        if block["position"] == side
    ]

    same_side.sort(
        key=lambda pair: (
            pair[1]["bbox"][1],
            pair[1]["bbox"][0],
            pair[0],
        )
    )

    positions = [
        index for index, _ in same_side
    ]

    local_index = positions.index(block_index)

    previous_text = (
        same_side[local_index - 1][1]["text"]
        if local_index > 0
        else None
    )

    next_text = (
        same_side[local_index + 1][1]["text"]
        if local_index + 1 < len(same_side)
        else None
    )

    record = {
        "evidence_id": evidence_id,
        "physical_pdf_page": page_no,
        "logical_page_candidate": (
            item["logical_page_candidate"]
        ),
        "side": side,
        "bbox": item["bbox"],
        "source_text": item["source_text"],
        "previous_block_text": previous_text,
        "next_block_text": next_text,
        "matched_keywords": item["keyword_categories"],
        "semantic_relevance_verified": False,
        "table_cell_relationship_verified": False,
        "policy_interpretation_verified": False,
    }

    for category in item["keyword_categories"]:
        assert category in CATEGORIES
        category_records[category].append(record)

assert len(seen_ids) == 241

for category in CATEGORIES:
    expected_count = inventory[
        "evidence_category_counts"
    ].get(category, 0)

    assert len(category_records[category]) == expected_count

print("[PASS] 근거 241개 원문·좌표·주변 문맥 대조")

# 3. 논리 페이지 미리보기 22개 생성 준비
# 먼저 전체 결과를 메모리에서 생성한 뒤 저장
preview_files = []

with pymupdf.open(
    stream=originals[PDF],
    filetype="pdf",
) as doc:
    assert len(doc) == 11

    for index, page in enumerate(doc):
        half = page.rect.width / 2

        for side, rect in (
            (
                "left",
                pymupdf.Rect(
                    0, 0, half, page.rect.height
                ),
            ),
            (
                "right",
                pymupdf.Rect(
                    half, 0,
                    page.rect.width,
                    page.rect.height,
                ),
            ),
        ):
            logical_page = index * 2 + (
                1 if side == "left" else 2
            )

            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(1.5, 1.5),
                clip=rect,
                alpha=False,
            )

            filename = (
                f"logical_page_{logical_page:02d}.png"
            )

            preview_files.append({
                "logical_page_candidate": logical_page,
                "physical_pdf_page": index + 1,
                "side": side,
                "filename": filename,
                "content": pix.tobytes("png"),
            })

assert len(preview_files) == 22

print("[PASS] 좌우 인쇄 페이지 이미지 22개 생성")

# 4. JSON 구성
review_categories = {}

for category in CATEGORIES:
    review_categories[category] = {
        "candidate_count": len(category_records[category]),
        "records": category_records[category],
        "manual_review_required": True,
    }

result = {
    "dataset_type": "west_evidence_review_package",
    "program_id": "US-WEST-01",
    "notice_period": "2026_first_half",
    "source_pdf_sha256": EXPECTED[PDF],
    "source_layout_sha256": EXPECTED[LAYOUT],
    "source_inventory_sha256": EXPECTED[INVENTORY],
    "physical_pdf_page_count": 11,
    "logical_page_candidate_count": 22,
    "unique_evidence_block_count": 241,
    "category_assignment_count": sum(
        len(records)
        for records in category_records.values()
    ),
    "categories": review_categories,
    "preview_images": [
        {
            "logical_page_candidate": item[
                "logical_page_candidate"
            ],
            "physical_pdf_page": item[
                "physical_pdf_page"
            ],
            "side": item["side"],
            "path": (
                PREVIEW_DIR / item["filename"]
            ).relative_to(ROOT).as_posix(),
            "sha256": sha256(item["content"]),
        }
        for item in preview_files
    ],
    "semantic_relevance_verified": False,
    "table_cell_relationship_verified": False,
    "reading_order_verified": False,
    "validation_status": "needs_review",
    "automatic_eligibility_rules_enabled": False,
}

payload = serialize(result)
assert payload == serialize(result)

# 5. 기존 결과 덮어쓰기 방지
assert not OUTPUT.exists(), (
    "기존 검토 패키지가 있습니다. 덮어쓰지 않습니다."
)

assert not PREVIEW_DIR.exists() or not any(
    PREVIEW_DIR.iterdir()
), "기존 미리보기 파일이 있습니다."

PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

# 6. 저장 및 재검증
for item in preview_files:
    path = PREVIEW_DIR / item["filename"]

    with path.open("xb") as f:
        f.write(item["content"])

    assert sha256(path.read_bytes()) == sha256(
        item["content"]
    )

with OUTPUT.open("xb") as f:
    f.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == result

# 7. 원본 파일 불변 확인
for path, raw in originals.items():
    assert path.read_bytes() == raw

print("[PASS] 미리보기 22개 저장 및 SHA-256")
print("[PASS] 검토 JSON 저장·재읽기")
print("[PASS] 기존 PDF / Layout / Inventory 불변")

# 8. 결과 요약
print("\n[카테고리별 근거 후보]")

for category in CATEGORIES:
    records = category_records[category]

    print(f"\n{category}: {len(records)}개")

    for record in records[:2]:
        print(
            "  PDF", record["physical_pdf_page"],
            record["side"],
            "|", short(record["source_text"]),
        )

print("\n===== STEP 64-10 최종 결과 =====")
print("고유 근거 후보:", len(seen_ids))
print("유형별 분류 건수:", result["category_assignment_count"])
print("논리 페이지 이미지:", len(preview_files))
print("검토 JSON:", OUTPUT.relative_to(ROOT))
print("검토 JSON SHA-256:", sha256(payload))
print("원본 데이터 변경: 없음")
print("의미·표 관계 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")