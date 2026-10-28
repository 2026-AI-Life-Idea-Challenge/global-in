
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup

from .collect_h1b_sources import ROOT


MANIFEST = (
    ROOT / "h1b_official_sources_2026_extended_draft.json"
)

OUTPUT = Path(
    "data/processed/usa/employment/"
    "h1b_specialty_occupation/"
    "h1b_policy_candidates_2026_draft.json"
)

MAX_PER_SOURCE = 15

TOPICS = {
    "eligibility": [
        "specialty occupation", "bachelor",
        "degree", "equivalent", "qualification",
    ],
    "employer_requirements": [
        "employer", "petitioner", "labor condition",
        "prevailing wage", "working conditions",
    ],
    "registration_selection": [
        "registration", "selection", "lottery",
        "cap-subject", "weighted selection",
    ],
    "petition_process": [
        "form i-129", "petition", "filing",
        "approval", "consular",
    ],
    "fees": [
        "fee", "payment", "$100,000",
        "biometric",
    ],
    "stay_extension": [
        "period of stay", "extension",
        "three years", "six years",
    ],
    "family": [
        "h-4", "dependent", "spouse",
        "children",
    ],
    "restrictions_screening": [
        "proclamation", "restriction",
        "screening", "vetting", "entry",
        "court", "vacated",
    ],
}


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def html_paragraphs(path):
    soup = BeautifulSoup(
        path.read_bytes(), "html.parser"
    )

    for tag in soup([
        "script", "style", "noscript",
        "nav", "footer", "header",
    ]):
        tag.decompose()

    root = (
        soup.find("main")
        or soup.find("article")
        or soup
    )

    paragraphs = []

    for tag in root.find_all(["p", "li", "pre"]):
        if tag.name == "pre":
            chunks = re.split(
                r"\n\s*\n",
                tag.get_text("\n", strip=True),
            )
        elif tag.find(["p", "li", "pre"]):
            continue
        else:
            chunks = [
                tag.get_text(" ", strip=True)
            ]

        for chunk in chunks:
            value = normalize(chunk)
            if value:
                paragraphs.append((None, value))

    return paragraphs


def pdf_paragraphs(path):
    paragraphs = []

    with pymupdf.open(path) as doc:
        for page_num, page in enumerate(doc, 1):
            text = page.get_text(sort=True)

            chunks = re.split(
                r"\n\s*\n", text
            )

            for chunk in chunks:
                value = normalize(chunk)
                if value:
                    paragraphs.append(
                        (page_num, value)
                    )

    return paragraphs


def classify(text):
    lower = text.lower()

    matches = {
        topic: sum(
            1 for term in terms
            if term in lower
        )
        for topic, terms in TOPICS.items()
    }

    topic = max(matches, key=matches.get)
    score = matches[topic]

    if score == 0:
        return None, 0

    return topic, score


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    manifest = json.loads(
        MANIFEST.read_text(encoding="utf-8-sig")
    )

    sources = manifest["official_sources"]

    if len(sources) != 15:
        raise ValueError(
            f"Expected 15 sources, got {len(sources)}"
        )

    records = []

    for source in sources:
        sid = source["source_id"]
        path = Path(source["local_path"])

        if not path.is_file():
            raise FileNotFoundError(path)

        actual_hash = sha256(path.read_bytes())

        if actual_hash != source["sha256"]:
            raise ValueError(
                f"Source hash mismatch: {sid}"
            )

        if path.suffix.lower() == ".pdf":
            paragraphs = pdf_paragraphs(path)
        else:
            paragraphs = html_paragraphs(path)

        candidates = []
        seen = set()

        for index, (page, text) in enumerate(paragraphs):
            if len(text) < 100:
                continue

            # Avoid cutting a policy statement in half.
            if len(text) > 2400:
                continue

            topic, score = classify(text)

            if not topic:
                continue

            fingerprint = sha256(
                text.encode("utf-8")
            )

            if fingerprint in seen:
                continue

            seen.add(fingerprint)

            candidates.append({
                "index": index,
                "page": page,
                "topic": topic,
                "score": score,
                "text": text,
                "hash": fingerprint,
            })

        # Select relevant excerpts, then restore source order.
        selected = sorted(
            sorted(
                candidates,
                key=lambda x: (
                    -x["score"], x["index"]
                ),
            )[:MAX_PER_SOURCE],
            key=lambda x: x["index"],
        )

        for item in selected:
            number = len(records) + 1

            records.append({
                "candidate_id": (
                    f"H1B-CAND-{number:04d}"
                ),
                "source_id": sid,
                "source_path": path.as_posix(),
                "source_sha256": actual_hash,
                "source_page": item["page"],
                "topic_candidate": item["topic"],
                "evidence_excerpt": item["text"],
                "excerpt_sha256": item["hash"],
                "extraction_method": (
                    "keyword_paragraph_candidate"
                ),
                "semantic_support_verified": False,
                "legal_effect_verified": False,
                "review_status": "needs_review",
            })

        print(
            f"[PASS] {sid} | "
            f"PARAGRAPHS: {len(paragraphs)} | "
            f"MATCHES: {len(candidates)} | "
            f"SELECTED: {len(selected)}"
        )

    result = {
        "country": "USA",
        "team_reference_program_id": "US-WK-01",
        "program_name": "H-1B Specialty Occupation",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_count": len(sources),
        "candidate_count": len(records),
        "candidate_type": "source_excerpt",
        "extraction_limit_per_source": MAX_PER_SOURCE,
        "candidate_records": records,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    OUTPUT.parent.mkdir(
        parents=True, exist_ok=True
    )

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            result, f,
            ensure_ascii=False, indent=2
        )

    print("\n=== H-1B POLICY CANDIDATES ===")
    print("SOURCES:", len(sources))
    print("CANDIDATES:", len(records))
    print("VALIDATION:", result["validation_status"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()