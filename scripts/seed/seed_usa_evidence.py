
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
USA_ROOT = ROOT / "data" / "processed" / "usa"

PROGRAM_COUNTS = {
    "US-EM-01": 191,
    "US-EM-02": 13,
    "US-EM-03": 13,
    "US-WEST-01": 241,
    "US-ST-01": 45,
    "US-ST-03": 10,
    "US-WH-01": 19,
}

WEST_PDF = (
    "data/raw/usa/employment/west/"
    "west_2026_first_half_notice.pdf"
)

WEST_SHA256 = (
    "6f11ae189a6ec58bde63eb52c2e7eba"
    "80b6ec4ffde1f0620f1dca95200542c31"
)


def read_json(path):
    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024), b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def source_content_path(path):
    return path.parent / "source_content.json"


def get_companion_source(path):
    companion = source_content_path(path)

    if not companion.is_file():
        raise ValueError(
            f"Missing source_content.json: {path}"
        )

    record = read_json(companion)
    source = record.get("source", {})

    if not isinstance(source, dict):
        raise ValueError(
            f"Invalid companion source: {companion}"
        )

    return source


def make_row(
    *,
    evidence_id,
    original_id,
    program,
    evidence,
    processed_path,
    source_url,
    source_file,
    source_sha256,
    source_id=None,
    location=None,
    source_hash_verified=False,
    extra_metadata=None,
):
    if not isinstance(evidence_id, str) or not evidence_id:
        raise ValueError(
            f"Missing evidence ID: {processed_path}"
        )

    if not isinstance(evidence, dict):
        raise ValueError(
            f"Invalid evidence: {processed_path}"
        )

    if not all((
        isinstance(v, str) and v.strip()
        for v in (
            source_url,
            source_file,
            source_sha256,
        )
    )):
        raise ValueError(
            f"Incomplete source: {evidence_id}"
        )

    if (
        len(source_sha256) != 64
        or any(
            c not in "0123456789abcdef"
            for c in source_sha256.lower()
        )
    ):
        raise ValueError(
            f"Invalid SHA-256: {evidence_id}"
        )

    quote = evidence.get("source_text")

    if not isinstance(quote, str) or not quote.strip():
        raise ValueError(
            f"Missing source text: {evidence_id}"
        )

    metadata = {
        "processed_file": processed_path.relative_to(
            ROOT
        ).as_posix(),
        "original_evidence": evidence,
        "derived_evidence_id": (
            evidence_id != original_id
        ),
        "source_hash_verified": source_hash_verified,
        "ingestion_status": "imported_unreviewed",
    }

    if extra_metadata:
        metadata.update(extra_metadata)

    return (
        evidence_id,
        f"US:{program}",
        "usa",
        original_id,
        source_id,
        source_url,
        source_file,
        source_sha256,
        quote,
        Jsonb(location) if isinstance(location, dict)
        else location,
        "needs_review",
        Jsonb(metadata),
    )


def load_rows():
    rows = []
    counts = Counter()
    ids = set()
    programs = set()
    verified_sources = 0

    for path in sorted(USA_ROOT.rglob("*.json")):
        record = read_json(path)

        if not isinstance(record, dict):
            continue

        kind = record.get("dataset_type")

        if kind not in (
            "usa_program_official_evidence",
            "bridgeusa_official_evidence",
            "official_evidence_inventory",
        ):
            continue

        # H-1B 원본은 보존하고 v2만 적재한다.
        if (
            record.get("program_id") == "US-EM-01"
            and path.name == "official_evidence.json"
        ):
            continue

        program = record.get("program_id")

        if program not in PROGRAM_COUNTS:
            raise ValueError(
                f"Unexpected program ID: {program} ({path})"
            )

        programs.add(f"US:{program}")

        if kind == "usa_program_official_evidence":
            sources = record.get("sources", [])

            for source_index, source in enumerate(
                sources, 1
            ):
                url = source.get("source_url")
                source_file = source.get("source_file")
                source_sha = source.get("source_sha256")

                for block_index, block in enumerate(
                    source.get("evidence_blocks", []), 1
                ):
                    original_id = block.get("block_id")

                    if not original_id:
                        raise ValueError(
                            f"Missing block ID: {path}"
                        )

                    # 원본 block_id는 출처 간 중복될 수 있다.
                    evidence_id = (
                        f"US:{program}:"
                        f"S{source_index:02d}:"
                        f"{original_id}"
                    )

                    row = make_row(
                        evidence_id=evidence_id,
                        original_id=original_id,
                        program=program,
                        evidence=block,
                        processed_path=path,
                        source_url=url,
                        source_file=source_file,
                        source_sha256=source_sha,
                        source_id=(
                            f"S{source_index:02d}"
                        ),
                        location=(
                            f"source={source_index};"
                            f"block={block_index}"
                        ),
                        extra_metadata={
                            "source_index": source_index,
                            "source_record": {
                                k: v
                                for k, v in source.items()
                                if k != "evidence_blocks"
                            },
                            "original_block_id": original_id,
                        },
                    )

                    rows.append(row)
                    counts[program] += 1

        elif kind == "bridgeusa_official_evidence":
            source = get_companion_source(path)

            source_file = source.get("snapshot_path")
            source_sha = source.get("snapshot_sha256")
            default_url = (
                record.get("source_url")
                or source.get("source_url")
            )

            for section in record.get("sections", []):
                original_id = section.get("evidence_id")

                row = make_row(
                    evidence_id=original_id,
                    original_id=original_id,
                    program=program,
                    evidence=section,
                    processed_path=path,
                    source_url=(
                        section.get("source_url")
                        or default_url
                    ),
                    source_file=source_file,
                    source_sha256=source_sha,
                    source_id=original_id,
                    location=(
                        f"section_index="
                        f"{section.get('section_index')}"
                    ),
                    extra_metadata={
                        "companion_source": source,
                        "source_text_sha256": section.get(
                            "source_text_sha256"
                        ),
                    },
                )

                rows.append(row)
                counts[program] += 1

        elif kind == "official_evidence_inventory":
            if program != "US-WEST-01":
                raise ValueError(
                    f"Unexpected inventory: {path}"
                )

            source = get_companion_source(path)
            pdf = ROOT / WEST_PDF

            if not pdf.is_file():
                raise FileNotFoundError(pdf)

            actual_sha = sha256_file(pdf)

            if actual_sha != WEST_SHA256:
                raise ValueError(
                    "WEST PDF SHA-256 mismatch"
                )

            verified_sources += 1

            url = source.get("source_url")

            for block in record.get("evidence", []):
                original_id = block.get("evidence_id")

                location = {
                    "logical_page_candidate": block.get(
                        "logical_page_candidate"
                    ),
                    "physical_pdf_page": block.get(
                        "physical_pdf_page"
                    ),
                    "side": block.get("side"),
                    "original_block_index": block.get(
                        "original_block_index"
                    ),
                    "bbox": block.get("bbox"),
                }

                row = make_row(
                    evidence_id=original_id,
                    original_id=original_id,
                    program=program,
                    evidence=block,
                    processed_path=path,
                    source_url=url,
                    source_file=WEST_PDF,
                    source_sha256=actual_sha,
                    source_id=original_id,
                    location=json.dumps(
                        location,
                        ensure_ascii=False,
                    ),
                    source_hash_verified=True,
                    extra_metadata={
                        "source_url_role": (
                            "official_notice_landing_page"
                        ),
                        "source_file_role": (
                            "official_pdf_attachment"
                        ),
                        "source_layout_sha256": record.get(
                            "source_layout_sha256"
                        ),
                        "source_candidate_sha256": record.get(
                            "source_candidate_sha256"
                        ),
                        "companion_source": source,
                    },
                )

                rows.append(row)
                counts[program] += 1

    for row in rows:
        evidence_id = row[0]

        if evidence_id in ids:
            raise ValueError(
                f"Duplicate evidence ID: {evidence_id}"
            )

        ids.add(evidence_id)

    for program, expected in PROGRAM_COUNTS.items():
        actual = counts[program]

        if actual != expected:
            raise ValueError(
                f"{program}: expected {expected}, "
                f"found {actual}"
            )

    if len(rows) != 532:
        raise ValueError(
            f"Expected 532 rows, found {len(rows)}"
        )

    if len(programs) != 7:
        raise ValueError(
            f"Expected 7 programs, found {len(programs)}"
        )

    if verified_sources != 1:
        raise ValueError(
            "WEST PDF verification incomplete"
        )

    return rows, programs, counts

