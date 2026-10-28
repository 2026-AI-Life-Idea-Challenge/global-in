
from pathlib import Path
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
import hashlib
import json
import re


# ============================================================
# STEP 64-71
# 한국장학재단 WEST 공식 웹페이지 원문 보관
#
# - 공식 도메인만 허용
# - 실제 응답 바이트 보관
# - SHA-256 및 HTTP 응답 정보 기록
# - 기존 원본 덮어쓰기 금지
# - 정책 승인, 임베딩, Git 작업 수행하지 않음
# ============================================================

ROOT = Path(__file__).resolve().parents[5]

RAW_DIR = (
    ROOT
    / "data/raw/usa/employment/west/2026_second_half/kosaf"
)

PROCESSED = (
    ROOT
    / "data/processed/usa/employment/west/2026_second_half"
)

PREVIOUS = (
    PROCESSED
    / "west_2026_second_half_readiness_audit.json"
)

PREVIOUS_SHA = (
    "6b0c7fbfaf5552a952304c8d1e9e133"
    "5c10d32079c379176421d4844789753ec"
)

MANIFEST = RAW_DIR / "kosaf_source_manifest.json"

SOURCES = {
    "kosaf_2026_h2_notice": {
        "url": (
            "https://www.kosaf.go.kr/ko/notice.do"
            "?mode=view&page=3&seqNo=21036"
        ),
        "filename": "kosaf_2026_h2_notice.html",
        "required_phrases": [
            "2026년 하반기",
            "WEST",
            "어학연수비 대출신청",
            "2026.06.30",
            "학자금 지원구간",
        ],
    },
    "kosaf_west_loan_guide": {
        "url": (
            "https://www.kosaf.go.kr/ko/tuition.do"
            "?pg=PTHDWestAply_01M&ttab1=2"
        ),
        "filename": "kosaf_west_loan_guide.html",
        "required_phrases": [
            "WEST",
            "어학연수비",
            "대출",
        ],
    },
}

MAX_BYTES = 12 * 1024 * 1024


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_input(path, expected):
    if not path.is_file():
        raise FileNotFoundError(path)

    actual = sha256(path.read_bytes())

    if actual != expected:
        raise ValueError(
            f"기존 감사 파일 SHA-256 불일치: {path}\n"
            f"예상: {expected}\n실제: {actual}"
        )


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data):
        if self.ignored == 0:
            self.parts.append(data)


def visible_text(raw, content_type):
    charset = "utf-8"

    match = re.search(
        r"charset\s*=\s*['\"]?([\w-]+)",
        content_type,
        re.IGNORECASE,
    )
    if match:
        charset = match.group(1)

    try:
        html = raw.decode(charset, errors="replace")
    except LookupError:
        html = raw.decode("utf-8", errors="replace")

    # HTML 내부 charset 표기를 우선 확인
    meta = re.search(
        r"<meta[^>]+charset\s*=\s*['\"]?([\w-]+)",
        html[:5000],
        re.IGNORECASE,
    )

    if meta and meta.group(1).lower() != charset.lower():
        try:
            html = raw.decode(
                meta.group(1), errors="replace"
            )
        except LookupError:
            pass

    parser = TextExtractor()
    parser.feed(html)

    return re.sub(
        r"\s+", " ", " ".join(parser.parts)
    ).strip()


def compact(text):
    return re.sub(r"\s+", "", text).casefold()


def check_source_text(text, phrases, source_id):
    normalized = compact(text)

    if len(text) < 300:
        raise ValueError(
            f"{source_id}: 본문이 지나치게 짧음"
        )

    for phrase in phrases:
        if compact(phrase) not in normalized:
            raise ValueError(
                f"{source_id}: 예상 내용 없음 - {phrase}\n"
                "페이지 구조 변경 또는 접근 차단 가능성"
            )


def download(source_id, source):
    request = Request(
        source["url"],
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; WESTResearchArchive/1.0)"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Encoding": "identity",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            final_url = response.geturl()
            parsed = urlparse(final_url)

            if (
                parsed.scheme != "https"
                or not (
                    parsed.hostname == "kosaf.go.kr"
                    or parsed.hostname.endswith(".kosaf.go.kr")
                )
            ):
                raise ValueError(
                    f"{source_id}: 허용되지 않은 리디렉션 "
                    f"{final_url}"
                )

            content_type = response.headers.get(
                "Content-Type", ""
            )

            if "html" not in content_type.lower():
                raise ValueError(
                    f"{source_id}: HTML이 아닌 응답 "
                    f"{content_type}"
                )

            raw = response.read(MAX_BYTES + 1)

            if len(raw) > MAX_BYTES:
                raise ValueError(
                    f"{source_id}: 허용 용량 초과"
                )

            if not raw:
                raise ValueError(
                    f"{source_id}: 빈 응답"
                )

            text = visible_text(raw, content_type)

            check_source_text(
                text,
                source["required_phrases"],
                source_id,
            )

            return raw, {
                "source_id": source_id,
                "requested_url": source["url"],
                "final_url": final_url,
                "http_status": response.status,
                "content_type": content_type,
                "filename": source["filename"],
                "size_bytes": len(raw),
                "sha256": sha256(raw),
                "text_validation": "required_phrases_present",
                "policy_semantics_verified": False,
            }

    except (HTTPError, URLError) as exc:
        raise RuntimeError(
            f"{source_id}: 다운로드 실패 - {exc}"
        ) from exc


