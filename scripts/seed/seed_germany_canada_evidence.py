
import json
import os
from collections import Counter
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "processed"

EXPECTED_FILES = {"germany": 6, "canada": 4}
EXPECTED_COUNTS = {"germany": 36, "canada": 182}

COUNTRY_PREFIX = {"germany": "DE", "canada": "CA"}


def is_evidence_field(name):
    return name == "evidence" or name.endswith("_evidence")


def get_source(record, evidence, field):
    source_file = evidence.get("source_file")

    matching_sources = [
        value
        for value in record.values()
        if isinstance(value, dict)
        and value.get("source_file") == source_file
        and value.get("source_url")
    ] if source_file else []

    if matching_sources:
        urls = {item["source_url"] for item in matching_sources}

        if len(urls) != 1:
            raise ValueError(
                f"Conflicting source URLs for {source_file}"
            )

        source = matching_sources[0]
    elif field == "embassy_evidence":
        source = record.get("embassy_source") or {}
    else:
        source = (
            record.get("official_source")
            or record.get("source")
            or {}
        )

    if not isinstance(source, dict):
        source = {}

    return (
        evidence.get("source_url") or source.get("source_url"),
        source_file or source.get("source_file"),
        evidence.get("source_sha256") or source.get("source_sha256"),
    )

def source_location(evidence):
    if evidence.get("line_number") is not None:
        return f"line:{evidence['line_number']}"

    if evidence.get("source_line") is not None:
        return f"line:{evidence['source_line']}"

    start = evidence.get("start_line")
    end = evidence.get("end_line")

    if start is not None and end is not None:
        return f"lines:{start}-{end}"

    if start is not None:
        return f"line:{start}"

    if evidence.get("html_table_index") is not None:
        return f"html_table:{evidence['html_table_index']}"

    return None


def load_rows():
    rows = []
    ids = set()
    programs = set()
    counts = Counter()
    generated_ids = 0
    no_exact_quote = 0

    for country in ("germany", "canada"):
        files = sorted(
            (DATA_ROOT / country).rglob("*.json")
        )

        if len(files) != EXPECTED_FILES[country]:
            raise ValueError(
                f"Unexpected {country} file count: {len(files)}"
            )

        for path in files:
            record = json.loads(
                path.read_text(encoding="utf-8-sig")
            )

            program = record.get("program")

            if not isinstance(program, str) or not program:
                raise ValueError(f"Missing program: {path}")

            program_id = (
                f"{COUNTRY_PREFIX[country]}:{program}"
            )
            programs.add(program_id)

            for field, items in record.items():
                if not is_evidence_field(field):
                    continue

                if not isinstance(items, list):
                    continue

                for evidence in items:
                    if not isinstance(evidence, dict):
                        raise ValueError(
                            f"Invalid evidence item: {path}"
                        )

                    evidence_id = evidence.get("evidence_id")
                    derived_id = False

                    if not evidence_id:
                        # 독일 공통 요건 4건:
                        # 기존 원본 행 번호로 파생 ID 생성.
                        line = evidence.get("source_line")

                        if (
                            country != "germany"
                            or program != "skilled_worker"
                            or field != "shared_requirement_evidence"
                            or line is None
                        ):
                            raise ValueError(
                                f"Unidentified evidence: {path}"
                            )

                        evidence_id = (
                            f"DE:skilled_worker:"
                            f"shared_requirement:line_{line}"
                        )

                        derived_id = True
                        generated_ids += 1

                    if evidence_id in ids:
                        raise ValueError(
                            f"Duplicate evidence ID: {evidence_id}"
                        )

                    ids.add(evidence_id)

                    url, source_file, sha256 = get_source(
                        record, evidence, field
                    )

                    if not all((url, source_file, sha256)):
                        raise ValueError(
                            f"Incomplete source: {evidence_id}"
                        )

                    exact_quote = evidence.get("exact_quote")

                    if not isinstance(exact_quote, str) or not exact_quote.strip():
                        exact_quote = None
                        no_exact_quote += 1

                    metadata = {
                        "processed_file": path.relative_to(
                            ROOT
                        ).as_posix(),
                        "evidence_field": field,
                        "original_evidence": evidence,
                        "derived_evidence_id": derived_id,
                        "source_hash_verified": False,
                        "ingestion_status": "imported_unreviewed",
                    }

                    if exact_quote is None:
                        metadata["quote_format"] = (
                            "source_quotes"
                            if evidence.get("source_quotes")
                            else "structured_or_missing"
                        )

                    rows.append(
                        (
                            evidence_id,
                            program_id,
                            country,
                            evidence.get("evidence_id"),
                            evidence.get("source_section_id"),
                            url,
                            source_file,
                            sha256,
                            exact_quote,
                            source_location(evidence),
                            "needs_review",
                            Jsonb(metadata),
                        )
                    )

                    counts[country] += 1

    for country, expected in EXPECTED_COUNTS.items():
        if counts[country] != expected:
            raise ValueError(
                f"{country}: expected {expected}, "
                f"found {counts[country]}"
            )

    if len(rows) != 218:
        raise ValueError(
            f"Expected 218 rows, found {len(rows)}"
        )

    if generated_ids != 4:
        raise ValueError(
            f"Expected 4 derived IDs, found {generated_ids}"
        )

    if no_exact_quote != 9:
        raise ValueError(
            f"Expected 9 non-text evidence items, "
            f"found {no_exact_quote}"
        )

    return rows, programs, counts, generated_ids, no_exact_quote


