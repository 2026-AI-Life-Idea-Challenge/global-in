
from pathlib import Path
from urllib.parse import urljoin, urlparse
import hashlib
import json
import re

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/raw/usa"
SNAPSHOT_DIR = BASE / "source_snapshots"

MANIFEST = BASE / "usa_program_source_manifest.json"
INDEX = SNAPSHOT_DIR / "snapshot_index.json"

EXPECTED_MANIFEST_SHA = (
    "52489441fd37a75b07045d9a252a478"
    "9a144fc65d19275da8a9ca05620adaf31"
)

EXPECTED_INDEX_SHA = (
    "7db1f2c5b0b1b4a63c4db1355791880"
    "fec1ef851e253b61f756a899395c97831"
)

EXPECTED_HTML_HASHES = {
    "college-and-university-student": (
        "5af565c7af41166e935fa0eae77729"
        "e18d2d915a4fe420ba60e0e0b4ba89a976"
    ),
    "intern": (
        "a571960556b62516af3a0a356e115b"
        "98af1f4f31d9bc3879cb06a64e718b2ccd"
    ),
    "summer-work-travel": (
        "93f99b20e1ac86731492a78758e63b"
        "274155a93eb8fcd577294b33fb0d7d6a33"
    ),
    "trainee": (
        "8a7b1f64d83e63854aebe0f5033cefa"
        "39856d83102c01ae054e7e8565c213349"
    ),
    "west": (
        "6b54a77e5c55f1f10efb305bbe756"
        "7b94d55c6abffe649d085f3e43413611847"
    ),
}