def seed_h1b_policies(check_only=True):
    policy_path = (
        USA_ROOT
        / "employment"
        / "h1b_specialty_occupation"
        / "h1b_policy_consolidation_2026_cap_gap_draft.json"
    )

    record = read_json(policy_path)

    allowed_decisions = {
        "policy_draft_candidate",
        "context_required",
        "legal_effect_review",
    }

    fields = ["policy_records"] + [
        name for name in record
        if name.endswith("_policy_drafts")
    ]

    selected = []

    for field in fields:
        for item in record.get(field, []):
            if not isinstance(item, dict):
                continue

            if item.get("human_review_decision") not in allowed_decisions:
                continue

            selected.append((field, item))

    if len(selected) != 92:
        raise ValueError(
            f"Expected 92 H-1B policies, found {len(selected)}"
        )

    policy_ids = [item.get("policy_id") for _, item in selected]

    if any(not isinstance(pid, str) or not pid for pid in policy_ids):
        raise ValueError("Missing H-1B policy ID")

    if len(set(policy_ids)) != 92:
        raise ValueError("Duplicate H-1B policy IDs")

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    rows = []
    linked_count = 0
    decisions = Counter()

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT program_id
                FROM programs
                WHERE program_id = %s
                """,
                ("US:US-EM-01",),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Missing DB program: US:US-EM-01"
                )

            cur.execute(
                """
                SELECT evidence_id, source_url, exact_quote
                FROM evidence
                WHERE program_id = %s
                """,
                ("US:US-EM-01",),
            )

            evidence_rows = cur.fetchall()

            for field, item in selected:
                policy_id = item["policy_id"]

                policy_text = (
                    item.get("policy_statement_ko")
                    or item.get("policy_statement_en")
                    or item.get("summary_ko")
                )

                if (
                    not isinstance(policy_text, str)
                    or not policy_text.strip()
                ):
                    raise ValueError(
                        f"Missing policy text: {policy_id}"
                    )

                topic = (
                    item.get("topic")
                    or item.get("topic_candidates")
                    or field.replace("_policy_drafts", "")
                )

                if isinstance(topic, list):
                    topic = (
                        str(topic[0])
                        if topic
                        else field
                    )

                if not isinstance(topic, str):
                    topic = str(topic)

                source_url = item.get("source_url")
                excerpt = item.get("evidence_excerpt")

                matched_ids = []

                if isinstance(excerpt, str) and excerpt.strip():
                    matched_ids = [
                        evidence_id
                        for evidence_id, evidence_url, quote
                        in evidence_rows
                        if (
                            evidence_url == source_url
                            and isinstance(quote, str)
                            and excerpt.strip() in quote
                        )
                    ]

                if len(matched_ids) > 1:
                    raise ValueError(
                        f"Ambiguous Evidence reference: {policy_id}"
                    )

                source_evidence_ids = (
                    matched_ids if len(matched_ids) == 1 else []
                )

                if source_evidence_ids:
                    linked_count += 1

                decision = item["human_review_decision"]
                decisions[decision] += 1

                metadata = {
                    "processed_file": policy_path.relative_to(
                        ROOT
                    ).as_posix(),
                    "original_policy": item,
                    "original_program_id": item.get(
                        "program_id", "US-WK-01"
                    ),
                    "policy_field": field,
                    "human_review_decision": decision,
                    "source_candidate_id": item.get(
                        "source_candidate_id"
                    ),
                    "source_id": item.get("source_id"),
                    "source_url": source_url,
                    "source_sha256": item.get(
                        "source_sha256"
                    ),
                    "source_paragraph_index": item.get(
                        "source_paragraph_index"
                    ),
                    "evidence_match_method": (
                        "same_url_unique_excerpt_substring"
                        if source_evidence_ids
                        else "unlinked_requires_review"
                    ),
                    "legal_validation_status": "needs_review",
                    "ingestion_status": "imported_unreviewed",
                }

                rows.append(
                    (
                        policy_id,
                        "US:US-EM-01",
                        "usa",
                        topic,
                        source_evidence_ids,
                        policy_text.strip(),
                        "needs_review",
                        False,
                        False,
                        False,
                        False,
                        Jsonb(metadata),
                    )
                )

            if linked_count != 26:
                raise ValueError(
                    f"Expected 26 Evidence links, found {linked_count}"
                )

            expected_decisions = {
                "policy_draft_candidate": 68,
                "context_required": 16,
                "legal_effect_review": 8,
            }

            if dict(decisions) != expected_decisions:
                raise ValueError(
                    f"Unexpected review decisions: {dict(decisions)}"
                )

            print("=== H1B POLICY VALIDATION ===")
            print("Selected policies:", len(rows))
            print("Unique policy IDs:", len(set(policy_ids)))
            print("Review decisions:", dict(decisions))
            print("Evidence-linked policies:", linked_count)
            print("Unlinked policies:", len(rows) - linked_count)
            print("Review status: needs_review")
            print("Approval flags: False")

            if check_only:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

            # 같은 ID가 다른 프로그램에 이미 존재하면 중단한다.
            cur.execute(
                """
                SELECT policy_id, program_id
                FROM policy_candidates
                WHERE policy_id = ANY(%s)
                """,
                (policy_ids,),
            )

            for existing_id, existing_program in cur.fetchall():
                if existing_program != "US:US-EM-01":
                    raise ValueError(
                        f"Conflicting policy ID: {existing_id}"
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

    print("=== H1B POLICY SEED ===")
    print("Inserted:", inserted)
    print("Skipped:", len(rows) - inserted)

def seed_west_policies(check_only=True):
    path = (
        USA_ROOT
        / "employment"
        / "west"
        / "west_2026_first_half_reviewed_data.json"
    )

    data = read_json(path)
    eligibility = data["eligibility"]
    documents = data["documents"]
    programs_data = data["programs"]

    source_pdf = WEST_PDF
    actual_sha = sha256_file(ROOT / source_pdf)

    if actual_sha != WEST_SHA256:
        raise ValueError("WEST PDF SHA-256 mismatch")

    # 항목: ID, 주제, 정책 문장, Evidence ID
    policies = []

    def add(suffix, topic, text, evidence_ids=None):
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Missing policy text: {suffix}")

        policies.append({
            "policy_id": f"US-WEST-01-POL-2026H1-{suffix}",
            "topic": topic,
            "policy_text": text.strip(),
            "evidence_ids": list(evidence_ids or []),
        })

    # 1. 기본 신청 자격: 5건
    add(
        "ELIG-001",
        "eligibility_nationality",
        eligibility["nationality_text"],
        ["WEST-P01-R-B017"],
    )

    add(
        "ELIG-002",
        "eligibility_visa",
        eligibility["visa_condition_text"],
        ["WEST-P01-R-B017"],
    )

    add(
        "ELIG-003",
        "eligibility_student_status",
        eligibility["student_status_text"],
        ["WEST-P01-R-B024"],
    )

    add(
        "ELIG-004",
        "eligibility_recent_graduate",
        eligibility["recent_graduate_text"],
        ["WEST-P01-R-B024", "WEST-P01-R-B046"],
    )

    add(
        "ELIG-005",
        "university_recommendation",
        eligibility["university_recommendation_text"],
        ["WEST-P02-L-B032", "WEST-P02-L-B034"],
    )

    # 2. 영어 성적: 단기·중기 각각 1건
    scores = eligibility["english_scores"]
    relationship = scores["group_relationship_in_notice"]

    for code, label in (
        ("short_term", "단기"),
        ("mid_term", "중기"),
    ):
        rule = scores[code]
        group_1 = rule["group_1"]
        group_2 = rule["group_2"]

        text = (
            f"{label} WEST 영어 성적 요건: "
            f"① TOEIC {group_1['TOEIC_min']}점 이상 또는 "
            f"G-TELP Level 2 "
            f"{group_1['GTELP_Level2_min']}점 이상. "
            f"② OPIc {group_2['OPIc_min']} 이상 또는 "
            f"TOEIC Speaking "
            f"{group_2['TOEIC_Speaking_min']} 이상 또는 "
            f"G-TELP Speaking Level "
            f"{group_2['GTELP_Speaking_min_level']} 이상. "
            f"{relationship} "
            "접수 마감일 기준 유효기간 2년 이내의 "
            "성적 기준을 적용합니다."
        )

        if code == "short_term":
            evidence_ids = [
                "WEST-P01-R-B026",
                "WEST-P01-R-B029",
                "WEST-P01-R-B032",
                "WEST-P01-R-B036",
                "WEST-P01-R-B038",
                "WEST-P01-R-B046",
                "WEST-P01-R-B047",
            ]
        else:
            evidence_ids = [
                "WEST-P01-R-B027",
                "WEST-P01-R-B030",
                "WEST-P01-R-B033",
                "WEST-P01-R-B037",
                "WEST-P01-R-B039",
                "WEST-P01-R-B046",
                "WEST-P01-R-B047",
            ]

        add(
            f"LANG-{code.upper()}",
            f"language_requirement_{code}",
            text,
            evidence_ids,
        )

    # 3. 참가 제한: 4건
    restrictions = eligibility["restrictions_in_notice"]

    if len(restrictions) != 4:
        raise ValueError("Unexpected WEST restriction count")

    for index, restriction in enumerate(restrictions, 1):
        add(
            f"RESTRICT-{index:03d}",
            "participation_restriction",
            f"WEST 지원 제한 대상: {restriction}",
        )

    # 4. 공통 제출 서류: 4건
    common_documents = documents["common_list_in_notice"]

    if len(common_documents) != 4:
        raise ValueError("Unexpected common document count")

    for index, item in enumerate(common_documents, 1):
        add(
            f"DOC-COMMON-{index:03d}",
            "required_document",
            f"WEST 공통 제출 서류: {item}",
        )

    # 5. 조건부 제출 서류: 2건
    conditional_documents = documents["conditional_items"]

    if len(conditional_documents) != 2:
        raise ValueError("Unexpected conditional document count")

    for index, item in enumerate(conditional_documents, 1):
        add(
            f"DOC-COND-{index:03d}",
            "conditional_document",
            (
                f"WEST 조건부 제출 서류: {item['item']}. "
                f"적용 조건: {item['condition']}."
            ),
        )

    # 6. 중복 지원 제한: 1건
    if programs_data["duplicate_application_prohibited"] is not True:
        raise ValueError("Unexpected duplicate application policy")

    add(
        "APPLY-001",
        "application_restriction",
        "WEST 단기·중기 프로그램의 중복 지원은 금지됩니다.",
    )

    # 7. 프로그램 구성: 단기·중기 2건
    for code, label, evidence_id in (
        ("short_term", "단기", "WEST-P01-R-B008"),
        ("mid_term", "중기", "WEST-P01-R-B006"),
    ):
        program = programs_data[code]
        internship = program["internship_months"]

        text = (
            f"2026년 상반기 {label} WEST 프로그램: "
            f"어학연수 {program['language_study_months']}개월, "
            f"인턴십 {internship['min']}~{internship['max']}개월, "
            f"여행 {program['travel_months']}개월로 구성됩니다. "
            f"공고에 기재된 최대 기간은 "
            f"{program['maximum_duration_months']}개월이며, "
            f"선발 예정 인원은 "
            f"약 {program['planned_selection_approx']}명입니다."
        )

        add(
            f"PROGRAM-{code.upper()}",
            f"program_structure_{code}",
            text,
            [evidence_id],
        )

    if len(policies) != 20:
        raise ValueError(
            f"Expected 20 WEST policies, found {len(policies)}"
        )

    ids = [p["policy_id"] for p in policies]

    if len(set(ids)) != 20:
        raise ValueError("Duplicate WEST policy IDs")

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT program_id FROM programs WHERE program_id = %s",
                ("US:US-WEST-01",),
            )

            if cur.fetchone() is None:
                raise ValueError("WEST program missing in DB")

            referenced_ids = sorted({
                eid
                for policy in policies
                for eid in policy["evidence_ids"]
            })

            cur.execute(
                """
                SELECT evidence_id
                FROM evidence
                WHERE program_id = %s
                  AND evidence_id = ANY(%s)
                """,
                ("US:US-WEST-01", referenced_ids),
            )

            existing_evidence = {
                row[0] for row in cur.fetchall()
            }

            missing_evidence = (
                set(referenced_ids) - existing_evidence
            )

            if missing_evidence:
                raise ValueError(
                    f"Missing WEST Evidence: {sorted(missing_evidence)}"
                )

            rows = []

            for policy in policies:
                metadata = {
                    "processed_file": path.relative_to(
                        ROOT
                    ).as_posix(),
                    "notice_period": "2026_first_half",
                    "historical_notice": True,
                    "source_pdf": source_pdf,
                    "source_pdf_sha256": actual_sha,
                    "source_hash_verified": True,
                    "source_evidence_link_method": (
                        "manual_source_text_and_location_review"
                        if policy["evidence_ids"]
                        else "unlinked_requires_review"
                    ),
                    "original_reviewed_dataset_type": data.get(
                        "dataset_type"
                    ),
                    "rule_interpretation_status": (
                        "not_approved"
                    ),
                    "ingestion_status": "imported_unreviewed",
                    "current_policy_verified": False,
                    "automatic_eligibility_rules_enabled": False,
                }

                rows.append((
                    policy["policy_id"],
                    "US:US-WEST-01",
                    "usa",
                    policy["topic"],
                    policy["evidence_ids"],
                    policy["policy_text"],
                    "needs_review",
                    False,
                    False,
                    False,
                    False,
                    Jsonb(metadata),
                ))

            linked = sum(
                bool(p["evidence_ids"]) for p in policies
            )

            print("=== WEST POLICY VALIDATION ===")
            print("Selected policies:", len(rows))
            print("Unique policy IDs:", len(set(ids)))
            print("Evidence-linked policies:", linked)
            print("Unlinked policies:", len(rows) - linked)
            print("Missing Evidence references:", len(missing_evidence))
            print("Notice period: 2026_first_half")
            print("WEST PDF SHA-256 verified: True")
            print("Review status: needs_review")
            print("Approval flags: False")

            if check_only:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

            cur.execute(
                """
                SELECT policy_id, program_id
                FROM policy_candidates
                WHERE policy_id = ANY(%s)
                """,
                (ids,),
            )

            for existing_id, program_id in cur.fetchall():
                if program_id != "US:US-WEST-01":
                    raise ValueError(
                        f"Policy ID conflict: {existing_id}"
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

    print("=== WEST POLICY SEED ===")
    print("Inserted:", inserted)
    print("Skipped:", len(rows) - inserted)

def seed_j1_intern_policies(check_only=True):
    """Seed human-review-only J-1 Intern policy candidates from official sections."""
    path = USA_ROOT / "employment" / "j1_intern" / "official_evidence.json"
    record = read_json(path)

    if record.get("program_id") != "US-EM-02":
        raise ValueError("Unexpected J-1 Intern program ID")

    sections = record.get("sections", [])
    source_sections = {s["evidence_id"]: s for s in sections}
    if len(sections) != 13 or len(source_sections) != 13:
        raise ValueError("Expected 13 distinct J-1 Intern sections")

    program_id = "US:US-EM-02"
    base_id = "US-J1-INTERN-POL"

    # These are verbatim substrings of the collected State Department source.
    # The conditions are not legal interpretations or approved eligibility rules.
    candidates = [
        (
            "001", "participant_eligibility", "003",
            "Interns must be foreign nationals: Who are currently enrolled in and pursuing studies at a foreign degree- or certificate-granting post-secondary academic institution outside the United States; or Who have graduated from such an institution no more than 12 months prior to their exchange visitor program start date.",
            "Enrollment OR graduation within 12 months; retain the OR relationship.",
        ),
        (
            "002", "work_restrictions", "006",
            "Interns cannot work in unskilled or casual labor positions, in positions that require or involve childcare or elder care or in any kind of position that involves medical patient care or contact.",
            "Restriction on placement types; not a determination of eligibility.",
        ),
        (
            "003", "work_restrictions", "006",
            "Nor can interns work in positions that require more than 20 percent clerical or office support work.",
            "Separate restriction on clerical/office-support duties.",
        ),
        (
            "004", "occupational_categories", "007",
            None,
            "Descriptive list of occupational categories, not blanket authorization for patient contact.",
        ),
        (
            "005", "sponsor_compliance", "010",
            "Conduct site visits of host organizations that: Have not previously participated successfully in the sponsor’s program; Have fewer than 25 employees; and Have less than $3 million in annual revenue.",
            "Keep original conjunction and thresholds; human legal interpretation required.",
        ),
        (
            "006", "sponsor_compliance", "010",
            "Collect the following information from all host organizations: Employer Identification Number (EIN); Verification of telephone number, address, brochures, website, etc.; and Proof of Worker’s Compensation Insurance Policy.",
            "Sponsor duty, never a participant eligibility rule.",
        ),
        (
            "007", "sponsor_evaluation", "011",
            "Participants in programs that exceed six months must be evaluated at midpoint and at the conclusion of the program;",
            "Six-month boundary requires further review.",
        ),
        (
            "008", "sponsor_evaluation", "011",
            "For programs with durations of less than six months, an evaluation is required at the conclusion of the program.",
            "Six-month boundary requires further review.",
        ),
        (
            "009", "host_compliance", "013",
            "Sign a completed Form DS–7002 – Training/Internship Placement Plan (T/IPP) to verify that all placements are appropriate and consistent with the objectives of the interns as outlined in their program applications and as set forth in their T/IPPs.",
            "Host organization duty, not a participant eligibility requirement.",
        ),
        (
            "010", "host_compliance", "013",
            "Notify sponsors promptly of any concerns about, changes in or deviations from T/IPPs during training and internship programs and contact sponsors immediately in the event of any emergency involving trainees or interns;",
            "Host organization reporting requirement.",
        ),
        (
            "011", "host_compliance", "013",
            "Provide continuous on-site supervision and mentoring by experienced and knowledgeable staff;",
            "Host supervision requirement.",
        ),
    ]

    if len(candidates) != 11:
        raise ValueError("Unexpected J-1 Intern candidate count")

    policy_ids = [f"{base_id}-{number}" for number, *_ in candidates]
    if len(set(policy_ids)) != len(policy_ids):
        raise ValueError("Duplicate J-1 Intern policy IDs")

    # Confirm every manually selected excerpt appears verbatim in source JSON.
    prepared = []
    for number, topic, section_number, excerpt, review_note in candidates:
        evidence_id = f"US-EM-02-SECTION-{section_number}"
        section = source_sections.get(evidence_id)
        if not section:
            raise ValueError(f"Missing source section: {evidence_id}")
        quote = section.get("source_text")
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError(f"Missing source text: {evidence_id}")
        if excerpt is None:
            excerpt = quote
        if excerpt not in quote:
            raise ValueError(f"Excerpt differs from source: {evidence_id} / {number}")
        prepared.append((
            f"{base_id}-{number}", topic, evidence_id,
            excerpt, review_note, section.get("source_url"),
        ))

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    rows = []
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT program_id FROM programs WHERE program_id = %s",
                (program_id,),
            )
            if cur.fetchone() is None:
                raise ValueError(f"Missing DB program: {program_id}")

            cur.execute(
                "SELECT evidence_id, exact_quote, source_url FROM evidence WHERE program_id = %s",
                (program_id,),
            )
            db_evidence = {
                eid: (quote, url) for eid, quote, url in cur.fetchall()
            }
            if len(db_evidence) != 13:
                raise ValueError("Expected 13 J-1 Intern Evidence records in DB")

            for policy_id, topic, evidence_id, excerpt, review_note, url in prepared:
                db_item = db_evidence.get(evidence_id)
                if not db_item or excerpt not in db_item[0] or url != db_item[1]:
                    raise ValueError(f"DB Evidence/source mismatch: {policy_id}")

                metadata = {
                    "processed_file": path.relative_to(ROOT).as_posix(),
                    "source_url": url,
                    "source_evidence_id": evidence_id,
                    "source_excerpt_verbatim": True,
                    "review_note": review_note,
                    "human_review_decision": "policy_draft_candidate",
                    "rule_interpretation_status": "not_approved",
                    "legal_validation_status": "needs_review",
                    "ingestion_status": "imported_unreviewed",
                    "automatic_eligibility_rules_enabled": False,
                }
                rows.append((
                    policy_id, program_id, "usa", topic, [evidence_id],
                    excerpt, "needs_review", False, False, False, False,
                    Jsonb(metadata),
                ))

            print("=== J1 INTERN POLICY VALIDATION ===")
            print("Selected policies:", len(rows))
            print("Unique policy IDs:", len(set(policy_ids)))
            print("Evidence-linked policies:", len(rows))
            print("Missing Evidence references: 0")
            print("Exact source excerpt matches:", len(rows))
            print("Review status: needs_review")
            print("Approval flags: False")

            if check_only:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

            cur.execute(
                "SELECT policy_id, program_id FROM policy_candidates WHERE policy_id = ANY(%s)",
                (policy_ids,),
            )
            for existing_id, existing_program in cur.fetchall():
                if existing_program != program_id:
                    raise ValueError(f"Conflicting policy ID: {existing_id}")

            inserted = 0
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO policy_candidates (
                        policy_id, program_id, country, topic,
                        source_evidence_ids, policy_text, review_status,
                        legal_validation_approved,
                        approved_for_eligibility_decision,
                        approved_for_embedding,
                        approved_for_user_answers, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (policy_id) DO NOTHING
                    """,
                    row,
                )
                inserted += cur.rowcount

    print("=== J1 INTERN POLICY SEED ===")
    print("Inserted:", inserted)
    print("Skipped:", len(rows) - inserted)

