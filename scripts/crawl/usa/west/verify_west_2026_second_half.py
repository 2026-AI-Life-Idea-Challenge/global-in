
from pathlib import Path
import hashlib
import json
import pymupdf

ROOT = Path(__file__).resolve().parents[4]
FOLDER = ROOT / "data/raw/usa/employment/west/2026_second_half"

PDF = FOLDER / "west_2026_second_half_notice.pdf"
ORIGINAL_MANIFEST = FOLDER / "source_manifest.json"
SUPPLEMENT = FOLDER / "pdf_verification_manifest.json"

EXPECTED_MANIFEST_SHA = (
    "123e7325ec53adb35f9f40b866454c8"
    "cb335935bf10fe771c703e482ad55d1eb"
)

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

print("===== STEP 64-36 하반기 WEST PDF 검증 =====")

assert PDF.is_file(), f"PDF가 없습니다: {PDF}"
assert ORIGINAL_MANIFEST.is_file()

manifest_raw = ORIGINAL_MANIFEST.read_bytes()
assert sha256(manifest_raw) == EXPECTED_MANIFEST_SHA

pdf_raw = PDF.read_bytes()
assert pdf_raw.startswith(b"%PDF-")

with pymupdf.open(stream=pdf_raw, filetype="pdf") as doc:
    page_count = len(doc)
    text = "\n".join(page.get_text() for page in doc)

assert page_count > 0
assert "WEST" in text.upper(), "WEST 문구 확인 실패"
assert "2026" in text, "2026년 표기 확인 실패"
assert "하반기" in text, "하반기 표기 확인 실패"

result = {
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_url": (
        "https://www.niied.go.kr/web/main/"
        "nid/niied_board/5749"
    ),
    "pdf_path": PDF.relative_to(ROOT).as_posix(),
    "pdf_sha256": sha256(pdf_raw),
    "pdf_size_bytes": len(pdf_raw),
    "physical_pdf_pages": page_count,
    "document_keywords_verified": [
        "WEST", "2026", "하반기"
    ],
    "original_manifest_sha256": EXPECTED_MANIFEST_SHA,
    "document_identity_status": "candidate_verified",
    "official_attachment_provenance_status": (
        "manual_download_claim_pending_independent_check"
    ),
    "semantic_review_status": "needs_review",
    "historical_notice": True,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

payload = (
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
).encode("utf-8")

if SUPPLEMENT.exists():
    assert SUPPLEMENT.read_bytes() == payload, (
        "기존 검증 기록과 충돌합니다."
    )
    state = "EXISTS_VERIFIED"
else:
    with SUPPLEMENT.open("xb") as f:
        f.write(payload)
    state = "CREATED"

assert sha256(ORIGINAL_MANIFEST.read_bytes()) == (
    EXPECTED_MANIFEST_SHA
)

print("[PASS] 기존 출처 기록 불변")
print("[PASS] PDF 파일 형식·본문 확인")
print("[PASS] 검증 기록:", state)
print("PDF 페이지:", page_count)
print("PDF 크기:", len(pdf_raw), "bytes")
print("PDF SHA-256:", sha256(pdf_raw))
print("기록 SHA-256:", sha256(payload))
print("정책 의미 검증: 미완료")
print("답변·임베딩 승인: False")
print("Git 커밋·푸시: 미실행")