EXPECTED_PROGRAM_KEYWORDS = {
    "college-and-university-student": [
        "College and University Student",
        "Students",
    ],
    "intern": [
        "Intern",
        "Internship",
    ],
    "summer-work-travel": [
        "Summer Work Travel",
    ],
    "trainee": [
        "Trainee",
        "Training",
    ],
    "west": [
        "WEST",
    ],
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def normalize(text):
    return " ".join(text.split())


def identify_source(url):
    if "niied.go.kr" in urlparse(url).netloc.lower():
        return "west"

    for key in EXPECTED_HTML_HASHES:
        if key != "west" and f"/{key}/" in url:
            return key

    raise ValueError(f"알 수 없는 출처: {url}")


def clean_body(soup):
    # 분석용 복사본: 원본 파일과 soup은 변경하지 않음
    cloned = BeautifulSoup(str(soup), "html.parser")

    for tag in cloned.select(
        "script, style, noscript, nav, footer, header"
    ):
        tag.decompose()

    main = cloned.find("main")

    if main:
        return normalize(main.get_text(" ", strip=True)), "main"

    article = cloned.find("article")

    if article:
        return normalize(article.get_text(" ", strip=True)), "article"

    body = cloned.find("body")

    if body:
        return normalize(body.get_text(" ", strip=True)), "body"

    return normalize(cloned.get_text(" ", strip=True)), "document"


def show_headings(soup):
    headings = []

    for heading in soup.find_all(
        ["h1", "h2", "h3", "h4"]
    ):
        text = normalize(heading.get_text(" ", strip=True))

        if text and text not in headings:
            headings.append(text)

    print("\n[HTML 제목 계층]")

    for title in headings[:20]:
        print(" -", title[:160])

    print("고유 제목 수:", len(headings))


def show_keyword_context(body_text, keywords):
    print("\n[프로그램 키워드 본문 확인]")

    lower = body_text.casefold()

    for keyword in keywords:
        match = re.search(
            re.escape(keyword.casefold()),
            lower,
        )

        if match:
            start = max(0, match.start() - 120)
            end = min(
                len(body_text),
                match.end() + 250,
            )

            print(
                f"[FOUND] {keyword}:",
                body_text[start:end],
            )
        else:
            print(f"[NOT FOUND] {keyword}")


def show_west_links(soup, base_url):
    print("\n[WEST 첨부·다운로드 링크 후보]")

    candidates = []
    seen = set()

    for tag in soup.select("a[href]"):
        href = tag.get("href", "").strip()
        label = normalize(tag.get_text(" ", strip=True))

        if not href or href.startswith(("javascript:", "#")):
            continue

        combined = (label + " " + href).lower()

        tokens = [
            "첨부", "다운로드", "붙임",
            "pdf", "hwp", "hwpx", "file",
            "download", "attach",
        ]

        if not any(token in combined for token in tokens):
            continue

        absolute = urljoin(base_url, href)

        key = (absolute, label)

        if key in seen:
            continue

        seen.add(key)
        candidates.append((label, absolute))

    if not candidates:
        print("후보 없음: HTML 내부 스크립트도 별도 확인 필요")

    for label, url in candidates[:20]:
        print("표시명:", label[:160])
        print("링크:", url[:300])

    print("첨부·다운로드 링크 후보 수:", len(candidates))
    print("링크의 유효성 및 실제 첨부 여부: 미검증")


print("===== STEP 64-03D 공식 HTML 본문 분석 =====")

manifest_raw = MANIFEST.read_bytes()
index_raw = INDEX.read_bytes()

assert sha256(manifest_raw) == EXPECTED_MANIFEST_SHA
assert sha256(index_raw) == EXPECTED_INDEX_SHA

manifest = json.loads(manifest_raw.decode("utf-8"))
index = json.loads(index_raw.decode("utf-8"))

assert manifest["program_count"] == 7
assert index["snapshot_count"] == 5
assert len(index["snapshots"]) == 5
assert (
    index["source_manifest_sha256"]
    == EXPECTED_MANIFEST_SHA
)

print("[PASS] Manifest SHA-256")
print("[PASS] Snapshot Index SHA-256")

total_checked = 0
identity_candidates = 0

for snapshot in index["snapshots"]:
    url = snapshot["source_url"]
    source_key = identify_source(url)

    path = SNAPSHOT_DIR / snapshot["filename"]

    # 인덱스에 등록된 파일만 읽으며 경로 이탈 방지
    assert path.resolve().parent == SNAPSHOT_DIR.resolve()
    assert path.is_file()

    raw = path.read_bytes()
    actual_sha = sha256(raw)

    assert actual_sha == snapshot["sha256"]
    assert actual_sha == EXPECTED_HTML_HASHES[source_key]

    soup = BeautifulSoup(raw, "html.parser")

    page_title = (
        normalize(soup.title.get_text(" ", strip=True))
        if soup.title
        else ""
    )

    body_text, body_location = clean_body(soup)

    print("\n" + "=" * 72)
    print("프로그램:", source_key)
    print("URL:", url)
    print("저장 파일:", snapshot["filename"])
    print("원본 SHA-256:", actual_sha)
    print("HTML title:", page_title)
    print("주요 본문 위치:", body_location)
    print("본문 글자 수:", len(body_text))

    show_headings(soup)

    keywords = EXPECTED_PROGRAM_KEYWORDS[source_key]

    show_keyword_context(body_text, keywords)

    found = any(
        keyword.casefold() in body_text.casefold()
        for keyword in keywords
    )

    if found and len(body_text) >= 300:
        print("\n[CHECK] 프로그램 관련 본문 후보 존재")
        identity_candidates += 1
    else:
        print("\n[REVIEW] 프로그램 본문 식별 수동 확인 필요")

    print("\n[본문 시작 1200자]")
    print(body_text[:1200])

    if source_key == "west":
        show_west_links(soup, url)

    total_checked += 1

assert total_checked == 5

# 원본 파일 및 인덱스 불변성 검증
assert MANIFEST.read_bytes() == manifest_raw
assert INDEX.read_bytes() == index_raw

print("\n===== STEP 64-03D 최종 결과 =====")
print("분석 HTML:", total_checked)
print("프로그램 본문 후보 식별:", identity_candidates)
print("추가 검토:", total_checked - identity_candidates)
print("HTML 5개 SHA-256:", "PASS")
print("Manifest / Index 불변:", "PASS")
print("공식 정책 내용의 최종 승인:", "미실행")
print("원본 HTML 수정:", "없음")
print("새 데이터 저장:", "없음")
print("Git 커밋·푸시:", "미실행")