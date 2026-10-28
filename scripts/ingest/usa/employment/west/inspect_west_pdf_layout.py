
from pathlib import Path
import hashlib
import json
import pymupdf

ROOT = Path(__file__).resolve().parents[5]

RAW = ROOT / "data/raw/usa/employment/west"
PROCESSED = ROOT / "data/processed/usa/employment/west"

PDF = RAW / "west_2026_first_half_notice.pdf"
TEXT_JSON = PROCESSED / "west_2026_first_half_notice_text.json"

REPORT = PROCESSED / "west_2026_first_half_layout_audit.json"
PREVIEW_DIR = RAW / "layout_previews"

EXPECTED_PDF_SHA = (
    "6f11ae189a6ec58bde63eb52c2e7eba"
    "80b6ec4ffde1f0620f1dca95200542c31"
)

EXPECTED_JSON_SHA = (
    "32c1889fc24e19b39ae3cbbde9a254"
    "230b6d70dbe320a146d6f49a91acb2bf68"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    return " ".join(text.split())


print("===== STEP 64-07 WEST PDF 레이아웃 통합 분석 =====")

# 1. 원본 무결성 검사
pdf_bytes = PDF.read_bytes()
json_bytes = TEXT_JSON.read_bytes()

assert sha256(pdf_bytes) == EXPECTED_PDF_SHA
assert sha256(json_bytes) == EXPECTED_JSON_SHA

source_json = json.loads(json_bytes.decode("utf-8"))
assert source_json["program_id"] == "US-WEST-01"
assert source_json["page_count"] == 11
assert source_json["source"]["raw_pdf_sha256"] == EXPECTED_PDF_SHA

assert not REPORT.exists(), "기존 분석 JSON이 있습니다."

PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

PREVIEW_PAGES = {1, 2, 3, 11}

for page_no in PREVIEW_PAGES:
    assert not (
        PREVIEW_DIR / f"page_{page_no:02d}.png"
    ).exists(), "기존 페이지 미리보기가 있습니다."

print("[PASS] PDF / 텍스트 JSON SHA-256")

# 2. 11페이지 전체 블록 분석
page_reports = []
preview_data = []

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
    assert len(doc) == 11

    for index, page in enumerate(doc):
        page_no = index + 1
        width = page.rect.width
        height = page.rect.height

        blocks = []
        left_count = 0
        right_count = 0
        cross_count = 0

        for block in page.get_text("blocks", sort=True):
            x0, y0, x1, y1, text, _, block_type = block[:7]

            if block_type != 0:
                continue

            clean = normalize(text)
            if not clean:
                continue

            # 블록이 페이지 중앙선을 가로지르는지 기록.
            # 표·다단 여부를 확정하는 판정은 아님.
            middle = width / 2

            if x1 <= middle:
                position = "left"
                left_count += 1
            elif x0 >= middle:
                position = "right"
                right_count += 1
            else:
                position = "cross_center"
                cross_count += 1

            blocks.append({
                "bbox": [
                    round(x0, 2),
                    round(y0, 2),
                    round(x1, 2),
                    round(y1, 2),
                ],
                "position": position,
                "text": text,
            })

        original_text = page.get_text("text", sort=True)

        assert original_text == (
            source_json["pages"][index]["raw_text_ko"]
        ), f"{page_no}페이지 원본 텍스트 불일치"

        page_reports.append({
            "page": page_no,
            "width": round(width, 2),
            "height": round(height, 2),
            "text_block_count": len(blocks),
            "left_block_count": left_count,
            "right_block_count": right_count,
            "cross_center_block_count": cross_count,
            "blocks": blocks,
            "manual_layout_review_required": True,
        })

        print(
            f"[PAGE {page_no:02d}]",
            f"블록 {len(blocks)}개",
            f"| 좌 {left_count}",
            f"| 우 {right_count}",
            f"| 중앙교차 {cross_count}",
        )

        if page_no in PREVIEW_PAGES:
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(1.5, 1.5),
                alpha=False,
            )
            preview_data.append((
                PREVIEW_DIR / f"page_{page_no:02d}.png",
                pixmap.tobytes("png"),
            ))

print("[PASS] 11페이지 텍스트·좌표 검증")
print("[PASS] 원본 JSON과 페이지별 텍스트 일치")

# 3. 레이아웃 분석 결과 생성
result = {
    "dataset_type": "pdf_layout_audit",
    "program_id": "US-WEST-01",
    "source_pdf_sha256": EXPECTED_PDF_SHA,
    "source_text_json_sha256": EXPECTED_JSON_SHA,
    "page_count": len(page_reports),
    "coordinate_unit": "PDF points",
    "column_position_method": "page_midpoint_heuristic",
    "reading_order_validated": False,
    "tables_validated": False,
    "validation_status": "needs_review",
    "automatic_eligibility_rules_enabled": False,
    "pages": page_reports,
}

payload = (
    json.dumps(result, ensure_ascii=False, indent=2)
    + "\n"
).encode("utf-8")

# 4. 저장 전 재현성 확인
replay_payload = (
    json.dumps(result, ensure_ascii=False, indent=2)
    + "\n"
).encode("utf-8")

assert payload == replay_payload

# 5. 출력 저장
with REPORT.open("xb") as f:
    f.write(payload)

for path, content in preview_data:
    with path.open("xb") as f:
        f.write(content)

assert REPORT.read_bytes() == payload

loaded = json.loads(REPORT.read_text(encoding="utf-8"))
assert loaded == result

for path, content in preview_data:
    assert path.read_bytes() == content

# 6. 원본 불변 확인
assert sha256(PDF.read_bytes()) == EXPECTED_PDF_SHA
assert sha256(TEXT_JSON.read_bytes()) == EXPECTED_JSON_SHA

print("[PASS] 레이아웃 JSON 저장·재읽기")
print("[PASS] 4개 페이지 미리보기 PNG 저장")
print("[PASS] 기존 PDF·텍스트 JSON 불변")

print("\n===== STEP 64-07 최종 결과 =====")
print("분석 페이지:", len(page_reports))
print(
    "전체 텍스트 블록:",
    sum(p["text_block_count"] for p in page_reports)
)
print("미리보기:", len(preview_data), "개")
print("레이아웃 JSON:", REPORT.relative_to(ROOT))
print("레이아웃 JSON SHA-256:", sha256(payload))
print("미리보기 폴더:", PREVIEW_DIR.relative_to(ROOT))
print("원본 읽기 순서 승인: 미실행")
print("표의 행·열 구조 승인: 미실행")
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")