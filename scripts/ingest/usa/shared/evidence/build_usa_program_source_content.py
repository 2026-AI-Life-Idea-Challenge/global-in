
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urljoin
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa"
PROCESSED = ROOT / "data/processed/usa"

MANIFEST = RAW / "usa_program_source_manifest.json"
INDEX = RAW / "source_snapshots/snapshot_index.json"
MAPPING = (
    RAW / "shared/source_manifest"
    / "usa_program_snapshot_mapping.json"
)

EXPECTED_HASHES = {
    MANIFEST: "52489441fd37a75b07045d9a252a4789a144fc65d19275da8a9ca05620adaf31",
    INDEX: "7db1f2c5b0b1b4a63c4db1355791880fec1ef851e253b61f756a899395c97831",
    MAPPING: "3f62fad51e20449940bb02cd0f6b0ebd84e83944586973f00600a35cbae34e4d",
}

EXPECTED_PROGRAMS = {
    "US-WH-01": "Summer Work Travel",
    "US-ST-03": "College and University Student",
    "US-EM-02": "Intern",
    "US-EM-03": "Trainee",
    "US-WEST-01": "2026년 상반기 WEST 참가자 모집 공고",
}

SKIP_TAGS = {
    "script", "style", "noscript", "nav",
    "footer", "header", "svg", "form",
}

HEADING_TAGS = {"h1", "h2", "h3", "h4"}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def normalized(text):
    return " ".join(text.split())


def read_json_verified(path):
    assert path.is_file(), f"파일 없음: {path}"
    raw = path.read_bytes()
    assert sha256(raw) == EXPECTED_HASHES[path], (
        f"SHA 불일치: {path}"
    )
    return json.loads(raw.decode("utf-8")), raw


def inside_excluded_tag(node):
    parent = node.parent

    while parent is not None:
        if isinstance(parent, Tag):
            if parent.name in SKIP_TAGS:
                return True
        parent = parent.parent

    return False


def heading_sections(soup, expected_heading):
    """
    프로그램 제목 이후의 제목 계층을 기준으로
    읽을 수 있는 텍스트를 섹션별로 추출한다.

    법적 조건 해석이나 AND/OR 분류는 하지 않는다.
    """
    headings = [
        tag for tag in soup.find_all(
            list(HEADING_TAGS)
        )
        if not inside_excluded_tag(tag)
    ]

    program_heading = next(
        (
            h for h in headings
            if normalized(h.get_text(" ", strip=True))
            == expected_heading
        ),
        None,
    )

    assert program_heading is not None, (
        f"프로그램 제목을 찾지 못함: {expected_heading}"
    )

    sections = []
    current_heading = program_heading

    # 본문 뒤에 붙는 사이트 푸터·관련 메뉴는
    # 후속 검토가 가능하도록 완전히 단정하지 않는다.
    for index, heading in enumerate(headings):
        if heading is program_heading:
            start_index = index
            break

    relevant_headings = headings[start_index:]

    for idx, heading in enumerate(relevant_headings):
        title = normalized(
            heading.get_text(" ", strip=True)
        )

        next_heading = (
            relevant_headings[idx + 1]
            if idx + 1 < len(relevant_headings)
            else None
        )

        parts = []

        for element in heading.next_elements:
            if element is next_heading:
                break

            if isinstance(element, NavigableString):
                if inside_excluded_tag(element):
                    continue

                content = normalized(str(element))

                if content:
                    parts.append(content)

        text = normalized(" ".join(parts))

        # 반복적인 웹사이트 관련 제목 이후에는
        # 본문이 아닐 수 있으므로 별도 상태로 관리
        sections.append({
            "heading": title,
            "heading_tag": heading.name,
            "raw_text": text,
            "text_length": len(text),
        })

        if len(sections) >= 40:
            break

    assert sections, "본문 섹션 추출 실패"
    assert sections[0]["heading"] == expected_heading

    return sections