def encode(data):
    return (
        json.dumps(
            data, ensure_ascii=False, indent=2
        ) + "\n"
    ).encode("utf-8")


def save_new(path, raw):
    # 파일이 있으면 기존 내용을 절대 덮어쓰지 않음
    with path.open("xb") as handle:
        handle.write(raw)


print("===== STEP 64-71 한국장학재단 원문 보관 =====")

# 1. 앞 단계 확인
verify_input(PREVIOUS, PREVIOUS_SHA)

previous = json.loads(
    PREVIOUS.read_text(encoding="utf-8")
)

assert previous["program_id"] == "US-WEST-01"
assert previous["notice_period"] == "2026_second_half"
assert previous["approved_for_user_answers"] is False
assert previous["approved_for_embedding"] is False
assert previous["automatic_eligibility_rules_enabled"] is False

print("[PASS] STEP 64-69 감사 파일 SHA-256")

# 2. 기존 보관 결과가 있다면 변경하지 않고 검증
if MANIFEST.exists():
    saved_manifest = json.loads(
        MANIFEST.read_text(encoding="utf-8")
    )

    for entry in saved_manifest["sources"]:
        saved_file = RAW_DIR / entry["filename"]

        if not saved_file.is_file():
            raise FileNotFoundError(saved_file)

        if sha256(saved_file.read_bytes()) != entry["sha256"]:
            raise ValueError(
                f"저장된 원문 SHA-256 불일치: {saved_file}"
            )

    print("[PASS] 기존 보관 원문 SHA-256")
    print("[INFO] 기존 원본이 있어 재다운로드하지 않음")
    print("원본 변경: 없음")
    raise SystemExit(0)

# 부분 저장된 상태에서는 새 수집을 중단
for source in SOURCES.values():
    target = RAW_DIR / source["filename"]

    if target.exists():
        raise FileExistsError(
            f"manifest 없이 원문 파일이 존재함: {target}\n"
            "기존 파일을 먼저 확인하세요."
        )

# 3. 두 페이지 다운로드 및 원문 확인
# 다운로드가 모두 성공한 뒤에만 파일 생성
downloaded = {}
records = []

for source_id, source in SOURCES.items():
    raw, record = download(
        source_id, source
    )

    downloaded[source["filename"]] = raw
    records.append(record)

    print(
        f"[PASS] 원문 응답 검사: {source_id}"
    )
    print("바이트:", len(raw))
    print("SHA-256:", record["sha256"])

# 4. 원본 바이트 및 메타데이터 생성
manifest = {
    "dataset_type": "west_kosaf_official_raw_sources",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "captured_at_utc": datetime.now(
        timezone.utc
    ).isoformat(),
    "previous_audit_sha256": PREVIOUS_SHA,
    "source_count": len(records),
    "sources": records,
    "original_http_bodies_preserved": True,
    "manual_source_review_completed": False,
    "policy_semantics_verified": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

manifest_raw = encode(manifest)

RAW_DIR.mkdir(parents=True, exist_ok=True)

for filename in downloaded:
    if (RAW_DIR / filename).exists():
        raise FileExistsError(
            f"저장 직전 출력 충돌: {filename}"
        )

if MANIFEST.exists():
    raise FileExistsError(MANIFEST)

for filename, raw in downloaded.items():
    save_new(RAW_DIR / filename, raw)

save_new(MANIFEST, manifest_raw)

# 5. 보관 후 SHA-256 재검증
for record in records:
    path = RAW_DIR / record["filename"]

    if sha256(path.read_bytes()) != record["sha256"]:
        raise ValueError(
            f"저장 후 SHA-256 불일치: {path}"
        )

verify_input(PREVIOUS, PREVIOUS_SHA)

print("\n===== STEP 64-71 최종 결과 =====")
print("공식 원문 보관:", len(records))
print("원문별 SHA-256: 확인")
print("[PASS] CREATED:", MANIFEST.name)
print("manifest SHA-256:", sha256(manifest_raw))
print("기존 입력 변경: 없음")
print("정책 의미 검수: 미완료")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")