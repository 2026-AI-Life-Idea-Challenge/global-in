
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa"

SOURCES = {
    "US-ST-01": {
        "folder": "student/f1_academic_student",
        "urls": [
            (
                "DHS Form I-20",
                "https://studyinthestates.dhs.gov/students/prepare/students-and-the-form-i-20",
            ),
        ],
    },
    "US-EM-01": {
        "folder": "employment/h1b_specialty_occupations",
        "urls": [
            (
                "USCIS H-1B Specialty Occupations",
                "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
            ),
            (
                "USCIS H-1B Cap Season",
                "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations/h-1b-cap-season",
            ),
        ],
    },
}

ALLOWED_HOSTS = {
    "studyinthestates.dhs.gov",
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


def fetch(url):
    metadata = {
        "http_status": None,
        "final_url": None,
        "content_type": None,
        "title": None,
        "body_length": None,
    }

    try:
        with requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 30),
            stream=True,
            allow_redirects=True,
        ) as response:

            metadata["http_status"] = response.status_code
            metadata["final_url"] = response.url
            metadata["content_type"] = response.headers.get(
                "Content-Type", ""
            )

            host = (
                urlparse(response.url).hostname or ""
            ).lower()

            if host not in ALLOWED_HOSTS:
                return None, metadata, "unexpected_redirect_host"

            if response.status_code != 200:
                return (
                    None,
                    metadata,
                    f"http_{response.status_code}",
                )

            if "text/html" not in (
                metadata["content_type"].lower()
            ):
                return None, metadata, "unexpected_content_type"

            chunks = []
            total = 0

            for chunk in response.iter_content(65536):
                if not chunk:
                    continue

                total += len(chunk)

                if total > MAX_BYTES:
                    return None, metadata, "size_limit_exceeded"

                chunks.append(chunk)

            raw = b"".join(chunks)

            if len(raw) < 500:
                return None, metadata, "insufficient_response"

            soup = BeautifulSoup(raw, "html.parser")

            title = (
                soup.title.get_text(" ", strip=True)
                if soup.title
                else ""
            )

            body_text = (
                soup.body.get_text(" ", strip=True)
                if soup.body
                else ""
            )

            metadata["title"] = title
            metadata["body_length"] = len(body_text)

            if len(body_text) < 300:
                return None, metadata, "insufficient_body"

            return raw, metadata, "collected_needs_review"

    except requests.RequestException as exc:
        metadata["error_type"] = type(exc).__name__
        return None, metadata, "request_error"


print("===== STEP 64-18 대체 공식 출처 일괄 수집 =====")

# 1. 기존 프로그램별 파일 확인
originals = {}

for program_id, config in SOURCES.items():
    folder = RAW / config["folder"]

    old_registry = (
        folder / "additional_official_sources.json"
    )

    assert folder.is_dir()
    assert old_registry.is_file()

    raw = old_registry.read_bytes()
    registry = json.loads(raw.decode("utf-8"))

    assert registry["program_id"] == program_id
    assert (
        registry["automatic_eligibility_rules_enabled"]
        is False
    )

    originals[old_registry] = sha256(raw)

print("[PASS] 기존 출처 기록 확인")

prepared = []
summary = {}

# 2. 공식 URL 전체 확인
for program_id, config in SOURCES.items():
    folder = RAW / config["folder"]
    records = []

    print(f"\n[{program_id}]")

    for number, (name, url) in enumerate(
        config["urls"], 1
    ):
        host = (urlparse(url).hostname or "").lower()
        assert host in ALLOWED_HOSTS

        raw, metadata, status = fetch(url)

        key = sha256(url.encode("utf-8"))[:12]
        filename = f"official_source_alt_{key}.html"
        target = folder / filename

        record = {
            "source_name": name,
            "source_url": url,
            "status": status,
            "response": metadata,
            "local_path": (
                target.relative_to(ROOT).as_posix()
                if raw is not None
                else None
            ),
            "sha256": (
                sha256(raw)
                if raw is not None
                else None
            ),
            "validation_status": "needs_review",
        }

        records.append(record)

        if raw is not None:
            prepared.append((target, raw))

        print(
            number,
            status,
            metadata["http_status"],
            name,
        )
        print("최종 URL:", metadata["final_url"])

    report = {
        "dataset_type": "alternative_official_sources",
        "country": "US",
        "program_id": program_id,
        "source_count": len(records),
        "collected_count": sum(
            item["status"] == "collected_needs_review"
            for item in records
        ),
        "checked_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "sources": records,
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
    }

    report_path = (
        folder / "alternative_official_sources.json"
    )

    prepared.append((report_path, serialize(report)))
    summary[program_id] = report

# 3. 저장 전 충돌·경로 확인
paths = [path for path, _ in prepared]

assert len(paths) == len(set(paths))

for path, raw in prepared:
    assert path.parent.is_dir()
    assert path.resolve().is_relative_to(
        RAW.resolve()
    )
    assert not path.exists(), (
        f"기존 파일이 존재합니다: {path}"
    )

print("\n[PASS] 저장 경로 및 덮어쓰기 방지")

# 4. 저장 및 검증
for path, raw in prepared:
    with path.open("xb") as file:
        file.write(raw)

    assert sha256(path.read_bytes()) == sha256(raw)

print("[PASS] 신규 파일 저장 및 SHA-256 검증")

# 5. 기존 파일 불변성 검사
for path, old_sha in originals.items():
    assert sha256(path.read_bytes()) == old_sha

print("[PASS] 기존 출처 기록 불변")

# 6. 결과 요약
print("\n===== STEP 64-18 최종 결과 =====")

for program_id, report in summary.items():
    print(
        program_id,
        "| 검사:",
        report["source_count"],
        "| HTML 수집:",
        report["collected_count"],
    )

    for item in report["sources"]:
        print(
            " -",
            item["status"],
            item["source_url"],
        )

print(
    "총 수집 HTML:",
    sum(
        report["collected_count"]
        for report in summary.values()
    )
)
print("기존 파일 변경: 없음")
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")