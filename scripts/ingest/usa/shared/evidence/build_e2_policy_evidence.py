
import json
import hashlib
import re
from pathlib import Path
from html.parser import HTMLParser

POLICY_PATH = Path(
    "data/processed/usa/employment/e2_treaty_investor/"
    "e2_policy_review_2026_draft.json"
)

OUTPUT_PATH = POLICY_PATH.parent / "e2_policy_evidence_2026_refined_draft.json"

ANCHORS = {
    "E2-01": ("USCIS-E2", "Be a national of a country"),
    "E2-02": ("DOS-TREATY", "Korea (South) E-2 November 7, 1957"),
    "E2-03": ("USCIS-E2", "Have invested, or be actively"),
    "E2-04": ("USCIS-E2", "at risk in the commercial sense"),
    "E2-05": ("USCIS-E2", "at least 50% ownership"),
    "E2-06": ("USCIS-E2", "A bona fide enterprise refers"),
    "E2-07": ("USCIS-E2", "A marginal enterprise is one"),
    "E2-08": ("USCIS-E2", "executive or supervisory character"),
    "E2-09": ("DOS-DS160-FAQ", "If you are a Treaty Investor (E-2) applicant"),
    "E2-10": ("USCIS-E2", "maximum initial stay of two years"),
    "E2-11": ("DOS-KR-RECIPROCITY", "E-2 2 None Multiple 60 Months"),
    "E2-12": ("DOS-E-VISA", "$315"),
    "E2-13": ("USCIS-E2", "There is no limit to the number of extensions"),
    "E2-14": ("USCIS-E2", "employment authorized incident to status"),
}


class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def extract_text(raw):
    parser = VisibleTextParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return " ".join(" ".join(parser.parts).split())


def main():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    sources = {s["source_id"]: s for s in policy["official_sources"]}
    records = {r["policy_id"]: r for r in policy["policy_records"]}

    assert len(sources) == 5
    assert len(records) == 14
    assert set(records) == set(ANCHORS)
    assert policy["validation_status"] == "needs_review"

    texts = {}

    for source_id, source in sources.items():
        raw = Path(source["local_path"]).read_bytes()
        assert sha256(raw) == source["sha256"], source_id
        texts[source_id] = extract_text(raw)

    evidence = []

    for policy_id, (source_id, anchor) in ANCHORS.items():
        assert source_id in records[policy_id]["source_ids"]

        text = texts[source_id]
        
        matches = list(re.finditer(re.escape(anchor), text, re.I))

        if not matches:
            raise ValueError(
                f"{policy_id}: evidence anchor not found"
            )

        if len(matches) > 1:
            print(
                f"[REVIEW] {policy_id}: "
                f"{len(matches)} matching passages found; "
                "first occurrence selected"
            )

        
        match = matches[0]

        # 표 데이터는 해당 행의 핵심 값만 추출합니다.
        if policy_id in {"E2-02", "E2-11"}:
            excerpt = match.group(0)

        # DS-160 FAQ는 질문에 대한 답변 구간만 추출합니다.
        elif policy_id == "E2-09":
            end_marker = "More Information"
            end = text.find(end_marker, match.start())

            if end == -1:
                raise ValueError("E2-09: FAQ answer boundary not found")

            excerpt = text[match.start():end].strip()

        # 나머지는 문장 경계를 기준으로 추출합니다.
        else:
            start = match.start()
            end = match.end()

            # 검색어가 포함된 문장의 시작 지점을 찾습니다.
            previous_period = text.rfind(". ", 0, start)
            previous_colon = text.rfind(": ", 0, start)

            boundary = max(previous_period, previous_colon)

            if boundary != -1:
                start = boundary + 2

            # 검색어 뒤에서 첫 번째 문장 종료 지점을 찾습니다.
            next_period = text.find(". ", end)

            if next_period != -1:
                end = next_period + 1

            excerpt = text[start:end].strip()

        if not excerpt:
            raise ValueError(f"{policy_id}: empty evidence text")

        if anchor.lower() not in excerpt.lower():
            raise ValueError(
                f"{policy_id}: anchor missing from extracted evidence"
            )

        evidence.append({
            "policy_id": policy_id,
            "source_id": source_id,
            "source_url": sources[source_id]["url"],
            "source_sha256": sources[source_id]["sha256"],
            "anchor_text": anchor,
            "match_start": match.start(),
            "match_end": match.end(),
            "excerpt_text": excerpt,
            "excerpt_sha256": sha256(excerpt.encode("utf-8")),
            "evidence_status": "candidate_text_matched",
            "semantic_review_status": "needs_review",
        })

        print(f"[PASS] {policy_id} -> {source_id}")

    result = {
        "dataset_type": "e2_policy_evidence_draft",
        "team_reference_program_id": "US-WK-02",
        "internal_program_id": policy["internal_program_id"],
        "internal_id_status": policy["internal_id_status"],
        "evidence_count": len(evidence),
        "extraction_method": "html_parser_visible_text_anchor",
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "embedding_generated": False,
        "evidence_records": evidence,
    }

    # 기존 검수 데이터를 덮어쓰지 않도록 보호합니다.
    if OUTPUT_PATH.exists():
        raise FileExistsError(f"Already exists: {OUTPUT_PATH}")

    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n[PASS] {len(evidence)} evidence records created")
    print(f"[PASS] Saved: {OUTPUT_PATH}")
    print("[INFO] Semantic review remains pending")


if __name__ == "__main__":
    main()