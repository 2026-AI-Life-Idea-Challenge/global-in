
from pathlib import Path
from urllib.parse import urlparse
from html.parser import HTMLParser
from datetime import datetime, timezone
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/raw/usa"

MANIFEST = BASE / "usa_program_source_manifest.json"
OUTPUT_DIR = BASE / "source_snapshots"

EXPECTED_MANIFEST_SHA = (
    "52489441fd37a75b07045d9a252a478"
    "9a144fc65d19275da8a9ca05620adaf31"
)

TARGET_URLS = {
    "https://j1visa.state.gov/programs/summer-work-travel/",
    "https://j1visa.state.gov/programs/college-and-university-student/",
    "https://j1visa.state.gov/programs/intern/",
    "https://j1visa.state.gov/programs/trainee/",
    "https://www.niied.go.kr/web/main/nid/niied_board/5570",
}

ALLOWED_HOSTS = {
    "j1visa.state.gov",
    "www.niied.go.kr",
}


class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.parts.append(data)

    def get_title(self):
        return " ".join("".join(self.parts).split())


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def url_key(url):
    return sha256(url.encode("utf-8"))[:16]


print("===== STEP 64-03C 공식 HTML 수집 =====")

manifest_bytes = MANIFEST.read_bytes()

if sha256(manifest_bytes) != EXPECTED_MANIFEST_SHA:
    raise ValueError("원본 manifest SHA-256 불일치")

manifest = json.loads(manifest_bytes.decode("utf-8"))

url_programs = {}

for program in manifest["programs"]:
    for source in program["sources"]:
        url_programs.setdefault(
            source["url"], []
        ).append(program["program_id"])

if not TARGET_URLS.issubset(set(url_programs)):
    raise ValueError("대상 URL이 manifest에 포함되지 않았습니다")
if len(TARGET_URLS) != 5:
    raise ValueError("수집 대상 URL 개수가 5개가 아닙니다")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

index_path = OUTPUT_DIR / "snapshot_index.json"

# 재실행으로 기존 스냅샷이 덮어써지는 것을 방지
if index_path.exists():
    raise FileExistsError(
    "기존 snapshot_index.json이 존재합니다. "
    "원본을 보존하고 먼저 상태를 확인하세요."
)

for url in TARGET_URLS:
    path = OUTPUT_DIR / f"{url_key(url)}.html"
    if path.exists():
        raise FileExistsError(f"기존 스냅샷 존재: {path}")

print("[PASS] Manifest SHA-256")
print("[PASS] 대상 공식 URL 5개 확인")
print("[PASS] 기존 스냅샷 덮어쓰기 방지")

HEADERS = {
    "User-Agent": "Global-In-OfficialSourceCollector/1.0",
    "Accept": "text/html,application/xhtml+xml",
}

# 먼저 응답을 메모리에서 검사한 뒤 저장
downloads = []
failures = []

for number, url in enumerate(sorted(TARGET_URLS), 1):
    print(f"\n[{number}/5] {url}")

    try:
        with requests.get(
            url,
            headers=HEADERS,
            timeout=(8, 25),
            allow_redirects=True,
            stream=True,
        ) as response:

            status = response.status_code
            final_url = response.url
            host = (urlparse(final_url).hostname or "").lower()
            content_type = response.headers.get(
                "Content-Type", ""
            )

            if (
                status != 200
                or host not in ALLOWED_HOSTS
                or "text/html" not in content_type.lower()
            ):
                failures.append({
                    "url": url,
                    "status": status,
                    "final_url": final_url,
                    "content_type": content_type,
                })
                print("[REVIEW] 예상과 다른 응답")
                continue

            # 안전을 위해 수집 크기를 5MB로 제한
            max_bytes = 5 * 1024 * 1024
            chunks = []
            total = 0

            for chunk in response.iter_content(65536):
                if not chunk:
                    continue

                total += len(chunk)

                if total > max_bytes:
                    raise ValueError("HTML 크기 5MB 초과")

                chunks.append(chunk)

            raw = b"".join(chunks)

            if len(raw) < 500:
                raise ValueError("HTML 응답 크기가 비정상적으로 작음")

            encoding = response.encoding or "utf-8"
            html_text = raw.decode(encoding, errors="replace")

            parser = TitleParser()
            parser.feed(html_text)

            title = parser.get_title()

            item = {
                "source_url": url,
                "final_url": final_url,
                "program_ids": url_programs[url],
                "status_code": status,
                "content_type": content_type,
                "title": title,
                "bytes": len(raw),
                "sha256": sha256(raw),
                "collected_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "content_validation_status": "needs_review",
                "raw": raw,
            }

            downloads.append(item)

            print("[PASS] HTTP 200 / HTML 응답")
            print("Title:", title)
            print("Bytes:", len(raw))
            print("SHA-256:", item["sha256"])

    except (requests.RequestException, ValueError) as exc:
        failures.append({
            "url": url,
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:250],
        })
        print("[REVIEW] 수집 실패:", type(exc).__name__)

# 모든 다운로드가 완료된 경우에만 저장
if failures or len(downloads) != 5:
    print("\n===== 저장 보류 =====")
    print("수집 성공:", len(downloads))
    print("추가 검토:", len(failures))

    for failure in failures:
        print(failure)

    print("기존 데이터 변경: 없음")
    print("신규 HTML 저장: 없음")
    raise SystemExit(1)

index = {
    "dataset_id": "USA_OFFICIAL_HTML_SNAPSHOTS_V1",
    "source_manifest_sha256": EXPECTED_MANIFEST_SHA,
    "snapshot_count": len(downloads),
    "validation_status": "needs_review",
    "snapshots": [],
}

for item in downloads:
    filename = f"{url_key(item['source_url'])}.html"
    output_path = OUTPUT_DIR / filename

    with output_path.open("xb") as f:
        f.write(item["raw"])

    if output_path.read_bytes() != item["raw"]:
        raise IOError(f"스냅샷 저장 후 검증 실패: {output_path}")

    metadata = {
        key: value
        for key, value in item.items()
        if key != "raw"
    }

    metadata["filename"] = filename
    index["snapshots"].append(metadata)

index_payload = (
    json.dumps(index, ensure_ascii=False, indent=2)
    + "\n"
).encode("utf-8")

with index_path.open("xb") as f:
    f.write(index_payload)

if json.loads(
    index_path.read_text(encoding="utf-8")
) != index:
    raise IOError("스냅샷 Index 저장 후 검증 실패")


for snapshot in index["snapshots"]:
    path = OUTPUT_DIR / snapshot["filename"]

    if sha256(path.read_bytes()) != snapshot["sha256"]:
        raise IOError(f"스냅샷 SHA-256 저장 후 검증 실패: {path}")

if MANIFEST.read_bytes() != manifest_bytes:
    raise IOError("수집 중 Manifest가 변경됐습니다")

print("\n===== STEP 64-03C 최종 결과 =====")
print("[PASS] 공식 HTML 5개 저장")
print("[PASS] 모든 HTML SHA-256 검증")
print("[PASS] 스냅샷 Index 저장")
print("[PASS] 기존 Manifest 불변")

print("수집 HTML:", len(downloads))
print(
    "저장 위치:",
    OUTPUT_DIR.relative_to(ROOT),
)
print("Index SHA-256:", sha256(index_payload))
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")