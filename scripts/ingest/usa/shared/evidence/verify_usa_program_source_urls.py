
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[5]

MANIFEST = (
    ROOT / "data/raw/usa/usa_program_source_manifest.json"
)

EXPECTED_SHA = (
    "52489441fd37a75b07045d9a252a478"
    "9a144fc65d19275da8a9ca05620adaf31"
)

ALLOWED_HOSTS = {
    "j1visa.state.gov",
    "travel.state.gov",
    "niied.go.kr",
    "www.niied.go.kr",
}

HEADERS = {
    "User-Agent": (
        "Global-In-SourceAudit/1.0 "
        "(official public-page metadata check)"
    ),
    "Accept": "text/html,application/pdf,*/*",
}

TIMEOUT = (8, 15)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def audit_url(url):
    result = {
        "url": url,
        "status_code": None,
        "final_url": None,
        "content_type": None,
        "redirect_count": None,
        "classification": None,
        "error": None,
    }

    try:
        # GET을 사용하되 응답 본문은 내려받지 않음
        with requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as response:
            result["status_code"] = response.status_code
            result["final_url"] = response.url
            result["redirect_count"] = len(response.history)

            content_type = response.headers.get(
                "Content-Type", ""
            )
            result["content_type"] = content_type

            final_host = (
                urlparse(response.url).hostname or ""
            ).lower()

            if final_host not in ALLOWED_HOSTS:
                result["classification"] = (
                    "unexpected_redirect_host"
                )

            elif response.status_code == 200:
                result["classification"] = "http_200"

            elif response.status_code in {403, 429}:
                result["classification"] = (
                    "access_restricted"
                )

            elif 500 <= response.status_code <= 599:
                result["classification"] = "server_error"

            else:
                result["classification"] = (
                    "needs_manual_review"
                )

    except requests.RequestException as exc:
        result["classification"] = "request_error"
        result["error"] = type(exc).__name__

    return result


print("===== STEP 64-03B 공식 출처 URL 검증 =====")

assert MANIFEST.is_file(), "Manifest 파일 없음"

original_bytes = MANIFEST.read_bytes()

assert sha256(original_bytes) == EXPECTED_SHA, (
    "Manifest SHA-256 불일치"
)

manifest = json.loads(
    original_bytes.decode("utf-8")
)

assert manifest["program_count"] == 7
assert manifest["source_link_count"] == 12
assert manifest["unique_source_url_count"] == 9

assert manifest["validation_status"] == "needs_review"
assert manifest["automatic_eligibility_rules_enabled"] is False

print("[PASS] Manifest SHA-256 및 구조")

url_programs = {}

for program in manifest["programs"]:
    for source in program["sources"]:
        url = source["url"]

        host = (urlparse(url).hostname or "").lower()

        assert host in ALLOWED_HOSTS, (
            f"허용되지 않은 출처 호스트: {host}"
        )

        url_programs.setdefault(url, []).append(
            program["program_id"]
        )

assert len(url_programs) == 9
assert sum(len(ids) for ids in url_programs.values()) == 12

print("[PASS] 출처 연결 12개 / 고유 URL 9개")

results = []

for index, (url, program_ids) in enumerate(
    url_programs.items(), start=1
):
    print(f"\n[{index}/9] {url}")

    result = audit_url(url)
    result["program_ids"] = program_ids
    results.append(result)

    print("HTTP:", result["status_code"])
    print("최종 URL:", result["final_url"])
    print("응답 유형:", result["content_type"])
    print("리다이렉트:", result["redirect_count"])
    print("분류:", result["classification"])

    if result["error"]:
        print("네트워크 오류 유형:", result["error"])

counts = Counter(
    item["classification"] for item in results
)

print("\n===== URL 검증 요약 =====")

for name in sorted(counts):
    print(f"{name}: {counts[name]}")

print("전체 URL:", len(results))
print(
    "접근성 확인 HTTP 200:",
    counts["http_200"],
)
print(
    "추가 검토 대상:",
    len(results) - counts["http_200"],
)

# 모든 기존 데이터가 바뀌지 않았는지 확인
assert MANIFEST.read_bytes() == original_bytes
assert sha256(MANIFEST.read_bytes()) == EXPECTED_SHA

print("\n[PASS] Manifest 불변")
print("[PASS] 기존 JSON 수정 없음")
print("[PASS] 응답 본문 저장 없음")
print("[PASS] 자동 자격 판정 비활성화")
print("Git 커밋·푸시: 미실행")

print("\n===== STEP 64-03B 완료 =====")