
import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
JP_ROOT = ROOT / "data" / "processed" / "japan"

PROGRAMS = {
    "employment": "JP:JP-EM-01",
    "student": "JP:JP-ST-01",
    "working_holiday": "JP:JP-WH-01",
}

# 통합본과 원본 구조화 파일을 중복 적재하지 않는다.
EMPLOYMENT_FILES = [
    "japan_employment_coe_common_structured.json",
    "japan_employment_coe_category34_structured.json",
    "japan_employment_change_integrated.json",
    "japan_employment_renewal_integrated.json",
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def processed_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_url_from(value):
    if isinstance(value, str) and value.startswith("https://"):
        return value

    if isinstance(value, dict):
        for key in ("source_url", "url", "embassy", "mofa"):
            result = value.get(key)
            if isinstance(result, str) and result.startswith("https://"):
                return result

    return None


def find_source_url(data, record):
    # 개별 증거의 출처가 파일 공통 출처보다 우선한다.
    evidence = record.get("evidence")

    if isinstance(evidence, dict):
        url = source_url_from(evidence)
        if url:
            return url

    url = source_url_from(record.get("source"))
    if url:
        return url

    url = source_url_from(data.get("source_url"))
    if url:
        return url

    source = data.get("source")

    # WH rules는 source가 여러 공식 기관을 가리킬 수 있다.
    if isinstance(source, dict):
        reference = record.get("source")
        if isinstance(reference, str):
            url = source.get(reference)
            if isinstance(url, str) and url.startswith("https://"):
                return url

    url = source_url_from(source)
    if url:
        return url

    return source_url_from(data.get("sources"))


def extract_quote(group, record):
    if group == "employment":
        return record.get("raw_row_text_ja")

    if group == "student":
        # name_ja는 PDF 제출서류 행의 일본어 항목명이다.
        # 적용 조건은 원문과 합성하지 않고 metadata에 보존한다.
        return record.get("name_ja")

    if group == "working_holiday":
        evidence = record.get("evidence")

        if isinstance(evidence, dict):
            value = evidence.get("original_text")
            if isinstance(value, str) and value.strip():
                return value

        for key in ("original_text", "raw_text", "raw_text_ja"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def candidate_files():
    for name in EMPLOYMENT_FILES:
        yield "employment", JP_ROOT / "employment" / name

    for path in sorted((JP_ROOT / "student").glob("*.json")):
        yield "student", path

    # 일본 워킹홀리데이는 모든 JSON을 검토하지만
    # 공식 원문이 추출 가능한 레코드만 적재한다.
    for path in sorted((JP_ROOT / "working_holiday").glob("*.json")):
        yield "working_holiday", path


def record_collections(group, data):
    if group in ("employment", "student"):
        return [("documents", data.get("documents", []))]

    collections = []

    for key in ("documents", "requirements", "country_specific_evidence"):
        value = data.get(key)

        if isinstance(value, list):
            collections.append((key, value))

    # 별도의 원문 텍스트가 있는 안내 자료
    # 원문이 문자열일 때만 추가한다.
    original = data.get("original_text")

    if isinstance(original, str) and original.strip():
        collections.append((
            "page_original_text",
            [{"original_text": original, "record_id": "PAGE"}],
        ))

    return collections


def make_rows():
    rows = []
    skipped = []
    seen = set()
    scanned = Counter()

    for group, path in candidate_files():
        if not path.is_file():
            raise FileNotFoundError(path)

        data = read_json(path)

        if not isinstance(data, dict):
            raise ValueError(f"Unexpected JSON root: {path}")

        program_id = PROGRAMS[group]
        scanned[group] += 1

        file_name = path.relative_to(JP_ROOT).as_posix()
        sha = processed_hash(path)

        source_info = data.get("source")

        official_source_hash = data.get("source_sha256")

        if isinstance(source_info, dict):
            official_source_hash = (
                official_source_hash
                or source_info.get("source_sha256")
            )

        for collection, records in record_collections(group, data):
            if not isinstance(records, list):
                raise ValueError(
                    f"Invalid collection: {file_name} / {collection}"
                )

            for index, record in enumerate(records, 1):
                if not isinstance(record, dict):
                    skipped.append((file_name, index, "not_dict"))
                    continue

                quote = extract_quote(group, record)

                if not isinstance(quote, str) or not quote.strip():
                    skipped.append((
                        file_name, index, "no_verbatim_text"
                    ))
                    continue

                source_url = find_source_url(data, record)

                if not source_url:
                    skipped.append((
                        file_name, index, "no_source_url"
                    ))
                    continue

                original_id = (
                    record.get("document_id")
                    or record.get("rule_id")
                    or record.get("evidence_id")
                    or record.get("record_id")
                    or f"ROW-{index:04d}"
                )

                local_id = (
                    f"{path.stem}:{collection}:{original_id}"
                )
                evidence_id = f"{program_id}:{local_id}"

                if evidence_id in seen:
                    raise ValueError(
                        f"Duplicate evidence ID: {evidence_id}"
                    )

                seen.add(evidence_id)

                location = (
                    f"file={file_name};"
                    f"collection={collection};"
                    f"row={record.get('row_number', index)};"
                    f"page={record.get('page', 'unknown')}"
                )

                metadata = {
                    "dataset_type": "japan_structured_evidence",
                    "source_record_id": str(original_id),
                    "source_collection": collection,
                    "processed_file": file_name,
                    "processed_file_sha256": sha,
                    "source_text_field": (
                        "raw_row_text_ja"
                        if group == "employment"
                        else "name_ja"
                        if group == "student"
                        else "original_text_or_nested_evidence"
                    ),
                    "source_record": record,
                    "application_type": data.get("application_type"),
                    "school_category": data.get("school_category"),
                    "school_classification": data.get(
                        "school_classification"
                    ),
                    "route_id": data.get("route_id"),
                    "source_document_type": "structured_json",
                    "legal_validation_status": "needs_review",
                    "automatic_eligibility_rules_enabled": False,
                    "approved_for_user_answers": False,
                }

                rows.append((
                    evidence_id,
                    program_id,
                    "japan",
                    str(original_id),
                    file_name,
                    source_url,
                    file_name,
                    official_source_hash,
                    quote.strip(),
                    location,
                    "needs_review",
                    Jsonb(metadata),
                ))

    return rows, skipped, scanned

def seed_japan_policies(check_only=True):
    """Create review-only policy candidates linked to existing Evidence."""

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    evidence_id,
                    program_id,
                    source_url,
                    exact_quote,
                    metadata
                FROM evidence
                WHERE country = %s
                ORDER BY program_id, evidence_id
                """,
                ("japan",),
            )

            evidence_rows = cur.fetchall()

            if len(evidence_rows) != 170:
                raise ValueError(
                    f"Expected 170 Japan Evidence, found {len(evidence_rows)}"
                )

            prepared = []
            excluded = Counter()

            for evidence_id, program_id, url, quote, meta in evidence_rows:
                meta = meta or {}
                record = meta.get("source_record") or {}
                collection = meta.get("source_collection")
                source_file = meta.get("processed_file", "")

                if not isinstance(record, dict):
                    excluded["invalid_source_record"] += 1
                    continue

                # 취업: 원문 서류 행과 카테고리 적용 조건이 있는 항목
                if program_id == "JP:JP-EM-01":
                    if collection != "documents":
                        excluded["employment_not_document"] += 1
                        continue
                    topic = "application_document"

                # 유학: 학교 유형별 제출서류 항목
                elif program_id == "JP:JP-ST-01":
                    if (
                        collection != "documents"
                        or not record.get("name_ja")
                    ):
                        excluded["student_not_document"] += 1
                        continue
                    topic = "school_specific_document"

                # 워킹홀리데이: 자격조건과 제출서류만 우선 정책화
                elif program_id == "JP:JP-WH-01":
                    if collection == "requirements":
                        topic = "participant_requirement"
                    elif collection == "documents":
                        topic = "application_document"
                    else:
                        excluded["working_holiday_context_only"] += 1
                        continue

                else:
                    excluded["unknown_program"] += 1
                    continue

                if not isinstance(quote, str) or not quote.strip():
                    excluded["missing_quote"] += 1
                    continue

                if not isinstance(url, str) or not url.startswith("https://"):
                    excluded["missing_source_url"] += 1
                    continue

                # Evidence ID로부터 재현 가능한 고정 Policy ID 생성
                digest = hashlib.sha256(
                    evidence_id.encode("utf-8")
                ).hexdigest()[:24]

                policy_id = f"JP-POL-{digest}"

                policy_metadata = {
                    "dataset_type": "japan_policy_candidate",
                    "source_evidence_id": evidence_id,
                    "source_url": url,
                    "processed_file": source_file,
                    "source_collection": collection,
                    "source_record": record,
                    "application_type": meta.get("application_type"),
                    "school_category": meta.get("school_category"),
                    "school_classification": meta.get(
                        "school_classification"
                    ),
                    "route_id": meta.get("route_id"),
                    "source_excerpt_verbatim": True,
                    "human_review_decision": "policy_draft_candidate",
                    "legal_validation_status": "needs_review",
                    "rule_interpretation_status": "not_approved",
                    "automatic_eligibility_rules_enabled": False,
                    "current_policy_verified": False,
                    "policy_role": "review_only",
                }

                prepared.append((
                    policy_id,
                    program_id,
                    "japan",
                    topic,
                    [evidence_id],
                    quote.strip(),
                    "needs_review",
                    False,
                    False,
                    False,
                    False,
                    Jsonb(policy_metadata),
                ))

            ids = [row[0] for row in prepared]

            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate Japan policy IDs")

            counts = Counter(row[1] for row in prepared)

            if any(counts[p] == 0 for p in PROGRAMS.values()):
                raise ValueError(
                    "Missing policy candidates for a Japan program"
                )

            # 기존 정책과 충돌하는지 확인
            cur.execute(
                """
                SELECT policy_id, program_id, source_evidence_ids,
                       policy_text
                FROM policy_candidates
                WHERE country = %s
                """,
                ("japan",),
            )

            existing = {
                pid: (program, refs, text)
                for pid, program, refs, text in cur.fetchall()
            }

            for row in prepared:
                old = existing.get(row[0])
                expected = (row[1], row[4], row[5])

                if old is not None and old != expected:
                    raise ValueError(
                        f"Existing policy conflict: {row[0]}"
                    )

            new_rows = [
                row for row in prepared
                if row[0] not in existing
            ]

            print("=== JAPAN POLICY VALIDATION ===")
            print("DB Evidence:", len(evidence_rows))
            print("Selected candidates:", len(prepared))
            print("By program:", dict(sorted(counts.items())))
            print("Excluded:", sum(excluded.values()))
            print("Exclusion reasons:", dict(excluded))
            print("Unique IDs:", len(set(ids)))
            print("Evidence linked:", len(prepared))
            print("Missing Evidence refs: 0")
            print("Already in DB:", len(prepared) - len(new_rows))
            print("Ready to insert:", len(new_rows))
            print("Review status: needs_review")
            print("Approval flags: False")

            if check_only:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

            inserted = 0

            for row in new_rows:
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
                    ON CONFLICT (policy_id) DO NOTHING
                    """,
                    row,
                )
                inserted += cur.rowcount

    print("=== JAPAN POLICY SEED ===")
    print("Inserted:", inserted)
    print("Skipped existing:", len(prepared) - inserted)

def main():
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--insert", action="store_true")

    parser.add_argument(
        "--policies",
        action="store_true",
        help="Validate or seed Japan Policy Candidates",
    )

    args = parser.parse_args()

    if args.policies:
        seed_japan_policies(check_only=args.check)
        return

    if not JP_ROOT.is_dir():
        raise FileNotFoundError(JP_ROOT)

    rows, skipped, scanned = make_rows()

    counts = Counter(row[1] for row in rows)
    reasons = Counter(reason for _, _, reason in skipped)

    print("=== JAPAN EVIDENCE VALIDATION ===")
    print("Source files:", sum(scanned.values()))
    print("Files by group:", dict(scanned))
    print("Prepared Evidence:", len(rows))
    print("Evidence by program:", dict(sorted(counts.items())))
    print("Skipped entries:", len(skipped))
    print("Skip reasons:", dict(reasons))
    print("Skip samples:", skipped[:12])

    if len(rows) != len(set(row[0] for row in rows)):
        raise ValueError("Duplicate Evidence IDs")

    if any(counts[p] == 0 for p in PROGRAMS.values()):
        raise ValueError(
            "At least one Japan program has no Evidence candidates"
        )

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT program_id
                FROM programs
                WHERE country = %s
                """,
                ("japan",),
            )

            existing_programs = {
                item[0] for item in cur.fetchall()
            }

            missing = set(PROGRAMS.values()) - existing_programs

            if missing:
                raise ValueError(
                    f"Missing DB programs: {sorted(missing)}"
                )

            # 기존 ID와 충돌하면 무조건 건너뛰는 대신
            # 실제 원문·출처가 일치하는지 확인한다.
            cur.execute(
                """
                SELECT evidence_id, program_id, source_url, exact_quote
                FROM evidence
                WHERE country = %s
                """,
                ("japan",),
            )

            existing = {
                item[0]: item[1:]
                for item in cur.fetchall()
            }

            for row in rows:
                old = existing.get(row[0])

                if old is None:
                    continue

                expected = (row[1], row[5], row[8])

                if old != expected:
                    raise ValueError(
                        f"Existing Evidence conflict: {row[0]}"
                    )

            new_count = sum(
                1 for row in rows if row[0] not in existing
            )

            print("Already in DB:", len(rows) - new_count)
            print("Ready to insert:", new_count)

            if args.check:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

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

    print("=== JAPAN EVIDENCE SEED ===")
    print("Inserted:", inserted)
    print("Skipped existing:", len(rows) - inserted)
    print("Review status: needs_review")
    print("Approved for eligibility: False")


if __name__ == "__main__":
    main()
