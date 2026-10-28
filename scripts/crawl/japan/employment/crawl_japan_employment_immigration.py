
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = ROOT / "data/raw/japan/employment"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_URL = (
    "https://www.moj.go.jp/isa/applications/status/gijinkoku"
)

HTML_PATH = RAW_DIR / "japan_employment_immigration_ja.html"
JSON_PATH = RAW_DIR / "japan_employment_immigration.json"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ja-JP,ja;q=0.9",
}

print("===== STEP 63-2 공식 원문 수집 =====")
print("공식 URL:", SOURCE_URL)

try:
    response = requests.get(
        SOURCE_URL,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
except requests.RequestException as e:
    print("수집 실패:", e)
    print("기존 파일은 변경하지 않았습니다.")
    raise SystemExit(1)

html_bytes = response.content

# 공식 HTML의 실제 인코딩을 UTF-8로 명시
# 디코딩 오류가 발생하면 수집을 중단
html_text = html_bytes.decode("utf-8", errors="strict")

if (
    len(html_bytes) < 1000
    or "技術・人文知識・国際業務" not in html_text
):
    print("공식 페이지 내용 검증 실패")
    print("기존 파일은 변경하지 않았습니다.")
    raise SystemExit(1)

sha256 = hashlib.sha256(html_bytes).hexdigest()

metadata = {
    "route_id": "JP-EM",
    "program_id": "JP-EM-01",
    "country": "Japan",
    "status_of_residence": "技術・人文知識・国際業務",
    "official_agency": "Immigration Services Agency of Japan",
    "source_url": SOURCE_URL,
    "final_url": response.url,
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "collection_mode": "automated",
    "source_sha256": sha256,
    "html_bytes": len(html_bytes),
    "validation_status": "needs_review",
    "verified_at": None,
}

# 기존 파일이 있다면 덮어쓰지 않음
for path in (HTML_PATH, JSON_PATH):
    if path.exists():
        print("이미 존재하는 파일:", path)
        print("기존 파일 보호를 위해 저장 중단")
        raise SystemExit(1)

HTML_PATH.write_bytes(html_bytes)

JSON_PATH.write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

assert hashlib.sha256(
    HTML_PATH.read_bytes()
).hexdigest() == sha256

print("HTML 저장:", HTML_PATH.relative_to(ROOT))
print("JSON 저장:", JSON_PATH.relative_to(ROOT))
print("HTML 크기:", len(html_bytes), "bytes")
print("SHA-256:", sha256)
print("정책 검증:", metadata["validation_status"])
print("원본 무결성 검증: 성공")
