
from pathlib import Path
import hashlib
import json

import requests

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"

MANIFEST = RAW / "japan_employment_document_manifest.json"

PDF_DIR = RAW / "japan_employment_change_pdfs"
PDF_PATH = PDF_DIR / "001437255.pdf"

HASH_PATH = RAW / "japan_employment_change_pdf_hashes.json"

FILENAME = "001437255.pdf"

EXPECTED_URL = (
    "https://www.moj.go.jp/isa/content/001437255.pdf"
)

print("===== STEP 63-50 재류자격 변경 PDF 다운로드 =====")

# 1. 기존 데이터 보호
assert MANIFEST.is_file(), "공식 문서 매니페스트 누락"

assert not PDF_PATH.exists(), (
    "PDF 파일이 이미 존재합니다. 덮어쓰지 않습니다."
)

assert not HASH_PATH.exists(), (
    "SHA-256 기록이 이미 존재합니다. 덮어쓰지 않습니다."
)

# 2. 매니페스트에서 문서 확인
manifest = json.loads(
    MANIFEST.read_text(encoding="utf-8")
)

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
    f"매니페스트 문서 검색 결과 이상: {len(records)}개"
)

record = records[0]

assert record["source_url"] == EXPECTED_URL
assert "change" in record["application_types"]
assert record["file_type"] == "pdf"

print("매니페스트 문서 확인: 성공")
print("공식 URL:", EXPECTED_URL)

# 3. 공식 PDF 다운로드
response = requests.get(
    EXPECTED_URL,
    timeout=60,
    headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/pdf",
    },
)

response.raise_for_status()

content = response.content

assert len(content) > 1000, (
    "다운로드 파일 크기가 비정상적으로 작습니다."
)

assert content.startswith(b"%PDF-"), (
    "PDF가 아닌 응답입니다. HTML 오류 페이지일 수 있습니다."
)

sha256 = hashlib.sha256(content).hexdigest()

# 4. PDF 원본 저장
PDF_DIR.mkdir(parents=True, exist_ok=True)

with PDF_PATH.open("xb") as f:
    f.write(content)

assert hashlib.sha256(
    PDF_PATH.read_bytes()
).hexdigest() == sha256, (
    "저장된 PDF의 SHA-256 검증 실패"
)

# 5. 출처 및 해시 기록
hash_record = {
    "route_id": "JP-EM",
    "application_type": "change",
    "official_agency": "Immigration Services Agency of Japan",
    "files": [
        {
            "filename": FILENAME,
            "source_url": EXPECTED_URL,
            "sha256": sha256,
            "file_size_bytes": len(content),
            "download_status": "downloaded",
            "validation_status": "needs_review",
        }
    ],
}

with HASH_PATH.open("x", encoding="utf-8") as f:
    json.dump(
        hash_record,
        f,
        ensure_ascii=False,
        indent=2,
    )

saved_record = json.loads(
    HASH_PATH.read_text(encoding="utf-8")
)

assert saved_record == hash_record

print("\n===== STEP 63-50 최종 결과 =====")
print("PDF 저장:", PDF_PATH.relative_to(ROOT))
print("파일 크기:", len(content), "bytes")
print("SHA-256:", sha256)
print("해시 기록:", HASH_PATH.relative_to(ROOT))
print("PDF 형식 검사: 성공")
print("저장 후 SHA-256 검증: 성공")
print("기존 COE JSON: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")