def attachment_candidates(soup, base_url):
    """
    WEST 페이지의 첨부파일 링크 및 HTML 속성 분석.
    실제 다운로드 URL을 검증하지 않았으므로
    이 단계에서는 어떤 파일도 다운로드하지 않는다.
    """
    candidates = []
    seen = set()

    keywords = (
        ".pdf", ".hwp", ".hwpx",
        "첨부", "다운로드", "미리보기",
        "download", "attach", "file_id",
    )

    for tag in soup.find_all(True):
        attrs = {
            key: str(value)
            for key, value in tag.attrs.items()
            if key in {
                "href", "onclick", "data-file-id",
                "data-id", "data-url",
                "title", "download",
            }
        }

        if not attrs:
            continue

        label = normalized(
            tag.get_text(" ", strip=True)
        )[:200]

        combined = (
            label + " " + json.dumps(
                attrs, ensure_ascii=False
            )
        ).lower()

        if not any(k in combined for k in keywords):
            continue

        href = attrs.get("href")
        resolved_url = None

        if href and not href.lower().startswith(
            ("javascript:", "#", "data:")
        ):
            resolved_url = urljoin(base_url, href)

        key = (
            label,
            json.dumps(attrs, sort_keys=True),
        )

        if key in seen:
            continue

        seen.add(key)

        candidates.append({
            "element": tag.name,
            "label": label,
            "attributes": attrs,
            "resolved_url_candidate": resolved_url,
            "download_verified": False,
        })

    return candidates[:100]


def make_content(program, snapshot):
    html_path = ROOT / snapshot["snapshot_path"]

    assert html_path.is_file()
    assert html_path.resolve().is_relative_to(
        (RAW / "source_snapshots").resolve()
    )

    raw = html_path.read_bytes()

    assert sha256(raw) == snapshot["snapshot_sha256"]

    soup = BeautifulSoup(raw, "html.parser")
    program_id = program["program_id"]

    expected_heading = EXPECTED_PROGRAMS[program_id]

    sections = heading_sections(
        soup, expected_heading
    )

    title = (
        normalized(soup.title.get_text(" ", strip=True))
        if soup.title
        else ""
    )

    # 모든 섹션을 하나로 합친 검색 후보 텍스트.
    # RAG 임베딩은 생성하지 않는다.
    extracted_text = normalized(
        " ".join(
            section["heading"] + " "
            + section["raw_text"]
            for section in sections
        )
    )

    assert expected_heading in extracted_text
    assert len(extracted_text) > 150

    is_west = program_id == "US-WEST-01"

    attachments = (
        attachment_candidates(
            soup, snapshot["source_url"]
        )
        if is_west
        else []
    )

    return {
        "dataset_type": "official_source_content",
        "country": "US",
        "program_id": program_id,
        "route_id": program["route_id"],
        "official_program_name": (
            program["official_program_name"]
        ),
        "visa_classification": (
            program["visa_classification"]
        ),
        "source": {
            "source_url": snapshot["source_url"],
            "snapshot_path": snapshot["snapshot_path"],
            "snapshot_sha256": (
                snapshot["snapshot_sha256"]
            ),
            "html_title": title,
        },
        "expected_page_heading": expected_heading,
        "sections": sections,
        "extracted_text": extracted_text,
        "attachment_candidates": attachments,
        "attachment_downloaded": False,
        "extraction_method": (
            "html_heading_and_text_nodes"
        ),
        "content_scope": (
            "extracted_sections_require_review"
        ),
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }


def render_json(data):
    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")


print("===== STEP 64-05 미국 공식 원문 통합 처리 =====")

# 1. 기존 주요 파일 검증
manifest, manifest_raw = read_json_verified(MANIFEST)
index, index_raw = read_json_verified(INDEX)
mapping, mapping_raw = read_json_verified(MAPPING)

assert manifest["program_count"] == 7
assert index["snapshot_count"] == 5
assert mapping["linked_snapshot_count"] == 5

