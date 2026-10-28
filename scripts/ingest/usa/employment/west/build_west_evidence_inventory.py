
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa/employment/west"

LAYOUT = BASE / "west_2026_first_half_layout_audit.json"
CANDIDATE = BASE / "west_2026_first_half_column_candidate.json"

OUTPUT = BASE / "west_2026_first_half_evidence_inventory.json"

EXPECTED_LAYOUT_SHA = (
    "296bd49de37aaeb35525f4939078bea"
    "63900fae0633ad661c491c35255cd3043"
)

EXPECTED_CANDIDATE_SHA = (
    "31865507945b9a46c7485518364597"
    "ccf44978622c50242913dde822a481b8e3"
)

KEYWORDS = {
    "eligibility": [
        "지원 자격", "지원 대상", "지원 제한",
        "대한민국 국적", "TOEIC", "OPIc",
        "G-TELP", "졸업생", "재학생",
    ],
    "documents": [
        "제출서류", "구비서류", "성적증명서",
        "재학증명서", "졸업증명서", "추천 공문",
        "증빙자료", "자기소개서",
    ],
    "application": [
        "신청 기간", "신청 절차", "온라인 지원",
        "서류 제출", "지원하기", "월드잡플러스",
    ],
    "cost_and_support": [
        "참가비", "정부재정지원", "항공료",
        "생활비", "지원구간", "본인부담금",
    ],
    "program": [
        "중기 WEST", "단기 WEST",
        "어학연수", "인턴", "선발인원",
    ],
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


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


def matches_keywords(text):
    compact = normalize(text).casefold()
    result = {}

    for category, keywords in KEYWORDS.items():
        found = [
            word for word in keywords
            if word.casefold() in compact
        ]
        if found:
            result[category] = found

    return result


def build_inventory(layout):
    logical_pages = []
    evidence = []
    counters = Counter()

    for physical_page in layout["pages"]:
        physical_no = physical_page["page"]
        source_blocks = physical_page["blocks"]

        for side in ("left", "right"):
            side_blocks = []

            for original_index, block in enumerate(source_blocks):
                if block["position"] != side:
                    continue

                side_blocks.append({
                    "original_block_index": original_index,
                    "bbox": block["bbox"],
                    "text": block["text"],
                })

            side_blocks.sort(
                key=lambda item: (
                    item["bbox"][1],
                    item["bbox"][0],
                    item["original_block_index"],
                )
            )

            logical_no = (physical_no - 1) * 2 + (
                1 if side == "left" else 2
            )

            text = "\n\n".join(
                item["text"].strip()
                for item in side_blocks
                if item["text"].strip()
            )

            logical_pages.append({
                "logical_page_candidate": logical_no,
                "physical_pdf_page": physical_no,
                "side": side,
                "block_count": len(side_blocks),
                "text": text,
                "text_sha256": sha256(
                    text.encode("utf-8")
                ),
                "printed_page_number_verified": False,
            })

            for block in side_blocks:
                found = matches_keywords(block["text"])

                if not found:
                    continue

                evidence.append({
                    "evidence_id": (
                        f"WEST-P{physical_no:02d}-"
                        f"{side[0].upper()}-"
                        f"B{block['original_block_index']:03d}"
                    ),
                    "logical_page_candidate": logical_no,
                    "physical_pdf_page": physical_no,
                    "side": side,
                    "original_block_index": (
                        block["original_block_index"]
                    ),
                    "bbox": block["bbox"],
                    "source_text": block["text"],
                    "keyword_categories": found,
                    "table_cell_relationship_verified": False,
                    "legal_interpretation_verified": False,
                })

                for category in found:
                    counters[category] += 1

    original_blocks = sum(
        len(page["blocks"])
        for page in layout["pages"]
    )

    recovered_blocks = sum(
        page["block_count"]
        for page in logical_pages
    )

    assert original_blocks == recovered_blocks == 577

    ids = [
        (item["physical_pdf_page"],
         item["side"],
         item["original_block_index"])
        for item in evidence
    ]

    assert len(ids) == len(set(ids))

    assert len(logical_pages) == 22

    return {
        "dataset_type": "official_evidence_inventory",
        "program_id": "US-WEST-01",
        "source_layout_sha256": EXPECTED_LAYOUT_SHA,
        "source_candidate_sha256": EXPECTED_CANDIDATE_SHA,
        "physical_pdf_page_count": 11,
        "logical_page_candidate_count": 22,
        "source_block_count": 577,
        "evidence_block_count": len(evidence),
        "evidence_category_counts": dict(
            sorted(counters.items())
        ),
        "layout_method": "physical_page_left_then_right",
        "logical_page_order_verified": False,
        "table_cell_relationship_verified": False,
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
        "logical_pages": logical_pages,
        "evidence": evidence,
    }


print("===== STEP 64-09 WEST 공식 근거 통합 정리 =====")

# 1. 원본 검증
layout_raw = LAYOUT.read_bytes()
candidate_raw = CANDIDATE.read_bytes()

assert sha256(layout_raw) == EXPECTED_LAYOUT_SHA
assert sha256(candidate_raw) == EXPECTED_CANDIDATE_SHA

layout = json.loads(layout_raw.decode("utf-8"))
candidate = json.loads(candidate_raw.decode("utf-8"))

assert layout["page_count"] == 11
assert candidate["page_count"] == 11
assert layout["program_id"] == "US-WEST-01"
assert candidate["program_id"] == "US-WEST-01"

print("[PASS] 기존 분석 데이터 SHA-256")

# 2. 논리 페이지 및 근거 추출
result = build_inventory(layout)

# 기존 좌우 분리 결과와 텍스트 비교
for logical_page in result["logical_pages"]:
    physical_index = logical_page["physical_pdf_page"] - 1
    original = candidate["pages"][physical_index]

    expected_text = (
        original["left_text"]
        if logical_page["side"] == "left"
        else original["right_text"]
    )

    assert logical_page["text"] == expected_text, (
        "기존 좌우 텍스트와 불일치: "
        f"{logical_page['logical_page_candidate']}"
    )

print("[PASS] 좌우 인쇄 페이지 후보 22개")
print("[PASS] 기존 좌우 추출 결과와 텍스트 일치")
print("[PASS] 577개 블록 누락·중복 없음")

# 3. 재현성 검증
payload = serialize(result)
assert payload == serialize(build_inventory(layout))

print("[PASS] 메모리 재생성 결과 일치")

# 4. 안전한 저장
assert OUTPUT.parent.is_dir()
assert not OUTPUT.exists(), "기존 출력 파일 존재"

with OUTPUT.open("xb") as file:
    file.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == result

# 5. 기존 데이터 불변 확인
assert LAYOUT.read_bytes() == layout_raw
assert CANDIDATE.read_bytes() == candidate_raw

print("[PASS] JSON 저장 및 검증")
print("[PASS] 기존 원본 불변")

# 6. 핵심 결과 출력
print("\n[근거 유형별 텍스트 블록]")
for category, count in result[
    "evidence_category_counts"
].items():
    print(f"{category}: {count}")

print("\n[주요 근거 예시]")

shown = set()

for item in result["evidence"]:
    for category in item["keyword_categories"]:
        if category in shown:
            continue

        shown.add(category)

        print(
            f"\n[{category}]",
            f"PDF {item['physical_pdf_page']}페이지",
            item["side"],
        )
        print(normalize(item["source_text"])[:350])

    if len(shown) == len(KEYWORDS):
        break

print("\n===== STEP 64-09 최종 결과 =====")
print("PDF 물리 페이지:", 11)
print("논리 페이지 후보:", len(result["logical_pages"]))
print("원본 블록:", result["source_block_count"])
print("근거 후보 블록:", result["evidence_block_count"])
print("결과 파일:", OUTPUT.relative_to(ROOT))
print("결과 SHA-256:", sha256(payload))
print("원본 불변: PASS")
print("재현성: PASS")
print("표 열 관계 승인: 미실행")
print("법적 조건 해석: 미실행")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")