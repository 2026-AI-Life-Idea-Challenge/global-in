
import hashlib
import html
import os
import re
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "AU:subclass_482_core_skills"

OFFICIAL_URL = (
    "https://immi.homeaffairs.gov.au/visas/getting-a-visa/"
    "visa-listing/skills-in-demand-visa-subclass-482/"
    "core-skills-stream"
)


def normalize(value):
    return re.sub(
        r"\s+",
        " ",
        html.unescape(value or ""),
    ).strip().casefold()


def prepare_evidence(policy_id, metadata):
    original = (metadata or {}).get("original_policy") or {}

    source_file = original.get("source_file")
    source_url = original.get("source_url")
    source_text = original.get("source_text")
    source_sha = original.get("source_sha256")
    section_id = original.get("source_section_id")
    start_line = original.get("source_start_line")
    end_line = original.get("source_end_line")

    if not all([
        source_file,
        source_url,
        source_text,
        source_sha,
        section_id,
    ]):
        raise ValueError(
            f"원본 출처 정보 누락: {policy_id}"
        )

    if source_url != OFFICIAL_URL:
        raise ValueError(
            f"공식 URL 불일치: {policy_id}"
        )

    if (
        not isinstance(start_line, int)
        or not isinstance(end_line, int)
        or start_line < 1
        or end_line < start_line
    ):
        raise ValueError(
            f"원본 줄 번호 오류: {policy_id}"
        )

    path = (ROOT / source_file).resolve()

    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError(
            f"프로젝트 외부 파일 경로: {policy_id}"
        )

    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()

    if actual_sha != source_sha:
        raise ValueError(
            f"원본 파일 SHA-256 불일치: {policy_id}"
        )

    text = raw.decode("utf-8-sig")
    lines = text.splitlines()

    if end_line > len(lines):
        raise ValueError(
            f"원본 줄 범위 초과: {policy_id}"
        )

    # 전체 원본뿐 아니라 기록된 줄 범위에도
    # 동일한 근거 문구가 있는지 검증
    line_text = "\n".join(
        lines[start_line - 1:end_line]
    )

    if normalize(source_text) not in normalize(text):
        raise ValueError(
            f"원본 전체에서 근거를 찾지 못함: {policy_id}"
        )

    if normalize(source_text) not in normalize(line_text):
        raise ValueError(
            f"기록된 줄 범위와 근거 불일치: {policy_id}"
        )

    evidence_id = (
        f"AU:482:RECOVERED:{section_id}"
    )

    return {
        "policy_id": policy_id,
        "evidence_id": evidence_id,
        "source_evidence_id": section_id,
        "source_id": section_id,
        "source_url": source_url,
        "source_file": path.relative_to(ROOT).as_posix(),
        "source_sha256": actual_sha,
        "exact_quote": source_text,
        "source_location": (
            f"lines={start_line}-{end_line}; "
            f"section={section_id}"
        ),
        "metadata": {
            "dataset_type": "au_482_core_eligibility_recovered",
            "source_policy_id": policy_id,
            "source_section_id": section_id,
            "source_start_line": start_line,
            "source_end_line": end_line,
            "source_verification_method": (
                "local_file_sha256_and_line_text_match"
            ),
            "legal_validation_status": "needs_review",
            "current_policy_verified": False,
            "approved_for_eligibility_decision": False,
            "approved_for_embedding": False,
            "approved_for_user_answers": False,
        },
    }