print("[PASS] Manifest / Index / Mapping SHA-256")

# 2. 원본 HTML 전부 확인
snapshot_index_by_url = {
    item["source_url"]: item
    for item in index["snapshots"]
}

original_hashes = {
    MANIFEST: sha256(manifest_raw),
    INDEX: sha256(index_raw),
    MAPPING: sha256(mapping_raw),
}

for snap in index["snapshots"]:
    path = RAW / "source_snapshots" / snap["filename"]

    assert path.is_file()
    assert path.resolve().parent == (
        RAW / "source_snapshots"
    ).resolve()
    assert sha256(path.read_bytes()) == snap["sha256"]

    original_hashes[path] = snap["sha256"]

print("[PASS] 공식 HTML 원본 5개 SHA-256")

# 3. 프로그램별 JSON을 먼저 메모리에서 생성
prepared = []
counts = Counter()

for program in mapping["programs"]:
    program_id = program["program_id"]

    if program_id not in EXPECTED_PROGRAMS:
        continue

    collected = [
        s for s in program["sources"]
        if s["snapshot_status"]
        == "collected_needs_review"
    ]

    assert len(collected) == 1, (
        f"{program_id}: HTML 연결 개수 오류"
    )

    source = collected[0]

    assert source["source_url"] in snapshot_index_by_url

    content = make_content(program, source)
    payload = render_json(content)

    # 같은 입력으로 다시 생성해 바이트 단위 비교
    replay_content = make_content(program, source)
    replay_payload = render_json(replay_content)

    assert payload == replay_payload

    output_path = (
        ROOT / program["processed_program_dir"]
        / "source_content.json"
    )

    assert output_path.parent.is_dir()
    assert not output_path.exists(), (
        f"기존 출력 파일 존재: {output_path}"
    )

    assert json.loads(payload.decode("utf-8")) == content

    prepared.append(
        (output_path, payload, content)
    )

    counts[program_id] += 1

assert len(prepared) == 5
assert set(counts) == set(EXPECTED_PROGRAMS)

print("[PASS] 프로그램별 원문 JSON 5개 구성")
print("[PASS] 메모리 재생성 바이트 일치")

# 4. 결과가 모두 정상일 때만 출력 저장
for path, payload, content in prepared:
    with path.open("xb") as f:
        f.write(payload)

    assert path.read_bytes() == payload
    assert json.loads(
        path.read_text(encoding="utf-8")
    ) == content

print("[PASS] 프로그램별 JSON 5개 저장 및 검증")

# 5. 원본 무결성 최종 검증
for path, expected_sha in original_hashes.items():
    assert sha256(path.read_bytes()) == expected_sha, (
        f"기존 원본 변경 감지: {path}"
    )

print("[PASS] 기존 원본 파일 전체 불변")

# 6. 요약
print("\n[프로그램별 결과]")

for path, payload, content in prepared:
    print(
        content["program_id"],
        "| 섹션:", len(content["sections"]),
        "| 본문:", len(content["extracted_text"]),
        "자",
        "| SHA-256:", sha256(payload),
    )

    if content["program_id"] == "US-WEST-01":
        print(
            "WEST 첨부 링크 후보:",
            len(content["attachment_candidates"])
        )

        for item in content["attachment_candidates"][:15]:
            print(
                "  -",
                item["label"][:100],
                "|",
                item["attributes"],
            )

print("\n===== STEP 64-05 최종 결과 =====")
print("처리 프로그램:", len(prepared))
print("구조화 원문 JSON:", len(prepared))
print("기존 HTML SHA-256: PASS")
print("출력 JSON 재현성: PASS")
print("저장 후 검증: PASS")
print("기존 원본 불변: PASS")
print("첨부 PDF 다운로드: 미실행")
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("임베딩·DB 적재: 미실행")
print("Git 커밋·푸시: 미실행")