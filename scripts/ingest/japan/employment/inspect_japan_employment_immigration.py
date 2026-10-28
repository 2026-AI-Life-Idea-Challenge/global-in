
from pathlib import Path
from urllib.parse import urljoin
import hashlib
import json

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = ROOT / "data/raw/japan/employment"

HTML_PATH = RAW_DIR / "japan_employment_immigration_ja.html"
JSON_PATH = RAW_DIR / "japan_employment_immigration.json"

print("===== STEP 63-5 일본 취업 공식 HTML 분석 =====")

assert HTML_PATH.is_file(), "HTML 원본 파일이 없습니다."
assert JSON_PATH.is_file(), "수집 메타데이터가 없습니다."

metadata = json.loads(JSON_PATH.read_text(encoding="utf-8"))
html_bytes = HTML_PATH.read_bytes()

actual_sha256 = hashlib.sha256(html_bytes).hexdigest()

assert actual_sha256 == metadata["source_sha256"], (
    "HTML SHA-256이 수집 메타데이터와 다릅니다."
)

html = html_bytes.decode("utf-8", errors="strict")
soup = BeautifulSoup(html, "html.parser")

source_url = metadata["source_url"]

print("\n[1] 원본 검증")
print("공식 URL:", source_url)
print("HTML 크기:", len(html_bytes), "bytes")
print("SHA-256:", actual_sha256)
print("무결성:", "성공")

print("\n[2] 페이지 제목")
print(
    soup.title.get_text(" ", strip=True)
    if soup.title else "(제목 없음)"
)

print("\n[3] 주요 제목 구조")

headings = soup.find_all(
    ["h1", "h2", "h3", "h4"]
)

for heading in headings:
    title = heading.get_text(" ", strip=True)
    if title:
        print(f"{heading.name}: {title}")

print("\n[4] 주요 키워드 존재 여부")

keywords = [
    "在留資格認定証明書交付申請",
    "在留資格変更許可申請",
    "在留期間更新許可申請",
    "カテゴリー１",
    "カテゴリー２",
    "カテゴリー３",
    "カテゴリー４",
    "提出書類",
    "技術・人文知識・国際業務",
]

text = soup.get_text(" ", strip=True)

for keyword in keywords:
    print(f"{keyword}: {'발견' if keyword in text else '미발견'}")

print("\n[5] 신청 절차 및 제출서류 관련 링크")

link_keywords = [
    "認定",
    "変更",
    "更新",
    "提出",
    "カテゴリー",
    "PDF",
    "申請",
]

found = []
seen = set()

for a in soup.find_all("a", href=True):
    label = a.get_text(" ", strip=True)
    href = urljoin(source_url, a["href"])

    if not href.startswith(("https://", "http://")):
        continue

    if not any(k in label for k in link_keywords):
        continue

    key = (label, href)

    if key in seen:
        continue

    seen.add(key)
    found.append((label, href))

print("관련 링크 수:", len(found))

for i, (label, href) in enumerate(found[:60], start=1):
    print(f"\n{i}. {label[:150]}")
    print("   URL:", href)

if len(found) > 60:
    print(f"\n그 외 {len(found) - 60}개 링크는 출력 생략")

print("\n분석 완료: 원본 파일 변경 없음")