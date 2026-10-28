
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

from scripts.ingest.usa.shared.evidence.build_e2_policy_evidence import (
    extract_text,
)


POLICY_PATH = Path(
    "data/processed/usa/employment/l1_intracompany_transferee/"
    "l1_policy_review_2026_draft.json"
)

OUTPUT_PATH = Path(
    "data/processed/usa/employment/l1_intracompany_transferee/"
    "l1_policy_evidence_2026_draft.json"
)


# policy_id: [(source_id, search_phrase), ...]
# 검색 문구는 원문 후보를 찾기 위한 것으로,
# 정책 전체에 대한 법적 검증을 의미하지 않습니다.
ANCHORS = {
    "L1-01": [
        ("USCIS-L1A", "parent company, branch, subsidiary, or affiliate"),
    ],
    "L1-02": [
        ("USCIS-L1A", "doing business"),
    ],
    "L1-03": [
        ("USCIS-L1A", "one continuous year"),
    ],
    "L1-04": [
        ("USCIS-L1A", "Executive capacity"),
    ],
    "L1-05": [
        ("USCIS-L1A", "Managerial capacity"),
    ],
    "L1-06": [
        ("USCIS-L1B", "Specialized knowledge means either"),
        ("USCIS-L1B", "an advanced level of knowledge or expertise"),
    ],
    "L1-07": [
        ("USCIS-L1A", "maximum initial stay of one year"),
    ],
    "L1-08": [
        ("USCIS-L1A", "maximum initial stay of three years"),
    ],
    "L1-09": [
        ("USCIS-L1A", "maximum limit of seven years"),
    ],
    "L1-10": [
        ("USCIS-L1B", "maximum limit of five years"),
    ],
    "L1-11": [
        ("USCIS-L1A", "New Offices"),
    ],
    "L1-12": [
        ("USCIS-L1B", "New Offices"),
    ],
    "L1-13": [
        ("USCIS-L1B", "L-1 Visa Reform Act of 2004"),
    ],
    "L1-14": [
        ("USCIS-L1A", "Family of L-1 Workers"),
    ],
    "L1-15": [
        ("USCIS-L1B", "employment authorized incident to status"),
    ],
    "L1-16": [
        ("DOS-TEMP-WORKER", "Form I-129"),
    ],
    "L1-17": [
        ("DOS-TEMP-WORKER", "Form DS-160"),
        ("DOS-TEMP-WORKER", "$205"),
        ("DOS-DS160-INSTRUCTIONS", "Print and keep the DS-160 barcode page."),
    ],
    "L1-18": [
        ("DOS-TEMP-WORKER", "Form I-129S"),
        ("DOS-TEMP-WORKER", "Fraud Prevention and Detection fee"),
    ],
    "L1-19": [
        ("DOS-KR-RECIPROCITY", "L-1 None Multiple 60 Months"),
    ],
    "L1-20": [
        ("USCIS-G1055-20261016", "I-129-L petitions"),
    ],
    "L1-21": [
        ("USCIS-G1055-20261016", "L petitioners must submit a Fraud Prevention"),
    ],
    "L1-22": [
        ("USCIS-G1055-20261016", "L-1 petitioners are required"),
    ],
    "L1-23": [
        (
            "USCIS-L1-POLICY-MANUAL",
            "L-1 Blanket Petitions",
        ),
    ],
    "L1-24": [
        (
            "USCIS-L1-POLICY-MANUAL",
            "Special Consideration: L-1A New Office Petitions",
        ),
    ],
    "L1-25": [
        (
            "USCIS-L1-POLICY-MANUAL",
            "Extension of L-1 New Office Petitions",
        ),
    ],
    "L1-26": [
        (
            "DOS-NIV-INTERVIEW-LOCATION-20260715",
            "Applicants for U.S. nonimmigrant visas (NIV) should schedule",
        ),
    ],
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def normalized_text(text):
    return " ".join(text.split())


def load_source(source):
    path = Path(source["local_path"])
    raw = path.read_bytes()

    actual_hash = sha256_bytes(raw)
    assert actual_hash == source["sha256"], (
        f"Source SHA-256 mismatch: {source['source_id']}"
    )

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        sections = [
            {
                "page": index + 1,
                "text": normalized_text(page.extract_text() or ""),
            }
            for index, page in enumerate(reader.pages)
        ]
    else:
        sections = [
            {
                "page": None,
                "text": normalized_text(extract_text(raw)),
            }
        ]

    return sections


def find_excerpt(sections, phrase):
    for section in sections:
        text = section["text"]
        position = text.casefold().find(phrase.casefold())

        if position == -1:
            continue

        
        if phrase == "Print and keep the DS-160 barcode page.":
            start = position
            end = min(len(text), position + 850)

        elif phrase == (
            "Applicants for U.S. nonimmigrant visas (NIV) should schedule"
        ):
            start = position
            end = min(len(text), position + 2200)

        # 국무부 비이민 비자 인터뷰 장소 지침
        elif phrase == (
            "Applicants for U.S. nonimmigrant visas (NIV) should schedule"
        ):
            start = position
            end = min(len(text), position + 2200)

        elif phrase in (
            "L-1 Blanket Petitions",
            "Special Consideration: L-1A New Office Petitions",
            "Extension of L-1 New Office Petitions",
        ):
            start = position
            end = min(len(text), position + 2400)
        
        # USCIS Policy Manual:
        # Blanket L 및 신규 사무소의 복수 요건을 함께 확보
        elif phrase in (
            "L-1 Blanket Petitions",
            "Special Consideration: L-1A New Office Petitions",
            "Extension of L-1 New Office Petitions",
        ):
            start = position
            end = min(len(text), position + 2400)

        elif phrase == "I-129-L petitions":
            start = position
            end = len(text)

        # L-1 수수료표: 해당 페이지의 L-1 항목부터 추출.
        # 앞선 H-1B 전용 $100,000 수수료가 섞이지 않도록 제한.
        elif phrase == "I-129-L petitions":
            start = position
            end = len(text)

        # PDF 39페이지는 두 수수료의 조건과
        # 하단 금액표($500, $4,500)를 함께 포함.
        elif phrase in (
            "L petitioners must submit a Fraud Prevention",
            "L-1 petitioners are required",
        ):
            start = max(0, position - 60)
            end = len(text)

        # L-2S 배우자 취업 관련 과거 I-94 예외 문장까지 포함.
        elif phrase == "employment authorized incident to status":
            start = max(0, position - 120)
            end = min(len(text), position + 1700)

        else:
            start = max(0, position - 120)
            end = min(len(text), position + len(phrase) + 650)

        return {
            "excerpt": text[start:end].strip(),
            "page": section["page"],
        }

    return None


def main():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    sources = {
        source["source_id"]: source
        for source in policy["official_sources"]
    }

    records = {
        record["policy_id"]: record
        for record in policy["policy_records"]
    }

    assert len(sources) == 8
    assert len(records) == 26
    assert set(ANCHORS) == set(records)

    texts = {
        source_id: load_source(source)
        for source_id, source in sources.items()
    }

    evidence = []
    missing = []

    for policy_id, searches in ANCHORS.items():
        record = records[policy_id]

        for source_id, phrase in searches:
            assert source_id in sources
            assert source_id in record["source_ids"]

            result = find_excerpt(texts[source_id], phrase)

            if result is None:
                missing.append({
                    "policy_id": policy_id,
                    "source_id": source_id,
                    "search_phrase": phrase,
                })
                continue

            excerpt = result["excerpt"]

            evidence.append({
                "evidence_id": f"L1-EV-{len(evidence) + 1:03d}",
                "policy_id": policy_id,
                "source_id": source_id,
                "source_path": sources[source_id]["local_path"],
                "source_sha256": sources[source_id]["sha256"],
                "source_page": result["page"],
                "search_phrase": phrase,
                "evidence_excerpt": excerpt,
                "excerpt_sha256": sha256_bytes(
                    excerpt.encode("utf-8")
                ),
                "evidence_type": "candidate_excerpt",
                "semantic_support_verified": False,
                "review_status": "needs_review",
            })

    covered = {item["policy_id"] for item in evidence}

    output = {
        "country": "USA",
        "team_reference_program_id": "US-WK-03",
        "program_name": "L-1A/L-1B Intracompany Transferee",
        "validation_status": "needs_review",
        "source_count": len(sources),
        "policy_count": len(records),
        "covered_policy_count": len(covered),
        "evidence_count": len(evidence),
        "missing_search_count": len(missing),
        "evidence_records": evidence,
        "missing_searches": missing,
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "embedding_generated": False,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== L-1 EVIDENCE GENERATION ===")
    print("Official sources:", len(sources))
    print("Policies:", len(records))
    print("Policies with candidate evidence:", len(covered))
    print("Evidence candidates:", len(evidence))
    print("Missing searches:", len(missing))

    for item in missing:
        print(
            "[REVIEW]",
            item["policy_id"],
            "|",
            item["source_id"],
            "|",
            item["search_phrase"],
        )

    print("Saved:", OUTPUT_PATH)
    print("[PASS] Evidence draft generated")
    print("[INFO] Semantic and legal review still required")


if __name__ == "__main__":
    main()