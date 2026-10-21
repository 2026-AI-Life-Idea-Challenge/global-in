
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa"

PROGRAMS = {
    "US-ST-01": {
        "folder": "student/f1_academic_student",
        "visa": "F-1",
        "sources": [
            {
                "agency": "U.S. Department of State",
                "url": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
            },
            {
                "agency": "U.S. Department of Homeland Security",
                "url": "https://studyinthestates.dhs.gov/school-search",
            },
        ],
    },
    "US-EM-01": {
        "folder": "employment/h1b_specialty_occupations",
        "visa": "H-1B",
        "sources": [
            {
                "agency": "U.S. Department of Labor",
                "url": "https://www.dol.gov/agencies/eta/foreign-labor/programs/h-1b",
            },
            {
                "agency": "U.S. Citizenship and Immigration Services",
                "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations-and-fashion-models",
            },
        ],
    },
}

ALLOWED_HOSTS = {
    "travel.state.gov",
    "studyinthestates.dhs.gov",
    "www.dol.gov",
    "www.uscis.gov",
}

HEADERS = {
    "User-Agent": "Global-In-OfficialSourceCollector/1.0",
    "Accept": "text/html,application/xhtml+xml",
}

MAX_BYTES = 5 * 1024 * 1024


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def serialize(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def collect(url):
    with requests.get(
        url,
        headers=HEADERS,
        timeout=(10, 30),
        stream=True,
        allow_redirects=True,
    ) as response:

        final_url = response.url
        host = (urlparse(final_url).hostname or "").lower()
        content_type = response.headers.get(
            "Content-Type", ""
        )
        status = response.status_code

        metadata = {
            "http_status": status,
            "final_url": final_url,
            "content_type": content_type,
        }

        if status != 200:
            return None, metadata, f"http_{status}"

        if host not in ALLOWED_HOSTS:
            return None, metadata, "unexpected_redirect"

        if "text/html" not in content_type.lower():
            return None, metadata, "unexpected_content_type"

        chunks = []
        size = 0

        for chunk in response.iter_content(65536):
            if not chunk:
                continue

            size += len(chunk)

            if size > MAX_BYTES:
                return None, metadata, "size_limit_exceeded"

            chunks.append(chunk)

        raw = b"".join(chunks)

        if len(raw) < 500:
            return None, metadata, "suspiciously_small"

        soup = BeautifulSoup(raw, "html.parser")

        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title
            else ""
        )

        body = soup.body
        body_text = (
            body.get_text(" ", strip=True)
            if body
            else ""
        )

        # 확인 가능한 원문 텍스트인지 최소 검사.
        # 오류 페이지 여부의 최종 판정은 별도 검토 필요.
        if len(body_text) < 300:
            return None, metadata, "insufficient_body_text"

        metadata["title"] = title
        metadata["body_characters"] = len(body_text)
        metadata["bytes"] = len(raw)
        metadata["sha256"] = sha256(raw)

        return raw, metadata, "collected_needs_review"


print("===== STEP 64-17 F-1 / H-1B 공식 자료 수집 =====")

# 1. 기존 폴더 및 출처 Registry 확인
for program_id, config in PROGRAMS.items():
    folder = RAW / config["folder"]
    registry = folder / "official_sources.json"

    assert folder.is_dir()
    assert registry.is_file()

    data = json.loads(
        registry.read_text(encoding="utf-8")
    )

    assert data["program_id"] == program_id

print("[PASS] 기존 F-1 / H-1B 프로그램 폴더 확인")

prepared = []

# 2. 공식 URL 4개 일괄 확인
for program_id, config in PROGRAMS.items():
    folder = RAW / config["folder"]
    records = []

    print(f"\n[{program_id}]")

    for index, item in enumerate(config["sources"], 1):
        url = item["url"]
        initial_host = (
            urlparse(url).hostname or ""
        ).lower()

        assert initial_host in ALLOWED_HOSTS

        filename = f"official_source_{index:02d}.html"
        target = folder / filename

        try:
            raw, metadata, status = collect(url)
        except requests.RequestException as exc:
            raw = None
            status = "request_error"
            metadata = {
                "error_type": type(exc).__name__,
            }
        except Exception as exc:
            raw = None
            status = "collection_error"
            metadata = {
                "error_type": type(exc).__name__,
            }

        record = {
            "agency": item["agency"],
            "source_url": url,
            "collection_status": status,
            "local_file": (
                target.relative_to(ROOT).as_posix()
                if raw is not None
                else None
            ),
            "sha256": (
                sha256(raw) if raw is not None else None
            ),
            "response": metadata,
            "validation_status": "needs_review",
        }

        records.append(record)

        if raw is not None:
            prepared.append((target, raw))

        print(
            index,
            status,
            metadata.get("http_status", "N/A"),
        )

    report = {
        "dataset_type": "additional_official_sources",
        "country": "US",
        "program_id": program_id,
        "visa_classification": config["visa"],
        "source_count": len(records),
        "collected_count": sum(
            r["collection_status"]
            == "collected_needs_review"
            for r in records
        ),
        "sources": records,
        "collected_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
    }

    prepared.append((
        folder / "additional_official_sources.json",
        serialize(report),
    ))

# 3. 모든 파일 저장 전 충돌 검사
paths = [path for path, _ in prepared]

assert len(paths) == len(set(paths))

for path, raw in prepared:
    assert path.parent.is_dir()
    assert not path.exists(), (
        f"기존 출력 파일이 있습니다: {path}"
    )

print("\n[PASS] 기존 파일 덮어쓰기 방지")

# 4. 저장 및 검증
for path, raw in prepared:
    with path.open("xb") as file:
        file.write(raw)

    assert sha256(path.read_bytes()) == sha256(raw)

print("[PASS] 신규 자료 저장 및 SHA-256")

# 5. 최종 결과
print("\n===== STEP 64-17 최종 결과 =====")

for program_id, config in PROGRAMS.items():
    path = (
        RAW / config["folder"]
        / "additional_official_sources.json"
    )

    report = json.loads(
        path.read_text(encoding="utf-8")
    )

    print(
        program_id,
        "| 출처:",
        report["source_count"],
        "| HTML 수집:",
        report["collected_count"],
    )

    for item in report["sources"]:
        print(
            " -",
            item["collection_status"],
            item["source_url"],
        )

    print("Registry SHA-256:", sha256(path.read_bytes()))

print("기존 원본 변경: 없음")
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")