def main():
    load_dotenv(ROOT / ".env")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    (
        rows,
        programs,
        counts,
        generated_ids,
        no_exact_quote,
    ) = load_rows()

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT program_id
                FROM programs
                WHERE country IN ('germany', 'canada')
                """
            )
            existing_programs = {
                row[0] for row in cur.fetchall()
            }

            missing_programs = programs - existing_programs

            if missing_programs:
                raise ValueError(
                    f"Missing DB programs: {sorted(missing_programs)}"
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

    print("=== GERMANY & CANADA EVIDENCE SEED ===")
    print("Programs verified:", len(programs))
    print("Germany evidence:", counts["germany"])
    print("Canada evidence:", counts["canada"])
    print("Total processed:", len(rows))
    print("Derived IDs:", generated_ids)
    print("Items without exact_quote:", no_exact_quote)
    print("New records inserted:", inserted)
    print("Existing IDs skipped:", len(rows) - inserted)
    print("Review status: needs_review")
    print("Source hash verification: pending")



def seed_policies():
    """독일·캐나다 Policy Candidate를 안전하게 적재한다."""
    from collections import Counter

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    country_prefix = {
        "germany": "DE",
        "canada": "CA",
    }

    expected_counts = {
        "germany": 19,
        "canada": 21,
    }

    rows = []
    policy_ids = set()
    program_ids = set()
    counts = Counter()

    reference_count = 0
    unresolved_count = 0

    for country in ("germany", "canada"):
        files = sorted(
            (DATA_ROOT / country).rglob("*.json")
        )

        expected_files = 6 if country == "germany" else 4

        if len(files) != expected_files:
            raise ValueError(
                f"{country}: unexpected file count {len(files)}"
            )

        for path in files:
            record = json.loads(
                path.read_text(encoding="utf-8-sig")
            )

            program = record.get("program")

            if not isinstance(program, str) or not program:
                raise ValueError(f"Invalid program: {path}")

            program_id = f"{country_prefix[country]}:{program}"
            program_ids.add(program_id)

            for policy in record.get("policy_candidates", []):
                policy_id = policy.get("policy_id")

                if not isinstance(policy_id, str) or not policy_id:
                    raise ValueError(
                        f"Missing policy ID: {path}"
                    )

                if policy_id in policy_ids:
                    raise ValueError(
                        f"Duplicate policy ID: {policy_id}"
                    )

                policy_ids.add(policy_id)

                approval_fields = (
                    "legal_validation_approved",
                    "approved_for_eligibility_decision",
                    "approved_for_embedding",
                    "approved_for_user_answers",
                )

                if any(
                    policy.get(field) is True
                    for field in approval_fields
                ):
                    raise ValueError(
                        f"Unexpected approved policy: {policy_id}"
                    )

                source_ids = policy.get("source_evidence_ids")

                if source_ids is None:
                    single_id = policy.get("source_evidence_id")
                    source_ids = [single_id] if single_id else []

                if (
                    not isinstance(source_ids, list)
                    or any(
                        not isinstance(eid, str) or not eid
                        for eid in source_ids
                    )
                ):
                    raise ValueError(
                        f"Invalid references: {policy_id}"
                    )

                if len(source_ids) != len(set(source_ids)):
                    raise ValueError(
                        f"Duplicate references: {policy_id}"
                    )

                reference_count += len(source_ids)

                if not source_ids:
                    unresolved_count += 1

                metadata = {
                    "processed_file": path.relative_to(
                        ROOT
                    ).as_posix(),
                    "original_policy": policy,
                    "source_section_id": policy.get(
                        "source_section_id"
                    ),
                    "evidence_link_status": (
                        "direct_reference_verified"
                        if source_ids
                        else "requires_manual_review"
                    ),
                    "ingestion_status": "imported_unreviewed",
                }

                rows.append(
                    (
                        policy_id,
                        program_id,
                        country,
                        policy.get("topic"),
                        source_ids,
                        policy.get("source_text"),
                        "needs_review",
                        False,
                        False,
                        False,
                        False,
                        Jsonb(metadata),
                    )
                )

                counts[country] += 1

    for country, expected in expected_counts.items():
        if counts[country] != expected:
            raise ValueError(
                f"{country}: expected {expected}, "
                f"found {counts[country]}"
            )

    if len(rows) != 40:
        raise ValueError(
            f"Expected 40 policies, found {len(rows)}"
        )

    if reference_count != 46:
        raise ValueError(
            f"Expected 46 references, found {reference_count}"
        )

    if unresolved_count != 13:
        raise ValueError(
            f"Expected 13 unresolved policies, "
            f"found {unresolved_count}"
        )

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT program_id
                FROM programs
                WHERE country IN ('germany', 'canada')
                """
            )

            existing_programs = {
                row[0] for row in cur.fetchall()
            }

            missing_programs = program_ids - existing_programs

            if missing_programs:
                raise ValueError(
                    f"Missing programs: {sorted(missing_programs)}"
                )

            cur.execute(
                """
                SELECT evidence_id, program_id
                FROM evidence
                WHERE country IN ('germany', 'canada')
                """
            )

            db_evidence = {
                evidence_id: program_id
                for evidence_id, program_id in cur.fetchall()
            }

            # 저장 전에 모든 Evidence 참조를 검사한다.
            for row in rows:
                policy_id = row[0]
                program_id = row[1]
                source_ids = row[4]

                for evidence_id in source_ids:
                    if db_evidence.get(evidence_id) != program_id:
                        raise ValueError(
                            f"Invalid evidence reference: "
                            f"{policy_id} -> {evidence_id}"
                        )

            inserted = 0

            for row in rows:
                cur.execute(
                    """
                    INSERT INTO policy_candidates (
                        policy_id,
                        program_id,
                        country,
                        topic,
                        source_evidence_ids,
                        policy_text,
                        review_status,
                        legal_validation_approved,
                        approved_for_eligibility_decision,
                        approved_for_embedding,
                        approved_for_user_answers,
                        metadata
                    )
                    VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (policy_id)
                    DO NOTHING
                    """,
                    row,
                )

                inserted += cur.rowcount

    print("=== GERMANY & CANADA POLICY SEED ===")
    print("Germany policies:", counts["germany"])
    print("Canada policies:", counts["canada"])
    print("Total processed:", len(rows))
    print("Direct evidence references:", reference_count)
    print("Policies without direct references:", unresolved_count)
    print("New records inserted:", inserted)
    print("Existing IDs skipped:", len(rows) - inserted)
    print("Review status: needs_review")
    print("Approval flags: False")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed Germany and Canada data"
    )

    parser.add_argument(
        "--evidence",
        action="store_true",
        help="Seed evidence records",
    )

    parser.add_argument(
        "--policies",
        action="store_true",
        help="Seed policy candidates",
    )

    args = parser.parse_args()

    if args.evidence and args.policies:
        parser.error(
            "Choose either --evidence or --policies"
        )

    if args.policies:
        seed_policies()
    else:
        main()