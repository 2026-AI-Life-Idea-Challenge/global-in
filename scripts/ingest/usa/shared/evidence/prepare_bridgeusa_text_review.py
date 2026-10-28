
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
DATA_ROOT = ROOT / "data/processed/usa/employment"

PROGRAMS = {
    "j1_intern": "US-EM-02",
    "j1_trainee": "US-EM-03",
}

OUTPUT = DATA_ROOT / "bridgeusa_j1_text_review_draft.json"

# 정확히 식별되는 웹사이트 UI 문자열만 제거합니다.
UI_PATTERNS = [
    r"Tweet get_facebook_share\(\)\? ",
    r"\bend featured experience component\b",
    r"\bfeatured experience component\b",
    r"\bend tab [123]\b",
    r"\btab [123]\b",
    r"\bProgram Resources\b",
    r"\bCommon Questions\b",
    r"\bSEVIS Information\b",
    r"\bREAD MORE\b",
    r"\bVisa Basics\b",
    r"\bFacts & Figures\b",
    r"\bAbout J-2 Visa\b",
    r"\bOther U\.S\. Student Visas\b",
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    return " ".join(text.split())


class TextAndLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def clean_text(raw):
    parser = TextAndLinks()
    parser.feed(raw)
    parser.close()

    text = normalize(" ".join(parser.parts))
    removed = []

    for pattern in UI_PATTERNS:
        updated, count = re.subn(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE,
        )
        if count:
            removed.append({
                "pattern": pattern,
                "count": count,
            })
        text = normalize(updated)

    return {
        "cleaned_text": text,
        "removed_ui_patterns": removed,
        "extracted_links": list(dict.fromkeys(parser.links)),
        "html_tag_detected": bool(re.search(r"<[^>]+>", raw)),
    }


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def process_program(folder_name, expected_id):
    folder = DATA_ROOT / folder_name
    source_path = folder / "source_content.json"
    evidence_path = folder / "official_evidence.json"

    source_raw = source_path.read_bytes()
    source = json.loads(source_raw.decode("utf-8"))
    evidence = load_json(evidence_path)

    assert source["program_id"] == expected_id
    assert evidence["program_id"] == expected_id

    # 기존 구조화 JSON 해시 검증
    assert sha256(source_raw) == evidence["source_content_sha256"]

    # 공식 원본 HTML 해시 검증
    snapshot = source["source"]
    html_path = ROOT / snapshot["snapshot_path"]
    html_hash = sha256(html_path.read_bytes())

    assert html_hash == snapshot["snapshot_sha256"]
    assert html_hash == evidence["source_html_sha256"]

    # 원본 근거와 구조화 섹션의 일치 여부
    original_sections = source["sections"]
    evidence_sections = evidence["sections"]

    assert len(original_sections) == len(evidence_sections)
    assert len(original_sections) == evidence["source_section_count"]

    records = []

    for index, (section, record) in enumerate(
        zip(original_sections, evidence_sections), start=1
    ):
        raw = section["raw_text"]

        assert record["source_text"] == raw
        assert record["source_text_sha256"] == sha256(
            raw.encode("utf-8")
        )

        result = clean_text(raw)

        assert result["cleaned_text"], (
            f"{folder_name}: empty section {index}"
        )

        records.append({
            "section_index": index,
            "evidence_id": record["evidence_id"],
            "heading": section["heading"],
            "heading_tag": section["heading_tag"],
            "category_candidate": record["category_candidate"],
            "source_text_sha256": record["source_text_sha256"],
            **result,
            "section_boundary_verified": False,
            "semantic_review_status": "needs_review",
        })

    return {
        "program_id": expected_id,
        "source_url": snapshot["source_url"],
        "source_html_sha256": html_hash,
        "source_content_sha256": sha256(source_raw),
        "section_count": len(records),
        "sections": records,
        "section_boundaries_verified": False,
        "eligibility_rules_verified": False,
        "validation_status": "needs_review",
    }


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"기존 결과가 존재합니다. 덮어쓰지 않습니다: {OUTPUT}"
        )

    results = {}
    for folder_name, program_id in PROGRAMS.items():
        results[folder_name] = process_program(
            folder_name, program_id
        )

    payload = {
        "dataset_type": "bridgeusa_text_cleanup_review_draft",
        "country": "US",
        "programs": results,
        "cleanup_method": (
            "html_tag_removal_and_explicit_ui_pattern_filtering"
        ),
        "source_texts_modified": False,
        "existing_files_modified": False,
        "section_boundaries_verified": False,
        "semantic_review_completed": False,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    # 결과를 새 파일로만 저장
    with OUTPUT.open("x", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

    # 저장한 파일의 문법 및 기본 구조 확인
    saved = load_json(OUTPUT)
    assert saved == payload

    for name, result in results.items():
        ui_count = sum(
            sum(p["count"] for p in s["removed_ui_patterns"])
            for s in result["sections"]
        )
        print(
            f"[PASS] {name}: "
            f"{result['section_count']} sections, "
            f"{ui_count} UI matches"
        )

    print("[PASS] Original HTML SHA-256")
    print("[PASS] Source and evidence consistency")
    print("[PASS] Review draft JSON")
    print("[PASS] Existing data preserved")
    print("Output:", OUTPUT.relative_to(ROOT))
    print("Status: needs_review")


if __name__ == "__main__":
    main()