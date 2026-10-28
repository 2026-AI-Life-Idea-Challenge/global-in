
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

from scripts.ingest.usa.shared.evidence.build_e2_policy_evidence import (
    extract_text,
)


POLICY_PATH = Path(
    "data/processed/usa/employment/o1_extraordinary_ability/"
    "o1_policy_review_2026_draft.json"
)

OUTPUT_PATH = Path(
    "data/processed/usa/employment/o1_extraordinary_ability/"
    "o1_policy_evidence_2026_refined_draft.json"
)


# 정책별 원문 검색 패턴
# 검색 패턴 일치는 의미적 근거 검증과 다릅니다.
# 찾지 못한 정책은 자동으로 누락 목록에 기록합니다.

ANCHORS_TEXT = r"""
O1-01|extraordinary ability|sciences, education, business, or athletics
O1-02|distinction in the field of arts|distinction
O1-03|extraordinary achievement|motion picture or television
O1-04|at least three alternate forms of evidence
O1-05|in some categories nomination for
O1-06|at least three of the following|Academy Award
O1-07|nationally or internationally recognized prizes|awards for excellence
O1-08|membership in associations|outstanding achievements
O1-09|published material|about the beneficiary
O1-10|judge of the work of others|judging the work of others
O1-11|original scientific|major significance
O1-12|authorship of scholarly articles|scholarly articles
O1-13|critical or essential capacity|critical or essential
O1-14|high salary|high remuneration
O1-15|comparable evidence|not readily applicable
O1-16|lead or starring participant|lead or starring
O1-17|national or international recognition|recognition for achievements
O1-18|lead, starring, or critical role|critical role
O1-19|major commercial or critically acclaimed successes|box office receipts
O1-20|significant recognition|organizations, critics
O1-21|high salary|substantial remuneration
O1-22|comparable evidence|arts
O1-23|comparable evidence|motion picture or television
O1-24|totality of the evidence|small percentage
O1-25|totality of the evidence|distinction
O1-26|totality of the evidence|extraordinary achievement
O1-27|United States employer|U.S. employer
O1-28|United States agent|U.S. agent
O1-29|foreign employer|United States agent
O1-30|multiple employers|more than one employer
O1-31|authorized to act|authorization
O1-32|O beneficiaries may not petition for themselves
O1-33|separate legal entity|owned by the beneficiary
O1-34|changes in the terms and conditions|notify USCIS
O1-35|reasonable cost of return transportation|return transportation
O1-36|Form I-129|Petition for a Nonimmigrant Worker
O1-37|one year before|1 year before
O1-38|written contract|contract between the petitioner
O1-39|oral agreement|summary of the terms
O1-40|nature of the events or activities|beginning and ending dates
O1-41|more than one location|itinerary
O1-42|25 O-2 beneficiaries|25 beneficiaries
O1-43|consultation|peer group
O1-44|labor union|management organization
O1-45|labor organization|appropriate labor organization
O1-46|labor union|management organization
O1-47|appropriate peer group|does not exist
O1-48|two years|2 years
O1-49|negative advisory opinion|not binding
O1-50|arts or athletics|support of an O-1
O1-51|critical skills and experience|not of a general nature
O1-52|substantial experience|essential
O1-53|significant production|continuing participation
O1-54|may not work separate|may not work apart
O1-55|change employers|change of employer
O1-56|spouse and children|unmarried children under 21
O1-57|accompany or follow to join|following to join
O1-58|same period of time|same conditions
O1-59|may not accept employment|not authorized to work
O1-60|not to exceed 3 years
O1-61|up to 1 year|one year
O1-62|new event or activity|new event
O1-63|no limit to the number|no limit on the number
O1-64|60 days|up to 60 days
O1-65|10 days before|10 days after
O1-66|change employers|new employer
O1-67|1,055|1,005
O1-68|Asylum Program Fee|600
O1-69|205|petition-based
O1-70|2,965|premium processing
O1-71|DS-160|confirmation page
O1-72|I-797|petition receipt number
O1-73|O-1|O-2
O1-74|The validity of H-1 through H-3, O-1 and O-2
O1-75|may participate in full-time or part-time study
O1-76|I-539|Application to Extend/Change Nonimmigrant Status
O1-77|professional athlete|traded from one team
"""


def parse_anchors():
    anchors = {}

    for raw_line in ANCHORS_TEXT.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        parts = [part.strip() for part in line.split("|")]

        if len(parts) < 2:
            raise ValueError(f"Invalid anchor: {line}")

        policy_id = parts[0]
        phrases = parts[1:]

        if policy_id in anchors:
            raise ValueError(f"Duplicate anchor: {policy_id}")

        anchors[policy_id] = phrases

    return anchors


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def load_source_pages(source):
    path = Path(source["local_path"])

    if not path.exists():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    actual_hash = sha256_bytes(raw)

    if actual_hash != source["sha256"]:
        raise ValueError(
            f"Source hash mismatch: {source['source_id']}"
        )

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))

        pages = []

        for page_number, page in enumerate(reader.pages, 1):
            content = normalize_text(page.extract_text() or "")

            if content:
                pages.append((page_number, content))

        return pages

    if path.suffix.lower() in {".html", ".htm"}:
        content = extract_text(raw)
        content = normalize_text(content)
        return [(None, content)]

    content = normalize_text(
        path.read_text(encoding="utf-8")
    )

    return [(None, content)]


