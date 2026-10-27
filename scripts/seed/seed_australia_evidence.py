
import os
import json
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed" / "australia"

EXPECTED_FILES = 20
EXPECTED_EVIDENCE = 233


def get_source(record, evidence):
    """국가별 호주 JSON 구조 차이를 통합한다."""
    sources = (
        record.get("official_sources")
        or record.get("source_tabs")
        or {}
    )

    tab = evidence.get("source_tab")

    source = (
        sources.get(tab, {})
        if isinstance(sources, dict)
        else {}
    )

    if not isinstance(source, dict):
        source = {}

    url = (
        evidence.get("source_url")
        or source.get("source_url")
        or source.get("url")
    )
    file_path = (
        evidence.get("source_file")
        or source.get("source_file")
        or source.get("path")
    )
    sha256 = (
        evidence.get("source_sha256")
        or source.get("source_sha256")
        or source.get("sha256")
    )

    return url, file_path, sha256


def get_source_location(evidence):
    if evidence.get("line_number") is not None:
        return f"line:{evidence['line_number']}"

    start = evidence.get("start_line")
    end = evidence.get("end_line")

    if start is not None and end is not None:
        return f"lines:{start}-{end}"

    if start is not None:
        return f"line:{start}"

    return None


def load_evidence():
    files = sorted(DATA_DIR.rglob("*_evidence_draft.json"))

    if len(files) != EXPECTED_FILES:
        raise ValueError(
            f"Expected {EXPECTED_FILES} files, found {len(files)}"
        )

    rows = []
    seen_ids = set()
    program_ids = set()

    for path in files:
        record = json.loads(
            path.read_text(encoding="utf-8-sig")
        )

        program = record.get("program")

        if not isinstance(program, str) or not program:
            raise ValueError(f"Missing program: {path}")

        program_id = f"AU:{program}"
        program_ids.add(program_id)

        for evidence in record.get("evidence", []):
            evidence_id = evidence.get("evidence_id")

            if not evidence_id:
                raise ValueError(
                    f"Missing evidence_id: {path}"
                )

            if evidence_id in seen_ids:
                raise ValueError(
                    f"Duplicate evidence_id: {evidence_id}"
                )

            seen_ids.add(evidence_id)

            url, source_file, sha256 = get_source(
                record, evidence
            )

            if not all((url, source_file, sha256)):
                raise ValueError(
                    f"Incomplete source: {evidence_id}"
                )

            metadata = {
                "processed_file": path.relative_to(
                    ROOT
                ).as_posix(),
                "source_tab": evidence.get("source_tab"),
                "original_evidence": evidence,
                "ingestion_status": "metadata_mapped",
                "source_hash_verified": False,
            }

            rows.append(
                (
                    evidence_id,
                    program_id,
                    "australia",
                    evidence_id,
                    evidence.get("source_section_id"),
                    url,
                    source_file,
                    sha256,
                    evidence.get("exact_quote"),
                    get_source_location(evidence),
                    "needs_review",
                    Jsonb(metadata),
                )
            )

    if len(rows) != EXPECTED_EVIDENCE:
        raise ValueError(
            f"Expected {EXPECTED_EVIDENCE} evidence records, "
            f"found {len(rows)}"
        )

    if len(program_ids) != EXPECTED_FILES:
        raise ValueError(
            "Program count does not match file count"
        )

    return rows, program_ids


def main():
    load_dotenv(ROOT / ".env")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    rows, program_ids = load_evidence()

    # psycopg 연결 컨텍스트는 성공 시 commit,
    # 예외 발생 시 rollback한다.
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT program_id
                FROM programs
                WHERE country = 'australia'
                """
            )

            existing_programs = {
                row[0] for row in cur.fetchall()
            }

            missing_programs = (
                program_ids - existing_programs
            )

            if missing_programs:
                raise ValueError(
                    f"Missing DB programs: "
                    f"{sorted(missing_programs)}"
                )

            inserted = 0

            for row in rows:
                cur.execute(
                    """
                    INSERT INTO evidence (
                        evidence_id,
                        program_id,
                        country,
                        source_evidence_id,
                        source_id,
                        source_url,
                        source_file,
                        source_sha256,
                        exact_quote,
                        source_location,
                        review_status,
                        metadata
                    )
                    VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (evidence_id)
                    DO NOTHING
                    """,
                    row,
                )

                inserted += cur.rowcount

    print("=== AUSTRALIA EVIDENCE SEED ===")
    print(f"Programs verified: {len(program_ids)}")
    print(f"Evidence processed: {len(rows)}")
    print(f"New records inserted: {inserted}")
    print(f"Existing IDs skipped: {len(rows) - inserted}")
    print("Review status: needs_review")
    print("Source hash verification: pending")


if __name__ == "__main__":
    main()