
from pathlib import Path
from io import BytesIO
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
import hashlib
import json
import re

import requests
import fitz

ROOT = Path(__file__).resolve().parents[5]

RAW = ROOT / "data/raw/usa"
PROCESSED = ROOT / "data/processed/usa"

SOURCE_JSON = (
    PROCESSED / "employment/west/source_content.json"
)

RAW_OUTPUT = (
    RAW / "employment/west/"
    "west_2026_first_half_notice.pdf"
)

JSON_OUTPUT = (
    PROCESSED / "employment/west/"
    "west_2026_first_half_notice_text.json"
)

EXPECTED_SOURCE_SHA = (
    "73d9860fe38632e5463072480926df"
    "9dc78ec48c3559d09bd3c85d3fc5b433d2"
)

EXPECTED_FILE_ID = (
    "d38331d7144c4042b8069bfbbb7855da"
)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def extract_pdf(raw):
    pages = []

    with fitz.open(stream=raw, filetype="pdf") as doc:
        assert len(doc) > 0, "PDF 페이지가 없습니다."

        for number, page in enumerate(doc, 1):
            text = page.get_text("text", sort=True)

            pages.append({
                "page": number,
                "raw_text_ko": text,
                "text_length": len(text),
            })

    return pages


print("===== STEP 64-06 WEST 공식 PDF 통합 처리 =====")

# 1. 이전 구조화 결과 검증
assert SOURCE_JSON.is_file()
assert sha256(SOURCE_JSON.read_bytes()) == (
    EXPECTED_SOURCE_SHA
)

source_bytes = SOURCE_JSON.read_bytes()
source = json.loads(source_bytes.decode("utf-8"))

assert source["program_id"] == "US-WEST-01"
assert source["validation_status"] == "needs_review"

print("[PASS] 기존 WEST HTML 구조화 JSON 무결성")

# 2. HTML에서 확인한 다운로드 링크 사용
matches = []

for item in source["attachment_candidates"]:
    onclick = item["attributes"].get("onclick", "")

    if EXPECTED_FILE_ID not in onclick:
        continue

    match = re.search(
        r"""location\.href\s*=\s*['"]([^'"]+)['"]""",
        onclick,
    )

    if match:
        matches.append(match.group(1))

assert len(matches) == 1, (
    "공식 PDF 다운로드 링크를 정확히 하나로 "
    "식별하지 못했습니다."
)

source_url = source["source"]["source_url"]
download_url = urljoin(source_url, matches[0])

assert urlparse(download_url).hostname == (
    "www.niied.go.kr"
)

assert (
    urlparse(download_url).path.endswith(
        "/" + EXPECTED_FILE_ID
    )
)

print("[PASS] 공식 HTML의 PDF 다운로드 링크 확인")
print("다운로드 URL:", download_url)

# 3. 덮어쓰기 방지
assert RAW_OUTPUT.parent.is_dir()
assert JSON_OUTPUT.parent.is_dir()

assert not RAW_OUTPUT.exists(), "기존 PDF가 존재합니다."
assert not JSON_OUTPUT.exists(), "기존 JSON이 존재합니다."

# 4. PDF 다운로드
headers = {
    "User-Agent": "Global-In-OfficialSourceCollector/1.0",
    "Accept": "application/pdf,*/*",
}

with requests.get(
    download_url,
    headers=headers,
    timeout=(10, 40),
    stream=True,
    allow_redirects=True,
) as response:

    print("HTTP:", response.status_code)
    print("최종 URL:", response.url)

    response.raise_for_status()

    assert urlparse(response.url).hostname in {
        "www.niied.go.kr",
        "niied.go.kr",
    }, "예상하지 못한 호스트로 이동했습니다."

    chunks = []
    total = 0
    limit = 20 * 1024 * 1024

    for chunk in response.iter_content(65536):
        if not chunk:
            continue

        total += len(chunk)

        if total > limit:
            raise ValueError("다운로드 크기 20MB 초과")

        chunks.append(chunk)

    pdf_bytes = b"".join(chunks)
    content_type = response.headers.get(
        "Content-Type", ""
    )
    final_url = response.url

assert pdf_bytes.startswith(b"%PDF-"), (
    "다운로드 결과가 PDF가 아닙니다."
)

print("[PASS] HTTP 다운로드 및 PDF 시그니처")

# 5. PDF 텍스트 추출
pages = extract_pdf(pdf_bytes)

total_chars = sum(
    p["text_length"] for p in pages
)

assert total_chars > 100, (
    "추출된 텍스트가 부족합니다. "
    "스캔 PDF 여부 등을 별도로 확인하세요."
)

print("[PASS] PDF 텍스트 추출")
print("페이지 수:", len(pages))
print("전체 추출 문자:", total_chars)

# 6. 메타데이터 구성
result = {
    "dataset_type": "official_pdf_text",
    "program_id": "US-WEST-01",
    "route_id": "US-EM",
    "official_program_name": (
        "WEST (Work, English Study, Travel)"
    ),
    "notice_period": "2026_first_half",
    "source": {
        "official_agency": (
            "National Institute for International Education"
        ),
        "notice_url": source_url,
        "download_url": download_url,
        "final_download_url": final_url,
        "raw_pdf_path": RAW_OUTPUT.relative_to(
            ROOT
        ).as_posix(),
        "raw_pdf_sha256": sha256(pdf_bytes),
        "content_type": content_type,
        "collected_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    },
    "page_count": len(pages),
    "total_text_length": total_chars,
    "pages": pages,
    "validation_status": "needs_review",
    "automatic_eligibility_rules_enabled": False,
    "current_recruitment_status": "not_verified",
    "embedding_generated": False,
}

payload = (
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ) + "\n"
).encode("utf-8")

# 7. 저장 및 즉시 검증
with RAW_OUTPUT.open("xb") as f:
    f.write(pdf_bytes)

with JSON_OUTPUT.open("xb") as f:
    f.write(payload)

assert RAW_OUTPUT.read_bytes() == pdf_bytes
assert JSON_OUTPUT.read_bytes() == payload

loaded = json.loads(
    JSON_OUTPUT.read_text(encoding="utf-8")
)

assert loaded == result

# 저장된 PDF에서 독립적으로 다시 텍스트 추출
replayed_pages = extract_pdf(RAW_OUTPUT.read_bytes())

assert replayed_pages == pages
assert sha256(RAW_OUTPUT.read_bytes()) == (
    result["source"]["raw_pdf_sha256"]
)

# 8. 기존 파일 불변 검증
assert SOURCE_JSON.read_bytes() == source_bytes

print("[PASS] PDF / JSON 저장 및 SHA-256")
print("[PASS] 저장 PDF 텍스트 재추출 일치")
print("[PASS] 기존 WEST JSON 불변")

print("\n[PDF 본문 미리보기]")
for page in pages[:2]:
    print(f"\n--- {page['page']}페이지 ---")
    print(page["raw_text_ko"][:800])

print("\n===== STEP 64-06 최종 결과 =====")
print("PDF 페이지:", len(pages))
print("추출 문자:", total_chars)
print("원본 PDF:", RAW_OUTPUT.relative_to(ROOT))
print("원본 PDF SHA-256:", sha256(pdf_bytes))
print("텍스트 JSON:", JSON_OUTPUT.relative_to(ROOT))
print("JSON SHA-256:", sha256(payload))
print("기존 데이터 변경: 없음")
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")