def find_candidate(source_pages, phrases):
    """
    검색어가 실제 원문에 존재하는 경우에만 후보 생성.
    의미적 일치 여부는 판단하지 않음.
    """

    for phrase in phrases:
        normalized_phrase = normalize_text(phrase)

        if not normalized_phrase:
            continue

        for page_number, text in source_pages:
            match = re.search(
                re.escape(normalized_phrase),
                text,
                flags=re.IGNORECASE,
            )

            if match is None:
                continue

            start = max(0, match.start() - 180)
            end = min(len(text), match.end() + 850)

            excerpt = text[start:end]

            return {
                "search_phrase": normalized_phrase,
                "source_page": page_number,
                "evidence_excerpt": excerpt,
            }

    return None


def main():
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing file: {OUTPUT_PATH}"
        )

    data = json.loads(
        POLICY_PATH.read_text(encoding="utf-8")
    )

    policies = data["policy_records"]
    sources = data["official_sources"]
    anchors = parse_anchors()

    expected_ids = {
        f"O1-{i:02d}" for i in range(1, 78)
    }

    policy_ids = {
        policy["policy_id"] for policy in policies
    }

    if policy_ids != expected_ids:
        raise ValueError("Policy ID set mismatch")

    if set(anchors) != expected_ids:
        raise ValueError("Anchor ID set mismatch")

    if len(policies) != 77:
        raise ValueError("Expected exactly 77 policies")

    if len(sources) != 11:
        raise ValueError("Expected exactly 11 sources")

    source_map = {
        source["source_id"]: source
        for source in sources
    }

    if len(source_map) != len(sources):
        raise ValueError("Duplicate source IDs")

    # 원본 11개를 미리 검증하고 텍스트 추출
    source_cache = {}

    for source in sources:
        source_cache[source["source_id"]] = (
            load_source_pages(source)
        )

    evidence_records = []
    missing_searches = []

    for policy in policies:
        policy_id = policy["policy_id"]
        phrases = anchors[policy_id]

        matched = False

        # 정책에서 지정한 공식 출처만 검색
        for source_id in policy["source_ids"]:
            source = source_map[source_id]

            candidate = find_candidate(
                source_cache[source_id],
                phrases,
            )

            if candidate is None:
                continue

            excerpt = candidate["evidence_excerpt"]

            evidence_records.append({
                "evidence_id": (
                    f"O1-EV-{len(evidence_records) + 1:03d}"
                ),
                "policy_id": policy_id,
                "source_id": source_id,
                "source_path": source["local_path"],
                "source_sha256": source["sha256"],
                "source_page": candidate["source_page"],
                "search_phrase": candidate["search_phrase"],
                "evidence_excerpt": excerpt,
                "excerpt_sha256": sha256_bytes(
                    excerpt.encode("utf-8")
                ),
                "evidence_type": "candidate_excerpt",
                "semantic_support_verified": False,
                "review_status": "needs_review",
            })

            matched = True

            # 우선 정책당 후보 1개씩 생성
            break

        if not matched:
            missing_searches.append({
                "policy_id": policy_id,
                "source_ids": policy["source_ids"],
                "search_phrases": phrases,
                "reason": "no_literal_phrase_match",
                "review_status": "needs_review",
            })

    covered_ids = {
        record["policy_id"]
        for record in evidence_records
    }

    output = {
        "country": "USA",
        "team_reference_program_id": data[
            "team_reference_program_id"
        ],
        "program_name": data["program_name"],
        "validation_status": "needs_review",
        "source_count": len(sources),
        "policy_count": len(policies),
        "covered_policy_count": len(covered_ids),
        "evidence_count": len(evidence_records),
        "missing_search_count": len(missing_searches),
        "evidence_records": evidence_records,
        "missing_searches": missing_searches,
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "embedding_generated": False,
        "refined_policy_ids": [],
        "refinement_status": "not_started",
    }

    assert (
        output["covered_policy_count"]
        + output["missing_search_count"]
        == 77
    ), "Coverage accounting mismatch"

    assert all(
        record["review_status"] == "needs_review"
        and record["semantic_support_verified"] is False
        for record in evidence_records
    ), "Evidence review state mismatch"

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== O VISA EVIDENCE EXTRACTION ===")
    print("Sources verified:", len(source_cache))
    print("Policies:", len(policies))
    print("Evidence candidates:", len(evidence_records))
    print("Covered policies:", len(covered_ids))
    print("Missing searches:", len(missing_searches))
    print(
        "Semantic support verified:",
        all(
            record["semantic_support_verified"]
            for record in evidence_records
        ) if evidence_records else False
    )
    print("Validation status:", output["validation_status"])
    print("Saved:", OUTPUT_PATH)

    if missing_searches:
        print("Missing policy IDs:", [
            item["policy_id"]
            for item in missing_searches
        ])

    print("[PASS] Evidence candidate extraction completed")
    print("[INFO] Candidate excerpts require semantic review")


if __name__ == "__main__":
    main()