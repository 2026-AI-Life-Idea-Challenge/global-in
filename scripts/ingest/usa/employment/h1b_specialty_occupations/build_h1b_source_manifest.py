
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pymupdf
from bs4 import BeautifulSoup

from .collect_h1b_sources import SOURCES, ROOT


OUTPUT = ROOT / "h1b_official_sources_2026_draft.json"

SHARED_DOS = Path(
    "data/raw/usa/employment/"
    "l1_intracompany_transferee/"
    "state_department_temporary_worker_visas.html"
)

EXTRA = [
    (
        "USCIS-AFM-CH31",
        "USCIS",
        "uscis_afm_chapter31_h_classifications.pdf",
        "historical_support",
        "https://www.uscis.gov/sites/default/files/"
        "document/policy-manual-afm/afm31-external.pdf",
    ),
    (
        "DHS-H1B-WEIGHTED-2025",
        "DHS",
        "dhs_h1b_weighted_selection_final_rule_2025.html",
        "final_rule",
        None,
    ),
    (
        "DHS-H1B-MODERNIZATION-2024",
        "DHS",
        "dhs_h1b_modernization_final_rule_2024.html",
        "final_rule",
        "https://www.govinfo.gov/content/pkg/"
        "FR-2024-12-18/html/2024-29354.htm",
    ),
    (
        "DOS-H1B-H4-SCREENING-2025",
        "DOS",
        "dos_h1b_h4_screening_2025.html",
        "consular_guidance",
        None,
    ),
    (
        "DOS-EXPANDED-SCREENING-2026",
        "DOS",
        "dos_expanded_screening_2026.html",
        "supplementary_guidance",
        None,
    ),
]

ALLOWED_DOMAINS = {
    "uscis.gov",
    "travel.state.gov",
    "dol.gov",
    "federalregister.gov",
    "govinfo.gov",
}


def digest(content):
    return hashlib.sha256(content).hexdigest()


def official_url(url):
    if not url:
        return False

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    return (
        parsed.scheme == "https"
        and any(
            host == domain or host.endswith("." + domain)
            for domain in ALLOWED_DOMAINS
        )
    )


def inspect_file(path):
    content = path.read_bytes()
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError(f"Invalid PDF: {path}")

        with pymupdf.open(path) as doc:
            if doc.page_count == 0:
                raise ValueError(f"Empty PDF: {path}")

            text = " ".join(page.get_text() for page in doc)
            title = doc.metadata.get("title") or path.stem
            pages = doc.page_count

        url = None
        kind = "pdf"

    else:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(" ", strip=True)
        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title else ""
        )

        candidates = []

        for tag in soup.find_all("link", href=True):
            if "canonical" in tag.get("rel", []):
                candidates.append(tag["href"])

        for tag in soup.find_all("meta"):
            if tag.get("property") == "og:url":
                candidates.append(tag.get("content"))

        url = next(
            (u for u in candidates if official_url(u)),
            None,
        )

        kind = "html"
        pages = None

        if (
            "page not found" in title.lower()
            or "access denied" in title.lower()
        ):
            raise ValueError(f"Error page: {path}")

    if len(text.strip()) < 200:
        raise ValueError(f"Insufficient text: {path}")

    return {
        "title": title,
        "document_type": kind,
        "size_bytes": len(content),
        "sha256": digest(content),
        "text_length": len(text),
        "page_count": pages,
        "detected_url": url,
    }


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    records = []
    seen_ids = set()
    seen_hashes = set()

    items = [
        (
            s["source_id"],
            s["agency"],
            s["filename"],
            "initial_official_source",
            s["url"],
        )
        for s in SOURCES
    ] + EXTRA

    for sid, agency, filename, role, fallback in items:
        if sid in seen_ids:
            raise ValueError(f"Duplicate source ID: {sid}")

        path = SHARED_DOS if sid == "DOS-TEMP-WORKER" else ROOT / filename

        if not path.is_file():
            raise FileNotFoundError(path)

        info = inspect_file(path)

        if info["sha256"] in seen_hashes:
            raise ValueError(f"Duplicate source content: {sid}")

        seen_ids.add(sid)
        seen_hashes.add(info["sha256"])

        detected = info.pop("detected_url")
        resolved_url = detected or fallback

        if resolved_url and not official_url(resolved_url):
            raise ValueError(f"Non-official URL: {sid}")

        url_status = (
            "html_metadata"
            if detected else
            "listed_url_unverified"
            if fallback else
            "needs_url_review"
        )

        records.append({
            "source_id": sid,
            "agency": agency,
            "source_role": role,
            "url": resolved_url,
            "url_verification_status": url_status,
            "local_path": path.as_posix(),
            **info,
            "review_status": "needs_review",
        })

        print(
            f"[PASS] {sid} | "
            f"{info['size_bytes']} bytes | "
            f"URL: {url_status}"
        )

    manifest = {
        "country": "USA",
        "team_reference_program_id": "US-WK-01",
        "program_name": "H-1B Specialty Occupation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_count": len(records),
        "official_sources": records,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    ROOT.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\n=== H-1B SOURCE MANIFEST ===")
    print("TOTAL SOURCES:", len(records))
    print(
        "URL REVIEW REQUIRED:",
        sum(
            r["url_verification_status"] != "html_metadata"
            for r in records
        ),
    )
    print("VALIDATION:", manifest["validation_status"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()