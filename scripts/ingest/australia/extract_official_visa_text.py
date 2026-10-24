
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

RAW = Path("data/raw/australia")
OUTPUT = Path(
    "data/processed/australia/"
    "official_visa_text_2026_draft.json"
)

EXPECTED = {
    "employment": {
        "subclass_482_official",
        "subclass_482_core_skills",
        "subclass_482_specialist_skills",
        "subclass_482_labour_agreement",
        "subclass_186_official",
        "subclass_186_direct_entry",
        "subclass_186_temporary_residence_transition",
        "subclass_186_labour_agreement",
        "subclass_189_official",
        "subclass_189_points_tested",
        "subclass_190_official",
        "subclass_407_official",
        "subclass_407_occupational_training_types",
    },
    "student": {
        "subclass_500_official",
        "subclass_500_length_of_stay",
        "subclass_500_document_checklist_disclaimer",
        "subclass_500_application_rule_changes",
    },
    "working_holiday": {
        "subclass_417_official",
        "subclass_417_six_month_work_limitation",
        "subclass_417_specified_work",
    },
}

OFFICIAL_HOST = "immi.homeaffairs.gov.au"


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def clean_text(element):
    # 원본 HTML은 건드리지 않고 파싱 결과만 수정
    copy = BeautifulSoup(str(element), "html.parser")

    for tag in copy.find_all([
        "script", "style", "noscript",
        "template", "svg",
    ]):
        tag.decompose()

    text = copy.get_text(separator="\n", strip=True)

    lines = [
        " ".join(line.split())
        for line in text.splitlines()
    ]

    return "\n".join(
        line for line in lines if line
    )


def extract_url(soup):
    canonical = soup.find(
        "link", rel=lambda value: (
            value is not None
            and "canonical" in (
                [value.lower()]
                if isinstance(value, str)
                else [str(v).lower() for v in value]
            )
        )
    )

    candidates = []

    if canonical:
        candidates.append(canonical.get("href"))

    og = soup.find(
        "meta",
        attrs={"property": "og:url"},
    )

    if og:
        candidates.append(og.get("content"))

    for candidate in candidates:
        if not candidate:
            continue

        parsed = urlparse(candidate)

        if (
            parsed.scheme == "https"
            and parsed.hostname == OFFICIAL_HOST
        ):
            return candidate

    return None


def parse_page(category, path):
    original = path.read_bytes()

    soup = BeautifulSoup(
        original, "html.parser"
    )

    main = soup.find("main")

    if main is None:
        raise ValueError(
            f"MAIN ELEMENT MISSING: {path}"
        )

    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else ""
    )

    text = clean_text(main)

    headings = [
        {
            "level": tag.name,
            "text": tag.get_text(
                " ", strip=True
            )[:200],
        }
        for tag in main.find_all(
            ["h1", "h2", "h3", "h4"]
        )
    ]

    subclass_match = re.match(
        r"subclass_(\d+)_",
        path.stem,
    )

    if not subclass_match:
        raise ValueError(
            f"INVALID FILENAME: {path}"
        )

    subclass = subclass_match.group(1)
    source_url = extract_url(soup)

    issues = []

    if len(text) < 300:
        issues.append(
            "main_text_too_short"
        )

    if not title:
        issues.append(
            "missing_page_title"
        )

    if not source_url:
        issues.append(
            "missing_verified_canonical_url"
        )

    if re.search(
        r"access denied|403 forbidden",
        title,
        flags=re.I,
    ):
        issues.append(
            "suspected_access_denied_page"
        )

    if subclass not in (
        title + " " + (source_url or "")
    ):
        issues.append(
            "subclass_identity_needs_review"
        )

    if not headings:
        issues.append(
            "no_main_headings"
        )

    record = {
        "country": "australia",
        "category": category,
        "subclass": subclass,
        "source_file": path.as_posix(),
        "source_url": source_url,
        "source_url_status": (
            "canonical_or_og_verified"
            if source_url
            else "needs_review"
        ),
        "page_title": title,
        "source_sha256": sha256(original),
        "source_bytes": len(original),
        "main_text": text,
        "main_text_sha256": sha256(
            text.encode("utf-8")
        ),
        "main_text_length": len(text),
        "headings": headings,
        "extraction_issues": issues,
        "extraction_status": (
            "candidate_review_pending"
            if not issues
            else "needs_review"
        ),
        "section_boundaries_verified": False,
        "semantic_validation_approved": False,
        "legal_validation_approved": False,
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
    }

    return record


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT}"
        )

    records = []
    failures = []

    for category, expected_names in EXPECTED.items():
        folder = RAW / category

        actual_files = sorted(
            folder.glob("subclass_*.html")
        )

        actual_names = {
            path.stem for path in actual_files
        }

        if actual_names != expected_names:
            raise ValueError(
                f"{category}: source mismatch\n"
                f"MISSING: {sorted(expected_names - actual_names)}\n"
                f"UNEXPECTED: {sorted(actual_names - expected_names)}"
            )

        for path in actual_files:
            try:
                record = parse_page(
                    category, path
                )
                records.append(record)

            except Exception as exc:
                failures.append({
                    "source_file": path.as_posix(),
                    "error": str(exc),
                })

    source_paths = [
        record["source_file"]
        for record in records
    ]

    if len(source_paths) != len(set(source_paths)):
        raise ValueError(
            "Duplicate source paths"
        )

    text_hashes = [
        record["main_text_sha256"]
        for record in records
    ]

    duplicate_hashes = [
        digest
        for digest, count
        in Counter(text_hashes).items()
        if count > 1
    ]

    if duplicate_hashes:
        for record in records:
            if record["main_text_sha256"] in duplicate_hashes:
                record["extraction_issues"].append(
                    "duplicate_main_text"
                )
                record["extraction_status"] = "needs_review"

    report = {
        "dataset_type":
            "australia_official_visa_text_draft",
        "country": "australia",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_count_expected": 20,
        "source_count_extracted": len(records),
        "source_count_failed": len(failures),
        "category_counts": dict(
            Counter(
                record["category"]
                for record in records
            )
        ),
        "duplicate_main_text_hash_count":
            len(duplicate_hashes),
        "pages_with_extraction_issues": sum(
            bool(record["extraction_issues"])
            for record in records
        ),
        "records": records,
        "failures": failures,
        "validation_status": "needs_review",
        "section_boundaries_verified": False,
        "semantic_validation_approved": False,
        "legal_validation_approved": False,
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    saved = json.loads(
        OUTPUT.read_text(encoding="utf-8")
    )

    if len(saved["records"]) != len(records):
        raise ValueError(
            "Saved record count mismatch"
        )

    print("=== AUSTRALIA TEXT EXTRACTION ===")
    print("EXPECTED:", 20)
    print("EXTRACTED:", len(records))
    print("FAILED:", len(failures))
    print(
        "BY CATEGORY:",
        report["category_counts"]
    )
    print(
        "DUPLICATE MAIN TEXT:",
        len(duplicate_hashes)
    )
    print(
        "PAGES WITH ISSUES:",
        report["pages_with_extraction_issues"]
    )

    for record in records:
        print(
            record["subclass"],
            "|",
            Path(record["source_file"]).stem,
            "| CHARS:",
            record["main_text_length"],
            "| HEADINGS:",
            len(record["headings"]),
            "| ISSUES:",
            ",".join(
                record["extraction_issues"]
            ) or "none",
        )

    for failure in failures:
        print(
            "FAILED FILE:",
            failure["source_file"],
            "|",
            failure["error"][:150],
        )

    print("LEGAL VALIDATION: PENDING")
    print("APPROVED FOR ANSWERS: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()