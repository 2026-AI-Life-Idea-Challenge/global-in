
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import requests

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = ROOT / "data/raw/japan/employment"
PDF_DIR = RAW_DIR / "japan_employment_coe_pdfs"

MANIFEST_PATH = RAW_DIR / "japan_employment_document_manifest.json"
HASH_PATH = RAW_DIR / "japan_employment_coe_pdf_hashes.json"

TARGETS = {
    "001366995.pdf": "해당 활동 및 상륙허가 기준",
    "001404131.pdf": "COE 카테고리 공통 제출서류",
    "001437254.pdf": "COE 카테고리 3·4 제출서류",
}

print("===== STEP 63-7 일본 취업 COE PDF 다운로드 =====")

assert MANIFEST_PATH.is_file(), "공식 자료 Manifest가 없습니다."
assert not HASH_PATH.exists(), "해시 기록 파일이 이미 존재합니다."

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
assert manifest["route_id"] == "JP-EM"

documents = {
    item["filename"]: item
    for item in manifest["documents"]
}

for filename in TARGETS:
    assert filename in documents, f"Manifest에 없는 자료: {filename}"
    assert documents[filename]["file_type"] == "pdf"

PDF_DIR.mkdir(parents=True, exist_ok=True)

records = []

for filename, description in TARGETS.items():
    item = documents[filename]
    url = item["source_url"]
    path = PDF_DIR / filename

    # 기존 파일이 있으면 덮어쓰지 않고 무결성만 확인
    if path.exists():
        data = path.read_bytes()
        status = "existing_verified"
        print(f"\n기존 파일 확인: {filename}")
    else:
        print(f"\n다운로드: {filename}")
        print("URL:", url)

        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=60,
        )
        response.raise_for_status()

        data = response.content
        status = "downloaded"

    # PDF 원본 확인
    assert data.startswith(b"%PDF-"), (
        f"PDF 형식이 아닌 응답: {filename}"
    )
    assert len(data) > 1000, (
        f"PDF 크기가 비정상적입니다: {filename}"
    )

    sha256 = hashlib.sha256(data).hexdigest()

    if status == "downloaded":
        # 대상 파일을 덮어쓰지 않도록 배타적으로 생성
        with path.open("xb") as f:
            f.write(data)

    # 디스크에 저장된 원본 검증
    saved_data = path.read_bytes()
    assert hashlib.sha256(saved_data).hexdigest() == sha256

    records.append({
        "filename": filename,
        "description_ko": description,
        "source_url": url,
        "relative_path": path.relative_to(ROOT).as_posix(),
        "size_bytes": len(saved_data),
        "sha256": sha256,
        "download_status": status,
        "validation_status": "needs_review",
    })

    print("상태:", status)
    print("크기:", len(saved_data), "bytes")
    print("SHA-256:", sha256)

hash_data = {
    "route_id": "JP-EM",
    "program_id": "JP-EM-01",
    "application_type": "coe",
    "source_manifest": MANIFEST_PATH.relative_to(ROOT).as_posix(),
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "validation_status": "needs_review",
    "files": records,
}

# 완료된 PDF 해시 기록을 새 파일로 저장
with HASH_PATH.open("x", encoding="utf-8") as f:
    json.dump(hash_data, f, ensure_ascii=False, indent=2)

saved = json.loads(HASH_PATH.read_text(encoding="utf-8"))
assert saved == hash_data, "해시 기록 검증 실패"

print("\n===== 최종 검증 =====")
print("PDF 파일:", len(records))
print("다운로드 폴더:", PDF_DIR.relative_to(ROOT))
print("해시 기록:", HASH_PATH.relative_to(ROOT))
print("PDF 무결성 검증: 성공")
print("정책 검증 상태: needs_review")