
import json
import os
from collections import defaultdict
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed" / "australia"

EXPECTED_FILES = 20
EXPECTED_POLICIES = 223
EXPECTED_LINKED = 207
EXPECTED_UNRESOLVED = 16


def load_policies():
    files = sorted(DATA_DIR.rglob("*_evidence_draft.json"))

    if len(files) != EXPECTED_FILES:
        raise ValueError(
            f"Expected {EXPECTED_FILES} files, found {len(files)}"
        )

    rows = []
    seen_policy_ids = set()
    program_ids = set()
    linked_count = 0
    unresolved_count = 0
    all_evidence_ids = set()

    for path in files:
        record = json.loads(
            path.read_text(encoding="utf-8-sig")
        )

        program = record.get("program")
        if not isinstance(program, str) or not program:
            raise ValueError(f"Missing program: {path}")

        program_id = f"AU:{program}"
        program_ids.add(program_id)

        section_map = defaultdict(list)

        for evidence in record.get("evidence", []):
            evidence_id = evidence.get("evidence_id")
            if not evidence_id:
                raise ValueError(f"Missing evidence ID: {path}")

            all_evidence_ids.add(evidence_id)

            section_id = evidence.get("source_section_id")
            if section_id:
                section_map[section_id].append(evidence_id)

        for policy in record.get("policy_candidates", []):
            policy_id = policy.get("policy_id")

            if not policy_id:
                raise ValueError(f"Missing policy ID: {path}")

            if policy_id in seen_policy_ids:
                raise ValueError(f"Duplicate policy ID: {policy_id}")

            seen_policy_ids.add(policy_id)

            section_id = policy.get("source_section_id")
            matches = section_map.get(section_id, [])

            if len(matches) == 1:
                source_evidence_ids = matches
                link_status = "section_id_matched"
                linked_count += 1
            else:
                source_evidence_ids = []
                link_status = "requires_manual_review"
                unresolved_count += 1

            # 원본 승인 여부가 True인 데이터는 자동 승인하지 않는다.
            approval_fields = (
                "legal_validation_approved",
                "approved_for_eligibility_decision",
                "approved_for_embedding",
                "approved_for_user_answers",
            )

            if any(policy.get(field) is True for field in approval_fields):
                raise ValueError(
                    f"Unexpected approved policy: {policy_id}"
                )

            metadata = {
                "processed_file": path.relative_to(
                    ROOT
                ).as_posix(),
                "source_section_id": section_id,
                "evidence_link_status": link_status,
                "original_policy": policy,
                "ingestion_status": "imported_unreviewed",
            }

            rows.append(
                (
                    policy_id,
                    program_id,
                    "australia",
                    policy.get("topic"),
                    source_evidence_ids,
                    policy.get("source_text"),
                    "needs_review",
                    False,
                    False,
                    False,
                    False,
                    Jsonb(metadata),
                )
            )

    if len(rows) != EXPECTED_POLICIES:
        raise ValueError(
            f"Expected {EXPECTED_POLICIES} policies, found {len(rows)}"
        )

    if linked_count != EXPECTED_LINKED:
        raise ValueError(
            f"Expected {EXPECTED_LINKED} linked policies, "
            f"found {linked_count}"
        )

    if unresolved_count != EXPECTED_UNRESOLVED:
        raise ValueError(
            f"Expected {EXPECTED_UNRESOLVED} unresolved policies, "
            f"found {unresolved_count}"
        )

    return rows, program_ids, all_evidence_ids, linked_count, unresolved_count


def main():
    load_dotenv(ROOT / ".env")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    (
        rows,
        program_ids,
        all_evidence_ids,
        linked_count,
        unresolved_count,
    ) = load_policies()

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT program_id
                FROM programs
                WHERE country = 'australia'
                """
            )
            db_program_ids = {r[0] for r in cur.fetchall()}

            missing_programs = program_ids - db_program_ids
            if missing_programs:
                raise ValueError(
                    f"Missing DB programs: {sorted(missing_programs)}"
                )

            cur.execute(
                """
                SELECT evidence_id
                FROM evidence
                WHERE country = 'australia'
                """
            )
            db_evidence_ids = {r[0] for r in cur.fetchall()}

            missing_evidence = all_evidence_ids - db_evidence_ids
            if missing_evidence:
                raise ValueError(
                    f"Missing DB evidence: {sorted(missing_evidence)}"
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

    print("=== AUSTRALIA POLICY SEED ===")
    print(f"Programs verified: {len(program_ids)}")
    print(f"Policies processed: {len(rows)}")
    print(f"Evidence-linked policies: {linked_count}")
    print(f"Unresolved evidence links: {unresolved_count}")
    print(f"New records inserted: {inserted}")
    print(f"Existing IDs skipped: {len(rows) - inserted}")
    print("Review status: needs_review")
    print("Approval flags: False")


if __name__ == "__main__":
    main()