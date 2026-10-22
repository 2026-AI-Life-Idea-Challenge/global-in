
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(
    "data/raw/usa/employment/h1b_specialty_occupation"
)
MANIFEST = ROOT / "h1b_source_manifest_2026_draft.json"

SOURCES = [
    {
        "source_id": "USCIS-H1B-OVERVIEW",
        "agency": "USCIS",
        "title": "H-1B Specialty Occupations",
        "url": (
            "https://www.uscis.gov/working-in-the-united-states/"
            "temporary-workers/h-1b-specialty-occupations"
        ),
        "filename": "uscis_h1b_overview.html",
    },
    {
        "source_id": "USCIS-H1B-REGISTRATION",
        "agency": "USCIS",
        "title": "H-1B Electronic Registration Process",
        "url": (
            "https://www.uscis.gov/working-in-the-united-states/"
            "temporary-workers/h-1b-specialty-occupations/"
            "h-1b-electronic-registration-process"
        ),
        "filename": "uscis_h1b_registration.html",
    },
    {
        "source_id": "USCIS-H1B-POLICY-MANUAL",
        "agency": "USCIS",
        "title": "Policy Manual Volume 2 Part H",
        "url": "https://www.uscis.gov/policy-manual/volume-2-part-h",
        "filename": "uscis_policy_manual_part_h.html",
    },
    {
        "source_id": "DOL-H1B-PROGRAM",
        "agency": "DOL",
        "title": "H-1B Program",
        "url": "https://www.dol.gov/agencies/whd/immigration/h1b",
        "filename": "dol_h1b_program.html",
    },
    {
        "source_id": "DOL-H1B-LCA-LAW",
        "agency": "DOL",
        "title": "H-1B Labor Condition Application",
        "url": (
            "https://www.dol.gov/agencies/whd/laws-and-regulations/"
            "laws/ina/h1b"
        ),
        "filename": "dol_h1b_lca_law.html",
    },
    {
        "source_id": "DOS-TEMP-WORKER",
        "agency": "DOS",
        "title": "Temporary Worker Visas",
        "url": (
            "https://travel.state.gov/content/travel/en/"
            "us-visas/employment/temporary-worker-visas.html"
        ),
        "filename": "dos_temporary_worker_visas.html",
    },
    {
        "source_id": "DOS-H1B-2025-RESTRICTION",
        "agency": "DOS",
        "title": "Restriction on Entry of Certain Nonimmigrant Workers",
        "url": (
            "https://travel.state.gov/en/newsroom/visas/2025/"
            "restriction-on-entry-of-certain-nonimmigrant-workers.html"
        ),
        "filename": "dos_h1b_2025_restriction.html",
    },
    {
        "source_id": "USCIS-H1B-2025-MEMO",
        "agency": "USCIS",
        "title": "September 2025 H-1B Proclamation Memorandum",
        "url": (
            "https://www.uscis.gov/sites/default/files/"
            "document/memos/H1B_Proc_Memo_FINAL.pdf"
        ),
        "filename": "uscis_h1b_2025_proclamation_memo.pdf",
    },
]


def sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()


def looks_valid(content, filename):
    if filename.endswith(".pdf"):
        return content.startswith(b"%PDF-")

    sample = content[:200000].decode(
        "utf-8", errors="ignore"
    ).lower()

    return (
        "<html" in sample
        or "<!doctype html" in sample
    )


def fetch_source(source):
    output = ROOT / source["filename"]

    if output.exists():
        content = output.read_bytes()
        if not looks_valid(content, source["filename"]):
            raise ValueError(
                f"Existing file is not valid HTML/PDF: {output}"
            )
        status = "existing_verified"
    else:
        request = Request(
            source["url"],
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html,application/pdf,*/*",
            },
        )

        with urlopen(request, timeout=35) as response:
            content = response.read()
            final_url = response.geturl()
            status_code = response.getcode()

        if status_code != 200:
            raise ValueError(f"HTTP status: {status_code}")

        if not final_url.startswith("https://"):
            raise ValueError("Unexpected non-HTTPS redirect")

        if not looks_valid(content, source["filename"]):
            raise ValueError(
                "Response is not the expected HTML/PDF format"
            )

        output.write_bytes(content)
        status = "downloaded"

    return {
        **source,
        "local_path": output.as_posix(),
        "sha256": sha256_bytes(content),
        "size_bytes": len(content),
        "status": status,
        "review_status": "needs_review",
    }


def main():
    ROOT.mkdir(parents=True, exist_ok=True)

    if MANIFEST.exists():
        raise FileExistsError(
            f"Manifest already exists: {MANIFEST}"
        )

    success = []
    failed = []

    for source in SOURCES:
        sid = source["source_id"]
        print(f"[FETCH] {sid}", flush=True)

        try:
            result = fetch_source(source)
            success.append(result)

            print(
                f"  [PASS] {result['status']} | "
                f"{result['size_bytes']} bytes"
            )
        except (
            HTTPError, URLError, TimeoutError,
            ValueError, OSError
        ) as exc:
            failed.append({
                "source_id": sid,
                "agency": source["agency"],
                "url": source["url"],
                "error": str(exc),
                "review_status": "needs_review",
            })
            print(f"  [FAIL] {exc}")

    manifest = {
        "country": "USA",
        "team_reference_program_id": "US-WK-01",
        "program_name": "H-1B Specialty Occupation",
        "collected_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "requested_source_count": len(SOURCES),
        "verified_source_count": len(success),
        "failed_source_count": len(failed),
        "official_sources": success,
        "failed_sources": failed,
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    MANIFEST.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n=== H-1B OFFICIAL SOURCE COLLECTION ===")
    print("Program: US-WK-01")
    print("Requested sources:", len(SOURCES))
    print("Verified sources:", len(success))
    print("Failed sources:", len(failed))
    print("Validation status: needs_review")
    print("Saved:", MANIFEST)

    if failed:
        print("Failed IDs:", [
            x["source_id"] for x in failed
        ])
        print("[INFO] Failed sources require recovery")
    else:
        print("[PASS] All initial official sources saved")

    print("[INFO] Semantic and legal review required")


if __name__ == "__main__":
    main()