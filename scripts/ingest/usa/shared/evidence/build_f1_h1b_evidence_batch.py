
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa"
PROCESSED = ROOT / "data/processed/usa"

PROGRAMS = {
    "US-ST-01": {
        "folder": "student/f1_academic_student",
        "visa": "F-1",
        "registries": {
            "additional_official_sources.json":
                "f424945c5b67c8dee54565f8f3ce03d0690d88ec34c0036f7a6dc7c37c544c85",
            "alternative_official_sources.json": None,
        },
        "expected_sources": 2,
    },
    "US-EM-01": {
        "folder": "employment/h1b_specialty_occupations",
        "visa": "H-1B",
        "registries": {
            "additional_official_sources.json":
                "f46ab15e3d22d61190e990ed8fe4347f9d6fd3a455fd2cced4a860273768f149",
            "alternative_official_sources.json": None,
        },
        "expected_sources": 2,
    },
}

ALLOWED_HOSTS = {
    "studyinthestates.dhs.gov",
    "www.uscis.gov",
}

SOURCE_TYPES = {
    "school-search": "sevp_school_search",
    "students-and-the-form-i-20": "form_i20_guidance",
    "h-1b-specialty-occupations":
        "h1b_specialty_occupations_guidance",
    "h-1b-cap-season": "h1b_cap_season_guidance",
}

