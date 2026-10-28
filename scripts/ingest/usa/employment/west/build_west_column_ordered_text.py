
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]

WEST = ROOT / "data/processed/usa/employment/west"

LAYOUT = WEST / "west_2026_first_half_layout_audit.json"
SOURCE = WEST / "west_2026_first_half_notice_text.json"
OUTPUT = WEST / "west_2026_first_half_column_candidate.json"

EXPECTED_LAYOUT_SHA = (
    "296bd49de37aaeb35525f4939078bea"
    "63900fae0633ad661c491c35255cd3043"
)

EXPECTED_SOURCE_SHA = (
    "32c1889fc24e19b39ae3cbbde9a254"
    "230b6d70dbe320a146d6f49a91acb2bf68"
)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def normalize(text):
    return " ".join(text.split())


def serialize(data):
    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")


def build_candidate(layout):
    pages = []
    total_original = 0
    total_reordered = 0

    for page in layout["pages"]:
        original_blocks = page["blocks"]
        page_no = page["page"]

        left = []
        right = []
        unassigned = []

        for index, block in enumerate(original_blocks):
            item = {
                "original_block_index": index,
                "bbox": block["bbox"],
                "text": block["text"],
            }

            if block["position"] == "left":
                left.append(item)
            elif block["position"] == "right":
                right.append(item)
            else:
                unassigned.append(item)

        # 블록의 세로 위치를 우선하고
        # 같은 높이에서는 가로 위치를 기준으로 정렬
        def sort_key(item):
            x0, y0, _, _ = item["bbox"]
            return (round(y0, 2), round(x0, 2))

        left.sort(key=sort_key)
        right.sort(key=sort_key)
        unassigned.sort(key=sort_key)

        # 좌측을 먼저, 우측을 다음에 배치한 후보
        ordered = left + right + unassigned

        original_ids = Counter(
            range(len(original_blocks))
        )

        ordered_ids = Counter(
            item["original_block_index"]
            for item in ordered
        )

        assert original_ids == ordered_ids, (
            f"{page_no}페이지 블록 누락 또는 중복"
        )

        assert len(left) == page["left_block_count"]
        assert len(right) == page["right_block_count"]
        assert len(unassigned) == (
            page["cross_center_block_count"]
        )

        left_text = "\n\n".join(
            item["text"].strip()
            for item in left
            if item["text"].strip()
        )

        right_text = "\n\n".join(
            item["text"].strip()
            for item in right
            if item["text"].strip()
        )

        unassigned_text = "\n\n".join(
            item["text"].strip()
            for item in unassigned
            if item["text"].strip()
        )

        ordered_text = "\n\n".join(
            text
            for text in [
                left_text,
                right_text,
                unassigned_text,
            ]
            if text
        )

        # 원본 블록의 텍스트가 순서 변경 외에
        # 삭제되거나 추가되지 않았는지 검사
        original_content = Counter(
            block["text"] for block in original_blocks
        )

        reordered_content = Counter(
            item["text"] for item in ordered
        )

        assert original_content == reordered_content

        pages.append({
            "page": page_no,
            "original_block_count": len(original_blocks),
            "ordered_block_count": len(ordered),
            "left_block_count": len(left),
            "right_block_count": len(right),
            "unassigned_block_count": len(unassigned),
            "left_text": left_text,
            "right_text": right_text,
            "unassigned_text": unassigned_text,
            "candidate_reading_text": ordered_text,
            "reading_order_verified": False,
            "table_structure_verified": False,
        })

        total_original += len(original_blocks)
        total_reordered += len(ordered)

    assert total_original == total_reordered == 577

    return {
        "dataset_type": "pdf_column_order_candidate",
        "program_id": "US-WEST-01",
        "source_layout_sha256": EXPECTED_LAYOUT_SHA,
        "source_text_json_sha256": EXPECTED_SOURCE_SHA,
        "page_count": len(pages),
        "original_block_count": total_original,
        "reordered_block_count": total_reordered,
        "reading_order_method": (
            "left_column_then_right_column"
        ),
        "reading_order_verified": False,
        "table_structure_verified": False,
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
        "pages": pages,
    }


print("===== STEP 64-08 WEST 좌우 읽기 순서 분석 =====")

# 1. 원본 무결성 검증
layout_raw = LAYOUT.read_bytes()
source_raw = SOURCE.read_bytes()

assert sha256(layout_raw) == EXPECTED_LAYOUT_SHA
assert sha256(source_raw) == EXPECTED_SOURCE_SHA

layout = json.loads(layout_raw.decode("utf-8"))
source = json.loads(source_raw.decode("utf-8"))

assert layout["page_count"] == 11
assert len(layout["pages"]) == 11
assert source["page_count"] == 11

assert layout["source_text_json_sha256"] == (
    EXPECTED_SOURCE_SHA
)

print("[PASS] 원본 Layout / Text JSON SHA-256")

# 2. 전체 페이지 읽기 순서 후보 구성
result = build_candidate(layout)

assert result["page_count"] == 11
assert result["original_block_count"] == 577
assert result["reordered_block_count"] == 577

print("[PASS] 11페이지 블록 재정렬")
print("[PASS] 577개 블록 누락·중복 없음")

# 3. 동일 입력으로 재생성
payload = serialize(result)
replay = serialize(build_candidate(layout))

assert payload == replay

print("[PASS] 재생성 바이트 일치")

# 4. 기존 파일 덮어쓰기 금지
assert OUTPUT.parent.is_dir()
assert not OUTPUT.exists(), (
    "기존 결과 파일이 있습니다. 덮어쓰지 않습니다."
)

with OUTPUT.open("xb") as f:
    f.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == result

print("[PASS] 후보 JSON 저장·재읽기")

# 5. 기존 파일 불변 확인
assert LAYOUT.read_bytes() == layout_raw
assert SOURCE.read_bytes() == source_raw

print("[PASS] 기존 Layout / Text JSON 불변")

# 6. 검토용 출력
print("\n[페이지별 결과]")

for page in result["pages"]:
    print(
        f"PAGE {page['page']:02d}",
        f"| 좌 {page['left_block_count']}",
        f"| 우 {page['right_block_count']}",
        f"| 미분류 {page['unassigned_block_count']}",
    )

print("\n[읽기 순서 후보 미리보기]")

for page in result["pages"][:3]:
    print("\n" + "=" * 65)
    print(f"PAGE {page['page']:02d} / LEFT")
    print(page["left_text"][:1300])

    print(f"\nPAGE {page['page']:02d} / RIGHT")
    print(page["right_text"][:1300])

print("\n===== STEP 64-08 최종 결과 =====")
print("전체 페이지:", len(result["pages"]))
print("원본 블록:", result["original_block_count"])
print("재정렬 블록:", result["reordered_block_count"])
print("누락·중복 검사: PASS")
print("재현성 검사: PASS")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", sha256(payload))
print("읽기 순서 최종 승인: 미실행")
print("표 구조 최종 승인: 미실행")
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")