def seed_j1_trainee_policies(check_only=True):
    """Validate or insert review-only J-1 Trainee policy candidates."""
    path = USA_ROOT / "employment" / "j1_trainee" / "official_evidence.json"
    data = read_json(path)

    if data.get("program_id") != "US-EM-03":
        raise ValueError("Unexpected J-1 Trainee program ID")

    sections = data.get("sections", [])
    by_id = {s["evidence_id"]: s for s in sections}

    if len(sections) != 13 or len(by_id) != 13:
        raise ValueError("Expected 13 unique Trainee Evidence sections")

    program_id = "US:US-EM-03"
    candidates = [
        (
            "001", "participant_eligibility", "003",
            "A trainee must be a foreign national who: Has a degree or professional certificate from a foreign post-secondary academic institution and at least one year of prior related work experience in his or her occupational field outside the United States; or Has five years of work experience outside the United States in the occupational field in which they are seeking training",
            "Preserve (degree/certificate AND one year related experience) OR five years experience.",
        ),
        (
            "002", "work_restrictions", "006",
            "Trainees cannot work in unskilled or casual labor positions, in positions that require or involve childcare or elder care, or in any kind of position that involves patient care or contact.",
            "Restricted placements; separate from occupational category listing.",
        ),
        (
            "003", "work_restrictions", "006",
            "Further, sponsors must not place trainees in positions that require more than 20 percent clerical or office support work.",
            "Sponsor placement restriction, 20 percent threshold.",
        ),
        (
            "004", "training_restrictions", "006",
            "Use of the Exchange Visitor Program for ordinary employment or work purposes is strictly prohibited.",
            "Prohibition on ordinary employment purposes.",
        ),
        (
            "005", "training_restrictions", "006",
            "Sponsors are not to place trainee participants in positions, which are filled or would be filled by full-time or part-time employees.",
            "Avoid displacement of regular employees.",
        ),
        (
            "006", "training_restrictions", "006",
            "Also, the training cannot duplicate a trainee participant’s prior work experience or training.",
            "No duplicate prior experience or training.",
        ),
        (
            "007", "occupational_categories", "007",
            None,
            "Informational occupational categories, not automatic approval.",
        ),
        (
            "008", "sponsor_compliance", "010",
            "Conduct site visits of host organizations that: Have not previously participated successfully in the sponsor’s program; Have fewer than 25 employees; Have less than $3 million in annual revenue.",
            "Keep the source conjunction as written; legal interpretation pending.",
        ),
        (
            "009", "sponsor_compliance", "010",
            "Collect the following information from all host organizations: Employer Identification Number (EIN) Verification of telephone number, address, brochures, website, etc.; and Proof of worker’s compensation insurance policy or equivalent.",
            "Host information collection is a sponsor obligation.",
        ),
        (
            "010", "sponsor_evaluation", "011",
            "Participants in programs that exceed six months must be evaluated at mid-point and at the conclusion of the program;",
            "Evaluation timing for programs exceeding six months.",
        ),
        (
            "011", "sponsor_evaluation", "011",
            "For programs with durations of less than six months, the participant must be evaluated at the conclusion of the program.",
            "Exactly six months requires separate legal review.",
        ),
        (
            "012", "training_structure", "011",
            "Ensure that the training program is full-time (at least 32 hours a week).",
            "Sponsor duty to ensure minimum weekly training hours.",
        ),
        (
            "013", "host_compliance", "013",
            "Sign a completed Form DS–7002 to verify that all placements are appropriate and consistent with the objectives of the trainees or interns as outlined in their program applications and as set forth in their T/IPPs;",
            "DS-7002 host obligation, not a participant eligibility rule.",
        ),
        (
            "014", "host_compliance", "013",
            "Provide continuous on-site supervision and mentoring by experienced and knowledgeable staff;",
            "Host supervision obligation.",
        ),
    ]

    if len(candidates) != 14:
        raise ValueError("Expected 14 Trainee policy candidates")

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    prepared = []

    for number, topic, section_number, excerpt, review_note in candidates:
        evidence_id = f"US-EM-03-SECTION-{section_number}"
        section = by_id.get(evidence_id)

        if section is None:
            raise ValueError(f"Missing source section: {evidence_id}")

        source_text = section.get("source_text")

        if not isinstance(source_text, str) or not source_text.strip():
            raise ValueError(f"Missing source text: {evidence_id}")

        if excerpt is None:
            excerpt = source_text

        if excerpt not in source_text:
            raise ValueError(
                f"Source excerpt mismatch: {number}, {evidence_id}"
            )

        prepared.append({
            "policy_id": f"US-J1-TRAINEE-POL-{number}",
            "topic": topic,
            "evidence_id": evidence_id,
            "text": excerpt,
            "review_note": review_note,
            "source_url": section.get("source_url"),
        })

    policy_ids = [x["policy_id"] for x in prepared]

    if len(policy_ids) != len(set(policy_ids)):
        raise ValueError("Duplicate Trainee policy IDs")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT program_id FROM programs WHERE program_id = %s",
                (program_id,),
            )

            if cur.fetchone() is None:
                raise ValueError("J-1 Trainee program missing in DB")

            cur.execute(
                """
                SELECT evidence_id, exact_quote, source_url
                FROM evidence
                WHERE program_id = %s
                """,
                (program_id,),
            )

            db_evidence = {
                eid: (quote, url)
                for eid, quote, url in cur.fetchall()
            }

            if len(db_evidence) != 13:
                raise ValueError("Expected 13 Trainee Evidence rows")

            rows = []

            for item in prepared:
                evidence = db_evidence.get(item["evidence_id"])

                if (
                    evidence is None
                    or not isinstance(evidence[0], str)
                    or item["text"] not in evidence[0]
                    or item["source_url"] != evidence[1]
                ):
                    raise ValueError(
                        f"DB Evidence mismatch: {item['policy_id']}"
                    )

                metadata = {
                    "processed_file": path.relative_to(ROOT).as_posix(),
                    "source_url": item["source_url"],
                    "source_evidence_id": item["evidence_id"],
                    "source_excerpt_verbatim": True,
                    "review_note": item["review_note"],
                    "human_review_decision": "policy_draft_candidate",
                    "rule_interpretation_status": "not_approved",
                    "legal_validation_status": "needs_review",
                    "ingestion_status": "imported_unreviewed",
                    "automatic_eligibility_rules_enabled": False,
                }

                rows.append((
                    item["policy_id"],
                    program_id,
                    "usa",
                    item["topic"],
                    [item["evidence_id"]],
                    item["text"],
                    "needs_review",
                    False,
                    False,
                    False,
                    False,
                    Jsonb(metadata),
                ))

            print("=== J1 TRAINEE POLICY VALIDATION ===")
            print("Selected policies:", len(rows))
            print("Unique policy IDs:", len(set(policy_ids)))
            print("Evidence-linked policies:", len(rows))
            print("Missing Evidence references: 0")
            print("Exact source excerpt matches:", len(rows))
            print("Review status: needs_review")
            print("Approval flags: False")

            if check_only:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

            cur.execute(
                """
                SELECT policy_id, program_id
                FROM policy_candidates
                WHERE policy_id = ANY(%s)
                """,
                (policy_ids,),
            )

            for existing_id, existing_program in cur.fetchall():
                if existing_program != program_id:
                    raise ValueError(
                        f"Conflicting policy ID: {existing_id}"
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

    print("=== J1 TRAINEE POLICY SEED ===")
    print("Inserted:", inserted)
    print("Skipped:", len(rows) - inserted)

def seed_f1_policies(check_only=True):
    """Validate or insert F-1 policy candidates from official Evidence."""

    path = (
        USA_ROOT
        / "student"
        / "f1_academic_student"
        / "official_evidence.json"
    )

    data = read_json(path)

    if data.get("program_id") != "US-ST-01":
        raise ValueError("Unexpected F-1 program ID")

    sources = data.get("sources", [])

    if len(sources) != 2:
        raise ValueError("Expected 2 F-1 official sources")

    program_id = "US:US-ST-01"

    # 정책 후보로 사용할 근거만 선택한다.
    # (출처 번호, 원본 블록 번호, 정책 주제)
    selected = [
        (1, 1, "school_certification"),
        (2, 2, "form_i20_requirement"),
        (2, 3, "form_i20_signature_and_dependents"),
        (2, 5, "sevis_fee"),
        (2, 11, "visa_and_entry_timing"),
        (2, 12, "entry_document_requirement"),
        (2, 13, "change_of_status"),
    ]

    if len(selected) != 7:
        raise ValueError("Unexpected F-1 selection count")

    source_blocks = {}

    for source_index, source in enumerate(sources, 1):
        for block in source.get("evidence_blocks", []):
            original_id = block.get("block_id")

            evidence_id = (
                f"US:US-ST-01:"
                f"S{source_index:02d}:"
                f"{original_id}"
            )

            if evidence_id in source_blocks:
                raise ValueError(
                    f"Duplicate F-1 Evidence ID: {evidence_id}"
                )

            source_blocks[evidence_id] = {
                "block": block,
                "source_url": source.get("source_url"),
            }

    if len(source_blocks) != 45:
        raise ValueError(
            f"Expected 45 F-1 Evidence blocks, found {len(source_blocks)}"
        )

    prepared = []

    for index, (source_index, block_number, topic) in enumerate(
        selected, 1
    ):
        block_id = f"US-ST-01-BLOCK-{block_number:04d}"

        evidence_id = (
            f"US:US-ST-01:"
            f"S{source_index:02d}:"
            f"{block_id}"
        )

        source = source_blocks.get(evidence_id)

        if source is None:
            raise ValueError(
                f"Missing source Evidence: {evidence_id}"
            )

        text = source["block"].get("source_text")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"Empty source text: {evidence_id}"
            )

        prepared.append({
            "policy_id": f"US-F1-POL-{index:03d}",
            "topic": topic,
            "evidence_id": evidence_id,
            "policy_text": text.strip(),
            "source_url": source["source_url"],
        })

    policy_ids = [
        item["policy_id"]
        for item in prepared
    ]

    if len(set(policy_ids)) != len(policy_ids):
        raise ValueError("Duplicate F-1 Policy IDs")

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
                WHERE program_id = %s
                """,
                (program_id,),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "F-1 program missing in DB"
                )

            cur.execute(
                """
                SELECT evidence_id, exact_quote, source_url
                FROM evidence
                WHERE program_id = %s
                """,
                (program_id,),
            )

            db_evidence = {
                evidence_id: (quote, url)
                for evidence_id, quote, url
                in cur.fetchall()
            }

            if len(db_evidence) != 45:
                raise ValueError(
                    f"Expected 45 DB Evidence, found {len(db_evidence)}"
                )

            rows = []

            for item in prepared:
                db_record = db_evidence.get(
                    item["evidence_id"]
                )

                if db_record is None:
                    raise ValueError(
                        f"Missing DB Evidence: {item['evidence_id']}"
                    )

                quote, url = db_record

                if (
                    quote != item["policy_text"]
                    or url != item["source_url"]
                ):
                    raise ValueError(
                        f"Source mismatch: {item['policy_id']}"
                    )

                metadata = {
                    "processed_file": path.relative_to(
                        ROOT
                    ).as_posix(),
                    "source_url": item["source_url"],
                    "source_evidence_id": item["evidence_id"],
                    "source_excerpt_verbatim": True,
                    "human_review_decision": (
                        "policy_draft_candidate"
                    ),
                    "rule_interpretation_status": (
                        "not_approved"
                    ),
                    "legal_validation_status": (
                        "needs_review"
                    ),
                    "ingestion_status": (
                        "imported_unreviewed"
                    ),
                    "automatic_eligibility_rules_enabled": False,
                    "approved_as_f1_specific_rule": False,
                }

                rows.append((
                    item["policy_id"],
                    program_id,
                    "usa",
                    item["topic"],
                    [item["evidence_id"]],
                    item["policy_text"],
                    "needs_review",
                    False,
                    False,
                    False,
                    False,
                    Jsonb(metadata),
                ))

            print("=== F1 POLICY VALIDATION ===")
            print("Source Evidence:", len(db_evidence))
            print("Selected policies:", len(rows))
            print("Unique policy IDs:", len(set(policy_ids)))
            print("Evidence-linked policies:", len(rows))
            print("Missing Evidence references: 0")
            print("Exact source matches:", len(rows))
            print("Review status: needs_review")
            print("Approval flags: False")

            if check_only:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

            cur.execute(
                """
                SELECT policy_id, program_id
                FROM policy_candidates
                WHERE policy_id = ANY(%s)
                """,
                (policy_ids,),
            )

            for existing_id, existing_program in cur.fetchall():
                if existing_program != program_id:
                    raise ValueError(
                        f"Conflicting policy ID: {existing_id}"
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

    print("=== F1 POLICY SEED ===")
    print("Inserted:", inserted)
    print("Skipped:", len(rows) - inserted)

def seed_j1_college_policies(check_only=True):
    """Validate or seed J-1 College Student review-only policies."""

    path = (
        USA_ROOT
        / "student"
        / "j1_college_university_student"
        / "official_evidence.json"
    )
    data = read_json(path)
    program_id = "US:US-ST-03"

    if data.get("program_id") != "US-ST-03":
        raise ValueError("Unexpected J-1 College program ID")

    sections = data.get("sections", [])
    source = {s["evidence_id"]: s for s in sections}

    if len(sections) != 10 or len(source) != 10:
        raise ValueError("Expected 10 unique Evidence sections")

    # Original-language excerpts are retained.
    # These are unapproved policy candidates.
    candidates = [
        (
            "001",
            "participant_eligibility",
            "003",
            None,
            "Mixed alternative conditions; manual logical review required.",
        ),
        (
            "002",
            "program_duration",
            "004",
            "School Credit: University/college students may engage in degree-granting programs until completion or non-degree granting programs for no more than 24 months.",
            "Degree and non-degree program durations are distinct.",
        ),
        (
            "003",
            "student_employment",
            "004",
            "Employment: Students may engage in part-time employment under certain conditions, including good academic standing at their host institution.",
            "Not a blanket employment authorization.",
        ),
        (
            "004",
            "academic_training",
            "004",
            "Academic training: Students may participate in academic training with or without wages or other remuneration during their studies with the approval of the academic dean or adviser and the responsible officer at their sponsor organization .",
            "Approval conditions must be preserved.",
        ),
        (
            "005",
            "sponsor_academic_verification",
            "008",
            "Secure sufficient background information on the students to ensure that they have the academic credentials required for enrollment;",
            "Sponsor obligation, not automatic participant eligibility.",
        ),
        (
            "006",
            "sponsor_admission_verification",
            "008",
            "Ensure that the foreign national has been admitted to, or accepted for a student internship program offered by, the post-secondary accredited academic institution.",
            "Sponsor obligation; retain the admission/internship alternatives.",
        ),
        (
            "007",
            "sponsor_study_compliance",
            "009",
            "Ensure that they pursue a full course of study at a post-secondary accredited academic institution in the United States.",
            "Sponsor monitoring obligation; not automatically a standalone eligibility rule.",
        ),
    ]

    if len(candidates) != 7:
        raise ValueError("Unexpected candidate count")

    prepared = []

    for number, topic, section_number, excerpt, note in candidates:
        evidence_id = f"US-ST-03-SECTION-{section_number}"
        section = source.get(evidence_id)

        if section is None:
            raise ValueError(f"Missing Evidence: {evidence_id}")

        quote = section.get("source_text")

        if not isinstance(quote, str) or not quote.strip():
            raise ValueError(f"Empty Evidence: {evidence_id}")

        if excerpt is None:
            excerpt = quote

        if excerpt not in quote:
            raise ValueError(
                f"Source excerpt mismatch: {evidence_id} / {number}"
            )

        prepared.append({
            "policy_id": f"US-J1-COLLEGE-POL-{number}",
            "topic": topic,
            "evidence_id": evidence_id,
            "policy_text": excerpt,
            "source_url": section.get("source_url"),
            "review_note": note,
        })

    policy_ids = [p["policy_id"] for p in prepared]

    if len(set(policy_ids)) != 7:
        raise ValueError("Duplicate policy IDs")

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT program_id FROM programs WHERE program_id=%s",
                (program_id,),
            )

            if cur.fetchone() is None:
                raise ValueError("J-1 College program missing in DB")

            cur.execute(
                """
                SELECT evidence_id, exact_quote, source_url
                FROM evidence
                WHERE program_id=%s
                """,
                (program_id,),
            )

            db_evidence = {
                eid: (quote, url)
                for eid, quote, url in cur.fetchall()
            }

            if len(db_evidence) != 10:
                raise ValueError(
                    f"Expected 10 DB Evidence, found {len(db_evidence)}"
                )

            rows = []

            for item in prepared:
                db_item = db_evidence.get(item["evidence_id"])

                if (
                    db_item is None
                    or not isinstance(db_item[0], str)
                    or item["policy_text"] not in db_item[0]
                    or item["source_url"] != db_item[1]
                ):
                    raise ValueError(
                        f"DB Evidence mismatch: {item['policy_id']}"
                    )

                metadata = {
                    "processed_file": path.relative_to(ROOT).as_posix(),
                    "source_url": item["source_url"],
                    "source_evidence_id": item["evidence_id"],
                    "source_excerpt_verbatim": True,
                    "review_note": item["review_note"],
                    "human_review_decision": "policy_draft_candidate",
                    "legal_validation_status": "needs_review",
                    "rule_interpretation_status": "not_approved",
                    "ingestion_status": "imported_unreviewed",
                    "automatic_eligibility_rules_enabled": False,
                }

                rows.append((
                    item["policy_id"],
                    program_id,
                    "usa",
                    item["topic"],
                    [item["evidence_id"]],
                    item["policy_text"],
                    "needs_review",
                    False,
                    False,
                    False,
                    False,
                    Jsonb(metadata),
                ))

            print("=== J1 COLLEGE POLICY VALIDATION ===")
            print("Source Evidence:", len(db_evidence))
            print("Selected policies:", len(rows))
            print("Unique policy IDs:", len(set(policy_ids)))
            print("Evidence-linked policies:", len(rows))
            print("Missing Evidence references: 0")
            print("Exact source excerpt matches:", len(rows))
            print("Review status: needs_review")
            print("Approval flags: False")

            if check_only:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

            cur.execute(
                """
                SELECT policy_id, program_id
                FROM policy_candidates
                WHERE policy_id = ANY(%s)
                """,
                (policy_ids,),
            )

            for existing_id, existing_program in cur.fetchall():
                if existing_program != program_id:
                    raise ValueError(
                        f"Conflicting policy ID: {existing_id}"
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

    print("=== J1 COLLEGE POLICY SEED ===")
    print("Inserted:", inserted)
    print("Skipped:", len(rows) - inserted)

def seed_swt_policies(check_only=True):
    """Validate or insert unapproved Summer Work Travel policy candidates."""

    path = (
        USA_ROOT
        / "working_holiday"
        / "summer_work_travel"
        / "official_evidence.json"
    )
    data = read_json(path)
    program_id = "US:US-WH-01"

    if data.get("program_id") != "US-WH-01":
        raise ValueError("Unexpected SWT program ID")

    sections = data.get("sections", [])
    by_id = {
        section["evidence_id"]: section
        for section in sections
    }

    if len(sections) != 19 or len(by_id) != 19:
        raise ValueError("Expected 19 unique SWT sections")

    def get_text(number):
        evidence_id = f"US-WH-01-SECTION-{number:03d}"
        section = by_id.get(evidence_id)

        if section is None:
            raise ValueError(f"Missing Evidence: {evidence_id}")

        text = section.get("source_text")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Empty Evidence: {evidence_id}")

        return text

    def extract_between(number, start, end=None):
        text = get_text(number)

        if start not in text:
            raise ValueError(
                f"Start anchor missing: SECTION-{number:03d}: {start}"
            )

        result = text[text.index(start):]

        if end is not None:
            if end not in result:
                raise ValueError(
                    f"End anchor missing: SECTION-{number:03d}: {end}"
                )
            result = result[:result.index(end)]

        if not result.strip():
            raise ValueError("Empty extracted policy")

        return result.strip()

    # Policy candidates preserve source-language wording.
    # Source excerpts are not approved executable eligibility rules.
    candidates = [
        (
            "001",
            "participant_language_requirement",
            3,
            extract_between(
                3,
                "Sufficiently proficient in English",
                "Post-secondary school students",
            ),
            "English proficiency condition; no numeric threshold inferred.",
        ),
        (
            "002",
            "participant_academic_status",
            3,
            extract_between(
                3,
                "Post-secondary school students enrolled",
                "Have successfully completed at least one semester",
            ),
            "Accredited institution and full-time study requirements.",
        ),
        (
            "003",
            "participant_semester_requirement",
            3,
            extract_between(
                3,
                "Have successfully completed at least one semester",
                "Pre-placed in a job prior to entry",
            ),
            "At least one semester or equivalent.",
        ),
        (
            "004",
            "participant_job_placement",
            3,
            extract_between(
                3,
                "Pre-placed in a job prior to entry",
            ),
            "Visa waiver country exception must be retained.",
        ),
        (
            "005",
            "program_duration_and_return",
            8,
            get_text(8),
            "Maximum four months; home-country return before studies resume.",
        ),
        (
            "006",
            "prohibited_placements",
            9,
            extract_between(
                9,
                "Program Exclusions Sponsors must not place participants:",
                "Sponsors must also:",
            ),
            "SWT exclusions; complex exceptions require human review.",
        ),
        (
            "007",
            "sponsor_placement_safeguards",
            9,
            extract_between(
                9,
                "Sponsors must also:",
                "featured experience component",
            ),
            "Sponsor safeguards, housing, transport and job placement obligations.",
        ),
        (
            "008",
            "sponsor_prearrival_obligations",
            13,
            extract_between(
                13,
                "Sponsors are required to:",
                "Sponsors of participants who are nationals of Visa Waiver Program countries must:",
            ),
            "Prearranged employment and pre-entry information requirements.",
        ),
        (
            "009",
            "sponsor_visa_waiver_and_welfare",
            13,
            extract_between(
                13,
                "Sponsors of participants who are nationals of Visa Waiver Program countries must:",
            ),
            "Visa waiver exception, wage and participant contact obligations.",
        ),
        (
            "010",
            "host_employer_compliance",
            19,
            extract_between(
                19,
                "Host employers are required to:",
                "Program Resources",
            ),
            "Host employer wage, hours and notification obligations.",
        ),
    ]

    if len(candidates) != 10:
        raise ValueError("Expected 10 SWT policies")

    prepared = []

    for number, topic, section_number, excerpt, note in candidates:
        evidence_id = f"US-WH-01-SECTION-{section_number:03d}"
        section = by_id[evidence_id]
        source_text = section["source_text"]

        if excerpt not in source_text:
            raise ValueError(
                f"Source excerpt mismatch: {evidence_id} / {number}"
            )

        prepared.append({
            "policy_id": f"US-SWT-POL-{number}",
            "topic": topic,
            "evidence_id": evidence_id,
            "policy_text": excerpt,
            "source_url": section.get("source_url"),
            "review_note": note,
        })

    ids = [item["policy_id"] for item in prepared]

    if len(set(ids)) != 10:
        raise ValueError("Duplicate SWT policy IDs")

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
                WHERE program_id = %s
                """,
                (program_id,),
            )

            if cur.fetchone() is None:
                raise ValueError("SWT program missing in DB")

            cur.execute(
                """
                SELECT evidence_id, exact_quote, source_url
                FROM evidence
                WHERE program_id = %s
                """,
                (program_id,),
            )

            db_evidence = {
                eid: (quote, url)
                for eid, quote, url in cur.fetchall()
            }

            if len(db_evidence) != 19:
                raise ValueError(
                    f"Expected 19 SWT Evidence, found {len(db_evidence)}"
                )

            rows = []

            for item in prepared:
                db_item = db_evidence.get(item["evidence_id"])

                if (
                    db_item is None
                    or not isinstance(db_item[0], str)
                    or item["policy_text"] not in db_item[0]
                    or item["source_url"] != db_item[1]
                ):
                    raise ValueError(
                        f"DB Evidence mismatch: {item['policy_id']}"
                    )

                metadata = {
                    "processed_file": path.relative_to(ROOT).as_posix(),
                    "source_url": item["source_url"],
                    "source_evidence_id": item["evidence_id"],
                    "source_excerpt_verbatim": True,
                    "review_note": item["review_note"],
                    "human_review_decision": "policy_draft_candidate",
                    "legal_validation_status": "needs_review",
                    "rule_interpretation_status": "not_approved",
                    "ingestion_status": "imported_unreviewed",
                    "automatic_eligibility_rules_enabled": False,
                    "current_policy_verified": False,
                    "policy_role": (
                        "source_based_review_candidate"
                    ),
                }

                rows.append((
                    item["policy_id"],
                    program_id,
                    "usa",
                    item["topic"],
                    [item["evidence_id"]],
                    item["policy_text"],
                    "needs_review",
                    False,
                    False,
                    False,
                    False,
                    Jsonb(metadata),
                ))

            print("=== SWT POLICY VALIDATION ===")
            print("Source Evidence:", len(db_evidence))
            print("Selected policies:", len(rows))
            print("Unique policy IDs:", len(set(ids)))
            print("Evidence-linked policies:", len(rows))
            print("Missing Evidence references: 0")
            print("Exact source excerpt matches:", len(rows))
            print("Review status: needs_review")
            print("Approval flags: False")

            if check_only:
                print("Mode: CHECK ONLY")
                print("Database modified: False")
                return

            cur.execute(
                """
                SELECT policy_id, program_id
                FROM policy_candidates
                WHERE policy_id = ANY(%s)
                """,
                (ids,),
            )

            for existing_id, existing_program in cur.fetchall():
                if existing_program != program_id:
                    raise ValueError(
                        f"Conflicting policy ID: {existing_id}"
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

    print("=== SWT POLICY SEED ===")
    print("Inserted:", inserted)
    print("Skipped:", len(rows) - inserted)

def main():
    parser = argparse.ArgumentParser(
        description="Seed USA official evidence"
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate data without DB insertion",
    )

    parser.add_argument(
        "--insert",
        action="store_true",
        help="Insert validated evidence into DB",
    )
    parser.add_argument(
        "--policies",
        action="store_true",
        help="Validate or insert H-1B policy candidates",
    )
    parser.add_argument(
        "--west-policies",
        action="store_true",
        help="Validate or insert WEST policy candidates",
    )

    parser.add_argument(
        "--j1-intern-policies",
        action="store_true",
        help="Validate or insert J-1 Intern policy candidates",
    )

    parser.add_argument(
        "--j1-trainee-policies",
        action="store_true",
        help="Validate or insert J-1 Trainee policy candidates",
    )

    parser.add_argument(
        "--f1-policies",
        action="store_true",
        help="Validate or insert F-1 policy candidates",
    )

    parser.add_argument(
        "--j1-college-policies",
        action="store_true",
        help="Validate or insert J-1 College Student policies",
    )

    parser.add_argument(
        "--swt-policies",
        action="store_true",
        help="Validate or insert Summer Work Travel policies",
    )

    args = parser.parse_args()

    if args.check == args.insert:
        parser.error("Choose exactly one: --check or --insert")

    policy_flags = (
        args.policies,
        args.west_policies,
        args.j1_intern_policies,
        args.j1_trainee_policies,
        args.f1_policies,
        args.j1_college_policies,
        args.swt_policies,
    )

    if sum(policy_flags) > 1:
        parser.error("Choose one policy dataset at a time")

    if args.swt_policies:
        seed_swt_policies(check_only=args.check)
        return

    if args.j1_college_policies:
        seed_j1_college_policies(check_only=args.check)
        return

    if args.f1_policies:
        seed_f1_policies(check_only=args.check)
        return

    if args.j1_trainee_policies:
        seed_j1_trainee_policies(check_only=args.check)
        return

    if args.j1_intern_policies:
        seed_j1_intern_policies(check_only=args.check)
        return

    if args.west_policies:
        seed_west_policies(check_only=args.check)
        return

    if args.policies:
        seed_h1b_policies(check_only=args.check)
        return

    rows, programs, counts = load_rows()

    print("=== USA EVIDENCE VALIDATION ===")

    for program in PROGRAM_COUNTS:
        print(f"{program}: {counts[program]}")

    print("Total evidence:", len(rows))
    print("Unique IDs:", len({r[0] for r in rows}))
    print("Programs:", len(programs))
    print("WEST PDF SHA-256 verified: True")
    print("Review status: needs_review")

    if args.check:
        print("Mode: CHECK ONLY")
        print("Database modified: False")
        return

    load_dotenv(ROOT / ".env")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    inserted = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT program_id
                FROM programs
                WHERE country = 'usa'
                """
            )

            existing = {
                row[0] for row in cur.fetchall()
            }

            missing = programs - existing

            if missing:
                raise ValueError(
                    f"Missing DB programs: {sorted(missing)}"
                )

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

    print("=== USA EVIDENCE SEED ===")
    print("Inserted:", inserted)
    print("Skipped:", len(rows) - inserted)


if __name__ == "__main__":
    main()