SKIP_TAGS = [
    "script", "style", "noscript",
    "nav", "footer", "header", "svg",
    "form",
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    return " ".join(text.split())


def serialize(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def safe_html_path(relative, expected_folder):
    path = ROOT / relative

    assert path.is_file()
    assert path.resolve().parent == expected_folder.resolve()
    assert path.suffix.lower() == ".html"

    return path


def get_records(registry):
    # STEP 64-17과 64-18의 필드명이 다르므로 정규화
    records = []

    for item in registry["sources"]:
        status = item.get(
            "collection_status",
            item.get("status")
        )

        if status != "collected_needs_review":
            continue

        records.append({
            "url": item["source_url"],
            "path": item.get(
                "local_file",
                item.get("local_path")
            ),
            "sha256": item["sha256"],
        })

    return records


def extract_html(path, record, program_id):
    raw = path.read_bytes()

    assert sha256(raw) == record["sha256"]

    soup = BeautifulSoup(raw, "html.parser")

    title = (
        normalize(soup.title.get_text(" ", strip=True))
        if soup.title
        else ""
    )

    # 원본을 보존하고 파싱 객체에서만 공통 UI 제거
    for tag in soup.select(", ".join(SKIP_TAGS)):
        tag.decompose()

    main = soup.find("main")
    article = soup.find("article")
    body = soup.find("body")

    selected = main or article or body or soup

    scope = (
        "main" if main is not None
        else "article" if article is not None
        else "body_fallback"
    )

    text = normalize(selected.get_text(" ", strip=True))

    assert len(text) >= 200, (
        f"본문이 지나치게 짧음: {path}"
    )

    headings = []
    for tag in selected.find_all(
        ["h1", "h2", "h3", "h4"]
    ):
        heading = normalize(
            tag.get_text(" ", strip=True)
        )
        if heading and heading not in headings:
            headings.append(heading)

    # 단락 및 목록을 근거 후보로 보존한다.
    # 실제 법적 조건이나 필수 여부는 판정하지 않는다.
    blocks = []
    seen = set()

    for tag in selected.find_all(["p", "li"]):
        # 상위 li와 하위 li 중복 방지
        if tag.name == "li" and tag.find("li"):
            continue

        content = normalize(
            tag.get_text(" ", strip=True)
        )

        if len(content) < 25:
            continue

        if content in seen:
            continue

        seen.add(content)

        blocks.append({
            "block_id": (
                f"{program_id}-BLOCK-{len(blocks)+1:04d}"
            ),
            "tag": tag.name,
            "source_text": content,
            "source_text_sha256": sha256(
                content.encode("utf-8")
            ),
            "semantic_review_status": "needs_review",
            "eligibility_rule_verified": False,
        })

    return {
        "source_url": record["url"],
        "source_file": path.relative_to(ROOT).as_posix(),
        "source_sha256": record["sha256"],
        "page_title": title,
        "extraction_scope": scope,
        "headings": headings,
        "body_text": text,
        "body_text_sha256": sha256(
            text.encode("utf-8")
        ),
        "evidence_block_count": len(blocks),
        "evidence_blocks": blocks,
        "content_validation_status": "needs_review",
    }


print("===== STEP 64-19 F-1 / H-1B 공식 근거 통합 구축 =====")

prepared = []
originals = {}
total_sources = 0

for program_id, config in PROGRAMS.items():
    folder = RAW / config["folder"]
    processed_folder = PROCESSED / config["folder"]

    assert folder.is_dir()
    assert processed_folder.is_dir()

    output = processed_folder / "official_evidence.json"
    assert not output.exists(), f"기존 파일 존재: {output}"

    records = []

    for name, expected_hash in config["registries"].items():
        registry_path = folder / name
        raw = registry_path.read_bytes()

        if expected_hash is not None:
            assert sha256(raw) == expected_hash, (
                f"출처 Registry SHA 불일치: {name}"
            )

        registry = json.loads(raw.decode("utf-8"))

        assert registry["program_id"] == program_id
        assert (
            registry["automatic_eligibility_rules_enabled"]
            is False
        )

        originals[registry_path] = sha256(raw)
        records.extend(get_records(registry))

    assert len(records) == config["expected_sources"]

    unique_urls = set()
    sources = []

    for record in records:
        url = record["url"]

        assert url not in unique_urls
        unique_urls.add(url)

        host = (urlparse(url).hostname or "").lower()
        assert host in ALLOWED_HOSTS

        path = safe_html_path(
            record["path"], folder
        )

        extracted = extract_html(
            path, record, program_id
        )

        source_type = next(
            (
                source_type
                for segment, source_type
                in SOURCE_TYPES.items()
                if segment in url
            ),
            "other_official_guidance",
        )

        extracted["source_type"] = source_type

        # URL에 맞는 실제 본문인지 검토할 신호
        searchable = (
            extracted["page_title"]
            + " "
            + extracted["body_text"]
        ).casefold()

        if program_id == "US-ST-01":
            identifiers = (
                ["school", "sevp"]
                if source_type == "sevp_school_search"
                else ["i-20", "student"]
            )
        else:
            identifiers = ["h-1b", "specialty"]

        found = [
            word for word in identifiers
            if word.casefold() in searchable
        ]

        extracted["identity_keywords_found"] = found
        extracted["identity_review_status"] = (
            "candidate_matched"
            if found
            else "requires_manual_review"
        )

        sources.append(extracted)
        originals[path] = record["sha256"]

        print(
            f"[PASS] {program_id} | {source_type}"
            f" | 본문 {len(extracted['body_text'])}자"
            f" | 근거 블록 {extracted['evidence_block_count']}개"
            f" | 식별 {extracted['identity_review_status']}"
        )

    data = {
        "dataset_type": "usa_program_official_evidence",
        "country": "US",
        "program_id": program_id,
        "visa_classification": config["visa"],
        "source_count": len(sources),
        "sources": sources,
        "extraction_method": "html_main_article_body",
        "source_identity_verified": False,
        "section_semantics_verified": False,
        "eligibility_rules_verified": False,
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    payload = serialize(data)
    assert payload == serialize(data)

    prepared.append((output, payload, data))
    total_sources += len(sources)

assert len(prepared) == 2
assert total_sources == 4

print("[PASS] 공식 HTML 4개 추출 및 근거 JSON 준비")

# 기존 출력 파일 충돌 사전 검사
for path, _, _ in prepared:
    assert not path.exists()
    assert path.parent.is_dir()

# 저장 후 재읽기·해시 대조
for path, payload, data in prepared:
    with path.open("xb") as file:
        file.write(payload)

    assert path.read_bytes() == payload
    assert json.loads(
        path.read_text(encoding="utf-8")
    ) == data

print("[PASS] 프로그램별 근거 JSON 2개 저장")
print("[PASS] JSON SHA-256 및 재현성")

# 모든 입력 파일 불변성 확인
for path, old_sha in originals.items():
    assert sha256(path.read_bytes()) == old_sha

print("[PASS] 기존 공식 원본·출처 Registry 불변")

print("\n===== STEP 64-19 최종 결과 =====")

for path, payload, data in prepared:
    print(
        data["program_id"],
        "| 출처:", data["source_count"],
        "| 근거 블록:",
        sum(
            source["evidence_block_count"]
            for source in data["sources"]
        ),
    )
    print("출력:", path.relative_to(ROOT))
    print("SHA-256:", sha256(payload))

    for source in data["sources"]:
        print(
            " -",
            source["source_type"],
            "|",
            source["identity_review_status"],
            "|",
            source["page_title"][:100],
        )

print("처리 프로그램: 2")
print("처리 HTML: 4")
print("출력 JSON: 2")
print("기존 데이터 변경: 없음")
print("정책·의미 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")