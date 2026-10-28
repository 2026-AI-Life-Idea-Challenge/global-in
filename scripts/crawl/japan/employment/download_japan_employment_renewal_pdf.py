
from pathlib import Path
import hashlib
import json

import requests

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
MANIFEST = RAW / "japan_employment_document_manifest.json"

PDF_DIR = RAW / "japan_employment_renewal_pdfs"
PDF_PATH = PDF_DIR / "001367009.pdf"

HASH_PATH = RAW / "japan_employment_renewal_pdf_hashes.json"

FILENAME = "001367009.pdf"
URL = "https://www.moj.go.jp/isa/content/001367009.pdf"

print("===== STEP 63-72 재류기간 갱신 PDF 다운로드 =====")

# 1. 기존 파일 보호
assert MANIFEST.is_file(), "매니페스트 파일 누락"
assert not PDF_PATH.exists(), "PDF가 이미 존재합니다."
assert not HASH_PATH.exists(), "해시 기록이 이미 존재합니다."

# 2. 공식 문서 정보 확인
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

def find_records(obj):
    if isinstance(obj, dict):
        if obj.get("filename") == FILENAME:
            yield obj
        for value in obj.values():
            yield from find_records(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from find_records(value)

records = list(find_records(manifest))

assert len(records) == 1, (
    f"매니페스트 문서 수 이상: {len(records)}"
)

record = records[0]

assert record["source_url"] == URL
assert record["file_type"] == "pdf"
assert "renewal" in record["application_types"]

print("매니페스트 확인: 성공")
print("공식 URL:", URL)

# 3. PDF 다운로드
response = requests.get(
    URL,
    timeout=60,
    headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/pdf",
    },
)
response.raise_for_status()

content = response.content

assert len(content) > 1000, "파일 크기 비정상"
assert content.startswith(b"%PDF-"), "PDF 형식 아님"

pdf_sha = hashlib.sha256(content).hexdigest()

# 4. 원본 저장
PDF_DIR.mkdir(parents=True, exist_ok=True)

with PDF_PATH.open("xb") as f:
    f.write(content)

assert hashlib.sha256(
    PDF_PATH.read_bytes()
).hexdigest() == pdf_sha

# 5. 다운로드 및 검증 정보 저장
result = {
    "route_id": "JP-EM",
    "application_type": "renewal",
    "official_agency": "Immigration Services Agency of Japan",
    "files": [
        {
            "filename": FILENAME,
            "source_url": URL,
            "sha256": pdf_sha,
            "file_size_bytes": len(content),
            "download_status": "downloaded",
            "validation_status": "needs_review",
        }
    ],
}

with HASH_PATH.open("x", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

assert json.loads(
    HASH_PATH.read_text(encoding="utf-8")
) == result

print("\n===== STEP 63-72 최종 결과 =====")
print("PDF:", PDF_PATH.relative_to(ROOT))
print("파일 크기:", len(content), "bytes")
print("SHA-256:", pdf_sha)
print("해시 기록:", HASH_PATH.relative_to(ROOT))
print("PDF 형식 검사: PASS")
print("원본 무결성: PASS")
print("기존 JSON 수정: 없음")
print("정책 검증: needs_review")
print("Git 커밋·푸시: 미실행")