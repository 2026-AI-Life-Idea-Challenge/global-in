
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
import hashlib
import json
import re
import sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print(
        "필요 패키지 설치: "
        "python -m pip install requests beautifulsoup4"
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[4]

RAW = (
    ROOT / "data/raw/usa/employment/west"
    / "2026_second_half"
)

PAGE_FILE = RAW / "official_notice_page.html"
PDF_FILE = RAW / "west_2026_second_half_notice.pdf"
MANIFEST = RAW / "source_manifest.json"

URL = (
    "https://www.niied.go.kr/web/main/"
    "nid/niied_board/5749"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 "
                  "(Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

EXPECTED_TITLE = "2026년 하반기 WEST 참가자 모집 공고"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def save_immutable(path, data):
    if path.exists():
        if path.read_bytes() == data:
            return "EXISTS_VERIFIED"

        raise RuntimeError(
            f"기존 파일과 내용이 다릅니다: {path}\n"
            "기존 공식 원본은 덮어쓰지 않습니다."
        )

    with path.open("xb") as f:
        f.write(data)

    assert path.read_bytes() == data
    return "CREATED"


def collect_attachment_candidates(soup):
    found = []
    seen = set()

    for anchor in soup.find_all("a"):
        label = anchor.get_text(
            " ", strip=True
        )

        href = anchor.get("href", "")
        onclick = anchor.get("onclick", "")

        combined = " ".join(
            [label, href, onclick]
        )

        # 모집 공고문 첨부파일을 찾기 위한 후보 수집.
        # JS 다운로드 링크도 기록하되 URL로 가정하지 않음.
        if not (
            "WEST" in combined.upper()
            or "공고문" in combined
            or ".pdf" in combined.lower()
        ):
            continue

        key = (label, href, onclick)

        if key in seen:
            continue

        seen.add(key)

        direct_url = None

        if href and not href.lower().startswith(
            ("javascript:", "#")
        ):
            direct_url = urljoin(URL, href)

        found.append({
            "label": label,
            "href": href,
            "onclick": onclick,
            "direct_url_candidate": direct_url,
        })

    return found


print("===== STEP 64-35 하반기 WEST 공식 자료 수집 =====")

RAW.mkdir(parents=True, exist_ok=True)

# 1. 기존 파일이 있으면 다운로드 대신 보존된 원본 사용
if PAGE_FILE.exists():
    page_data = PAGE_FILE.read_bytes()
    page_state = "EXISTS_VERIFIED"
else:
    try:
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        page_data = response.content

    except requests.RequestException as exc:
        print("[REVIEW] 공식 게시물 다운로드 실패")
        print(type(exc).__name__, str(exc)[:300])
        print("기존 데이터 변경: 없음")
        sys.exit(0)

    page_state = save_immutable(
        PAGE_FILE, page_data
    )

print("[PASS] 공식 게시물:", page_state)
print("HTML SHA-256:", sha256(page_data))

# 2. 게시물 식별
soup = BeautifulSoup(page_data, "html.parser")
page_text = soup.get_text(" ", strip=True)

title_found = EXPECTED_TITLE in page_text
date_found = (
    "2026-06-26" in page_text
    or "2026.06.26" in page_text
    or "2026. 6. 26" in page_text
)

if not title_found:
    print("[REVIEW] 예상 공고 제목을 HTML에서 확인하지 못함")

print("공고 제목 확인:", title_found)
print("공고일 확인:", date_found)

# 3. 첨부파일 후보 식별
attachments = collect_attachment_candidates(soup)

print("\n[첨부파일 후보]")
for i, item in enumerate(attachments, 1):
    print(i, "|", item["label"][:100])
    print("   href:", item["href"][:150])
    print("   onclick:", item["onclick"][:150])

# 4. 직접 PDF 후보 탐색
pdf_download_status = "not_downloaded"
pdf_sha = None
selected_url = None
pdf_bytes = None

# 정확히 모집 공고문임을 알 수 있는 후보만 사용
eligible = [
    item for item in attachments
    if (
        "공고문" in item["label"]
        and item["direct_url_candidate"]
        and (
            ".pdf" in item["direct_url_candidate"].lower()
        )
    )
]

# 중복 URL 제거
urls = list(dict.fromkeys(
    item["direct_url_candidate"]
    for item in eligible
))

# 유일한 PDF URL이 확인된 경우만 자동 다운로드
if len(urls) == 1:
    candidate_url = urls[0]

    if urlparse(candidate_url).scheme == "https":
        try:
            response = requests.get(
                candidate_url,
                headers=HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            candidate_data = response.content

            if (
                candidate_data.startswith(b"%PDF-")
                and len(candidate_data) > 1000
            ):
                pdf_bytes = candidate_data
                selected_url = candidate_url
                pdf_download_status = "verified_pdf_bytes"

            else:
                pdf_download_status = "not_pdf_response"

        except requests.RequestException:
            pdf_download_status = "download_failed"

elif len(urls) > 1:
    pdf_download_status = "ambiguous_attachment_urls"
else:
    pdf_download_status = "manual_attachment_required"

# 5. PDF는 검증된 경우에만 저장
if PDF_FILE.exists():
    existing = PDF_FILE.read_bytes()

    assert existing.startswith(b"%PDF-")

    if pdf_bytes is not None:
        assert existing == pdf_bytes, (
            "기존 PDF와 신규 다운로드 PDF가 다릅니다."
        )

    pdf_sha = sha256(existing)
    pdf_download_status = "existing_pdf_preserved"

elif pdf_bytes is not None:
    save_immutable(PDF_FILE, pdf_bytes)
    pdf_sha = sha256(pdf_bytes)

# 6. 회차별 출처 기록
manifest = {
    "dataset_type": "west_official_source_snapshot",
    "country": "US",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "official_notice_url": URL,
    "official_notice_title": EXPECTED_TITLE,
    "notice_date_candidate": "2026-06-26",
    "title_found_in_html": title_found,
    "notice_date_found_in_html": date_found,
    "html_path": (
        PAGE_FILE.relative_to(ROOT).as_posix()
    ),
    "html_sha256": sha256(page_data),
    "pdf_path": (
        PDF_FILE.relative_to(ROOT).as_posix()
        if pdf_sha else None
    ),
    "pdf_sha256": pdf_sha,
    "pdf_source_url": selected_url,
    "pdf_download_status": pdf_download_status,
    "attachment_candidates": attachments,
    "source_collection_status": (
        "pdf_collected"
        if pdf_sha else "pdf_pending"
    ),
    "semantic_review_status": "needs_review",
    "approved_for_embedding": False,
    "approved_for_user_answers": False,
    "automatic_eligibility_rules_enabled": False,
}

payload = json_bytes(manifest)
state = save_immutable(MANIFEST, payload)

assert json.loads(
    MANIFEST.read_text(encoding="utf-8")
) == manifest

assert sha256(PAGE_FILE.read_bytes()) == sha256(
    page_data
)

if pdf_sha:
    assert sha256(
        PDF_FILE.read_bytes()
    ) == pdf_sha

print("\n===== STEP 64-35 최종 결과 =====")
print("공식 게시물:", URL)
print("HTML 보존: PASS")
print("공고 제목 확인:", title_found)
print("공고일 확인:", date_found)
print("첨부 후보:", len(attachments))
print("PDF 상태:", pdf_download_status)
print("PDF SHA-256:", pdf_sha)
print("Manifest:", MANIFEST.relative_to(ROOT))
print("Manifest 상태:", state)
print("Manifest SHA-256:", sha256(payload))
print("상반기 기존 데이터 변경: 없음")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")