def main():
    load_dotenv(ROOT / ".env")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL 없음")

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            policies = conn.execute(
                """
                SELECT
                    policy_id,
                    metadata,
                    review_status,
                    legal_validation_approved,
                    approved_for_eligibility_decision,
                    approved_for_embedding,
                    approved_for_user_answers
                FROM policy_candidates
                WHERE program_id = %s
                  AND cardinality(source_evidence_ids) = 0
                ORDER BY policy_id
                FOR UPDATE
                """,
                (PROGRAM_ID,),
            ).fetchall()

            if len(policies) != 16:
                raise RuntimeError(
                    "예상한 호주 미연결 정책 16건과 불일치: "
                    + str(len(policies))
                )

            prepared = []

            for row in policies:
                policy_id = row[0]
                metadata = row[1]

                if row[2] != "needs_review":
                    raise RuntimeError(
                        f"검토 상태 불일치: {policy_id}"
                    )

                if any(row[3:7]):
                    raise RuntimeError(
                        f"승인된 정책 발견: {policy_id}"
                    )

                prepared.append(
                    prepare_evidence(policy_id, metadata)
                )

            new_ids = [
                item["evidence_id"]
                for item in prepared
            ]

            if len(set(new_ids)) != 16:
                raise RuntimeError(
                    "신규 Evidence ID 중복"
                )

            duplicates = conn.execute(
                """
                SELECT evidence_id
                FROM evidence
                WHERE evidence_id = ANY(%s)
                """,
                (new_ids,),
            ).fetchall()

            if duplicates:
                raise RuntimeError(
                    f"Evidence ID 충돌: {duplicates}"
                )

            print("=== AU 482 RECOVERY PRECHECK ===")
            print("POLICIES:", len(policies))
            print("SOURCE QUOTES VERIFIED:", len(prepared))
            print("SOURCE HASH VERIFIED:", len(prepared))
            print("SOURCE LINE RANGES VERIFIED:", len(prepared))
            print("ID CONFLICTS:", len(duplicates))
            print("PRECHECK: PASS")

            # 신규 Evidence 16건 생성
            for item in prepared:
                conn.execute(
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
                    """,
                    (
                        item["evidence_id"],
                        PROGRAM_ID,
                        "australia",
                        item["source_evidence_id"],
                        item["source_id"],
                        item["source_url"],
                        item["source_file"],
                        item["source_sha256"],
                        item["exact_quote"],
                        item["source_location"],
                        "needs_review",
                        Jsonb(item["metadata"]),
                    ),
                )

                updated = conn.execute(
                    """
                    UPDATE policy_candidates
                    SET source_evidence_ids = ARRAY[%s]::text[]
                    WHERE policy_id = %s
                      AND program_id = %s
                      AND cardinality(source_evidence_ids) = 0
                      AND review_status = 'needs_review'
                      AND NOT legal_validation_approved
                      AND NOT approved_for_eligibility_decision
                      AND NOT approved_for_embedding
                      AND NOT approved_for_user_answers
                    """,
                    (
                        item["evidence_id"],
                        item["policy_id"],
                        PROGRAM_ID,
                    ),
                )

                if updated.rowcount != 1:
                    raise RuntimeError(
                        "정책 연결 실패: "
                        + item["policy_id"]
                    )

            remaining_au = conn.execute(
                """
                SELECT COUNT(*)
                FROM policy_candidates
                WHERE country = 'australia'
                  AND cardinality(source_evidence_ids) = 0
                """
            ).fetchone()[0]

            if remaining_au != 0:
                raise RuntimeError(
                    f"호주 미연결 정책 잔여: {remaining_au}"
                )

            # 전체 국가에서 Evidence 참조 무결성 확인
            invalid_refs = conn.execute(
                """
                SELECT COUNT(*)
                FROM policy_candidates pc
                CROSS JOIN LATERAL
                    unnest(pc.source_evidence_ids) AS eid
                LEFT JOIN evidence e
                    ON e.evidence_id = eid
                   AND e.program_id = pc.program_id
                WHERE e.evidence_id IS NULL
                """
            ).fetchone()[0]

            if invalid_refs:
                raise RuntimeError(
                    f"잘못된 Evidence 참조: {invalid_refs}"
                )

            # 전체 DB 현황
            totals = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM evidence),
                    (SELECT COUNT(*) FROM policy_candidates),
                    (
                        SELECT COUNT(*)
                        FROM policy_candidates
                        WHERE cardinality(source_evidence_ids) = 0
                    )
                """
            ).fetchone()

            # 독일의 빈 정책 상태를 함께 확인
            de_rows = conn.execute(
                """
                SELECT policy_id, topic, policy_text
                FROM policy_candidates
                WHERE country = 'germany'
                  AND cardinality(source_evidence_ids) = 0
                ORDER BY policy_id
                """
            ).fetchall()

            if len(de_rows) != 2:
                raise RuntimeError(
                    "독일 잔여 정책 수 예상과 불일치: "
                    + str(len(de_rows))
                )

            print("=== AU 482 RECOVERY RESULT ===")
            print("INSERTED EVIDENCE:", len(prepared))
            print("LINKED POLICIES:", len(prepared))
            print("AU UNLINKED:", remaining_au)
            print("INVALID EVIDENCE REFS:", invalid_refs)

            print("=== DATABASE TOTALS ===")
            print("EVIDENCE:", totals[0])
            print("POLICIES:", totals[1])
            print("UNLINKED:", totals[2])

            print("=== GERMANY REMAINING ===")
            for pid, topic, policy_text in de_rows:
                print(
                    "POLICY:",
                    pid,
                    "TOPIC:",
                    topic,
                    "HAS_TEXT:",
                    bool(policy_text),
                )

            print("POSTCHECK: PASS")

    print("TRANSACTION: COMMITTED")


if __name__ == "__main__":
    main()