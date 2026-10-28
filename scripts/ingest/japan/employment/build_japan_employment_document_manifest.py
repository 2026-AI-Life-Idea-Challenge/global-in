
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
RAW_DIR = ROOT / "data/raw/japan/employment"

HTML_PATH = RAW_DIR / "japan_employment_immigration_ja.html"
META_PATH = RAW_DIR / "japan_employment_immigration.json"
OUTPUT_PATH = RAW_DIR / "japan_employment_document_manifest.json"

print("===== STEP 63-6 일본 취업 공식 자료 Manifest 생성 =====")

# 기존 파일 보호
assert HTML_PATH.is_file(), "HTML 원본이 없습니다."
assert META_PATH.is_file(), "수집 메타데이터가 없습니다."
assert not OUTPUT_PATH.exists(), "Manifest가 이미 존재합니다. 덮어쓰지 않습니다."

html_bytes = HTML_PATH.read_bytes()
metadata = json.loads(META_PATH.read_text(encoding="utf-8"))

sha256 = hashlib.sha256(html_bytes).hexdigest()

assert sha256 == metadata["source_sha256"], "원본 SHA-256 불일치"

soup = BeautifulSoup(
    html_bytes.decode("utf-8", errors="strict"),
    "html.parser",
)

# 주요 신청 유형
SECTION_MAP = {
    "在留資格認定証明書交付申請": "coe",
    "在留資格変更許可申請": "change",
    "在留期間更新許可申請": "renewal",
    "在留資格取得許可申請": "acquisition",
    "この在留資格で在留中の方に必要な届出": "notifications",
    "参考資料": "references",
}

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}

documents = {}
current_section = "general"

# HTML에 나타나는 순서대로 섹션과 링크 확인
for node in soup.find_all(["h2", "a"]):

    if node.name == "h2":
        heading = node.get_text(" ", strip=True)
        current_section = SECTION_MAP.get(
            heading,
            "other",
        )
        continue

    href = node.get("href")
    if not href:
        continue

    from urllib.parse import urljoin
    url = urljoin(metadata["source_url"], href)
    parsed = urlparse(url)

    # 공식 사이트의 자료 파일만 수집
    if parsed.netloc != "www.moj.go.jp":
        continue

    if not parsed.path.startswith("/isa/content/"):
        continue

    filename = Path(parsed.path).name
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        continue

    label = node.get_text(" ", strip=True)

    if url not in documents:
        documents[url] = {
            "filename": filename,
            "file_type": extension.lstrip("."),
            "source_url": url,
            "link_labels_ja": [],
            "application_types": [],
            "download_status": "not_downloaded",
            "validation_status": "needs_review",
        }

    item = documents[url]

    if label and label not in item["link_labels_ja"]:
        item["link_labels_ja"].append(label)

    if current_section not in item["application_types"]:
        item["application_types"].append(current_section)

manifest = {
    "route_id": "JP-EM",
    "program_id": "JP-EM-01",
    "status_of_residence": "技術・人文知識・国際業務",
    "official_agency": "Immigration Services Agency of Japan",
    "source_page_url": metadata["source_url"],
    "source_html_sha256": sha256,
    "validation_status": "needs_review",
    "documents": list(documents.values()),
}

assert manifest["documents"], "공식 자료 링크를 찾지 못했습니다."

OUTPUT_PATH.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

# 저장 결과 재검증
saved = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
assert saved == manifest, "저장된 Manifest 검증 실패"

print("Manifest 저장:", OUTPUT_PATH.relative_to(ROOT))
print("고유 자료 파일:", len(documents))

counts = {}
for doc in documents.values():
    ext = doc["file_type"]
    counts[ext] = counts.get(ext, 0) + 1

print("파일 형식별 개수:", counts)

print("\n===== 공식 자료 목록 =====")
for i, doc in enumerate(documents.values(), 1):
    print(f"{i:02d}. {doc['filename']}")
    print("    신청 유형:", ", ".join(doc["application_types"]))
    print("    설명:", " / ".join(doc["link_labels_ja"])[:150])

print("\n원본 HTML SHA-256 검증: 성공")
print("Manifest 저장 검증: 성공")
print("실제 파일 다운로드: 미실행")
print("정책 검증 상태: needs_review")