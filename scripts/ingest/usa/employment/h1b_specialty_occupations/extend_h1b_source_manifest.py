
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from .collect_h1b_sources import ROOT


INPUT = ROOT / "h1b_official_sources_2026_draft.json"
OUTPUT = ROOT / "h1b_official_sources_2026_extended_draft.json"

ADDITIONAL_SOURCES = [
    {
        "source_id": "H1B-PROCLAMATION-2026",
        "agency": "PRESIDENT",
        "source_role": "presidential_proclamation",
        "filename": "h1b_entry_restriction_proclamation_2026.html",
        "url": (
            "https://www.govinfo.gov/content/pkg/"
            "FR-2026-09-23/html/2026-19554.htm"
        ),
        "document_number": "2026-19554",
    },
    {
        "source_id": "DHS-H1B-BIOMETRIC-FEE-2026",
        "agency": "DHS-CBP",
        "source_role": "final_rule",
        "filename": "dhs_h1b_biometric_fee_final_rule_2026.html",
        "url": (
            "https://www.govinfo.gov/content/pkg/"
            "FR-2026-08-10/html/2026-16231.htm"
        ),
        "document_number": "2026-16231",
    },
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    original = json.loads(
        INPUT.read_text(encoding="utf-8-sig")
    )

    records = list(original["official_sources"])

    if len(records) != 13:
        raise ValueError(
            f"Expected 13 existing sources, got {len(records)}"
        )

    ids = set()
    hashes = set()

    for record in records:
        sid = record["source_id"]
        path = Path(record["local_path"])

        if not path.is_file():
            raise FileNotFoundError(path)

        actual_hash = sha256(path.read_bytes())

        if actual_hash != record["sha256"]:
            raise ValueError(f"Hash mismatch: {sid}")

        if sid in ids or actual_hash in hashes:
            raise ValueError(f"Duplicate source: {sid}")

        ids.add(sid)
        hashes.add(actual_hash)

    for source in ADDITIONAL_SOURCES:
        sid = source["source_id"]
        path = ROOT / source["filename"]

        if not path.is_file():
            raise FileNotFoundError(path)

        content = path.read_bytes()
        content_hash = sha256(content)

        soup = BeautifulSoup(content, "html.parser")
        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title else ""
        )
        text = soup.get_text(" ", strip=True)

        if not (
            "<html" in content[:10000]
            .decode("utf-8", errors="ignore")
            .lower()
            or "<!doctype html" in content[:10000]
            .decode("utf-8", errors="ignore")
            .lower()
        ):
            raise ValueError(f"Invalid HTML: {sid}")

        if source["document_number"] not in text:
            raise ValueError(
                f"Document number mismatch: {sid}"
            )

        if "h-1b" not in text.lower():
            raise ValueError(f"H-1B content missing: {sid}")

        if sid in ids or content_hash in hashes:
            raise ValueError(f"Duplicate source: {sid}")

        records.append({
            "source_id": sid,
            "agency": source["agency"],
            "source_role": source["source_role"],
            "url": source["url"],
            "url_verification_status": "listed_url_unverified",
            "local_path": path.as_posix(),
            "title": title,
            "document_type": "html",
            "document_number": source["document_number"],
            "size_bytes": len(content),
            "sha256": content_hash,
            "text_length": len(text),
            "page_count": None,
            "review_status": "needs_review",
        })

        ids.add(sid)
        hashes.add(content_hash)

        print(
            f"[PASS] {sid} | "
            f"{len(content)} bytes"
        )

    result = {
        **original,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_count": len(records),
        "official_sources": records,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n=== H-1B EXTENDED SOURCE MANIFEST ===")
    print("TOTAL SOURCES:", len(records))
    print("UNIQUE IDS:", len(ids))
    print("UNIQUE HASHES:", len(hashes))
    print("VALIDATION:", result["validation_status"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()