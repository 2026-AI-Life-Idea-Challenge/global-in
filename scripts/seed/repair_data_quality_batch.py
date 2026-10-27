
import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def is_empty(value):
    return value is None or not str(value).strip()


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 없음")

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            # 잠재적 동시 수정 방지
            jp = conn.execute(
                """
                SELECT evidence_id, source_file, source_sha256, metadata
                FROM evidence
                WHERE country = 'japan'
                  AND (source_sha256 IS NULL
                       OR btrim(source_sha256) = '')
                FOR UPDATE
                """
            ).fetchall()

            de_evidence = conn.execute(
                """
                SELECT evidence_id, source_file, exact_quote, metadata
                FROM evidence
                WHERE country = 'germany'
                  AND (exact_quote IS NULL
                       OR btrim(exact_quote) = '')
                FOR UPDATE
                """
            ).fetchall()

            de_policies = conn.execute(
                """
                SELECT policy_id, topic, metadata
                FROM policy_candidates
                WHERE country = 'germany'
                  AND (topic IS NULL OR btrim(topic) = '')
                FOR UPDATE
                """
            ).fetchall()

            ca_policies = conn.execute(
                """
                SELECT policy_id, policy_text, metadata
                FROM policy_candidates
                WHERE country = 'canada'
                  AND (policy_text IS NULL
                       OR btrim(policy_text) = '')
                FOR UPDATE
                """
            ).fetchall()

            ca_evidence = conn.execute(
                """
                SELECT evidence_id, exact_quote, metadata
                FROM evidence
                WHERE country = 'canada'
                  AND (exact_quote IS NULL
                       OR btrim(exact_quote) = '')
                FOR UPDATE
                """
            ).fetchall()

            expected = (29, 2, 6, 21, 7)
            actual = (
                len(jp),
                len(de_evidence),
                len(de_policies),
                len(ca_policies),
                len(ca_evidence),
            )

            if actual != expected:
                raise RuntimeError(
                    f"대상 건수 불일치: {actual}, 예상: {expected}"
                )

            print("=== DATA QUALITY BATCH PRECHECK ===")
            print("JP:", len(jp))
            print("DE_EVIDENCE:", len(de_evidence))
            print("DE_POLICIES:", len(de_policies))
            print("CA_POLICIES:", len(ca_policies))
            print("CA_TABLES:", len(ca_evidence))

            # 1. 일본: 가공 JSON 파일 경로와 해시 검증
            jp_updates = []

            for eid, source_file, source_sha, metadata in jp:
                m = metadata or {}
                expected_sha = m.get("processed_file_sha256")

                if not expected_sha or not source_file:
                    raise RuntimeError(
                        f"일본 원본 메타데이터 누락: {eid}"
                    )

                path = (
                    ROOT / "data/processed/japan" / source_file
                ).resolve()

                if not path.is_relative_to(ROOT.resolve()):
                    raise RuntimeError(
                        f"프로젝트 외부 경로: {eid}"
                    )

                if not path.is_file():
                    raise FileNotFoundError(path)

                actual_sha = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()

                if actual_sha != expected_sha:
                    raise RuntimeError(
                        f"일본 가공 파일 해시 불일치: {eid}"
                    )

                jp_updates.append((
                    eid,
                    path.relative_to(ROOT).as_posix(),
                    actual_sha,
                    source_file,
                ))

            # 2. 독일: 저장된 공식 인용문 검증
            de_ev_updates = []

            for eid, source_file, quote, metadata in de_evidence:
                original = (
                    (metadata or {}).get("original_evidence")
                    or {}
                )

                quotes = original.get("source_quotes") or []

                if len(quotes) != 3:
                    raise RuntimeError(
                        f"독일 인용문 수 불일치: {eid}"
                    )

                path = (ROOT / source_file).resolve()

                if not path.is_file():
                    raise FileNotFoundError(path)

                text = path.read_text(encoding="utf-8-sig")
                parts = []

                for item in quotes:
                    part = item.get("exact_quote")

                    if not part or part not in text:
                        raise RuntimeError(
                            f"독일 원문 불일치: {eid}"
                        )

                    parts.append(part)

                de_ev_updates.append((
                    eid,
                    "\n\n".join(parts),
                ))

            # 3. 독일: 원본 경로를 이용한 topic 복구
            de_policy_updates = []

            for pid, topic, metadata in de_policies:
                original = (
                    (metadata or {}).get("original_policy")
                    or {}
                )

                pathway = (
                    original.get("pathway")
                    or original.get("pathway_id")
                )

                if not pathway:
                    raise RuntimeError(
                        f"독일 경로 정보 없음: {pid}"
                    )

                prefix = (
                    "blue_card"
                    if pid.startswith("DE_BLUE_CARD_")
                    else "skilled_worker"
                    if pid.startswith("DE_SKILLED_")
                    else None
                )

                if prefix is None:
                    raise RuntimeError(
                        f"알 수 없는 정책 유형: {pid}"
                    )

                topic_value = f"{prefix}_{pathway}"

                de_policy_updates.append((
                    pid,
                    topic_value,
                ))

            # 4. 캐나다: 규칙이 없는 정책은 분류만 보완
            for pid, text, metadata in ca_policies:
                original = (
                    (metadata or {}).get("original_policy")
                    or {}
                )

                conditions = original.get(
                    "conditions_to_review"
                )

                if (
                    not isinstance(conditions, list)
                    or not conditions
                    or original.get("eligibility_rule") is not None
                ):
                    raise RuntimeError(
                        f"캐나다 정책 구조 확인 필요: {pid}"
                    )

            # 5. 캐나다: 표 데이터의 구조 확인
            for eid, quote, metadata in ca_evidence:
                original = (
                    (metadata or {}).get("original_evidence")
                    or {}
                )

                if eid.startswith("CA_PGWP_LANG_"):
                    if not (
                        original.get("header")
                        and original.get("rows")
                        and original.get("html_table_index")
                    ):
                        raise RuntimeError(
                            f"언어 환산표 구조 누락: {eid}"
                        )

                elif eid == "CA_PGWP_CIP_EVD_01":
                    if not (
                        original.get("data_row_count")
                        and original.get("html_table_index")
                    ):
                        raise RuntimeError(
                            f"CIP 표 구조 누락: {eid}"
                        )

                else:
                    raise RuntimeError(
                        f"예상하지 않은 캐나다 Evidence: {eid}"
                    )

            print("PRECHECK: PASS")

            # 모든 사전 검증 성공 후 DB 수정
            for eid, path, sha, previous_path in jp_updates:
                conn.execute(
                    """
                    UPDATE evidence
                    SET source_file = %s,
                        metadata = metadata || %s::jsonb
                    WHERE evidence_id = %s
                    """,
                    (
                        path,
                        Jsonb({
                            "original_source_file_value":
                                previous_path,
                            "processed_file_resolved": path,
                            "processed_file_sha256_verified": sha,
                            "processed_file_hash_verified": True,
                            "official_source_sha256_missing": True,
                            "source_provenance_review_required": True,
                        }),
                        eid,
                    ),
                )

            for eid, quote in de_ev_updates:
                conn.execute(
                    """
                    UPDATE evidence
                    SET exact_quote = %s,
                        metadata = metadata || %s::jsonb
                    WHERE evidence_id = %s
                    """,
                    (
                        quote,
                        Jsonb({
                            "quote_format":
                                "multiple_verbatim_source_excerpts",
                            "quote_sections_combined": 3,
                            "source_text_match_verified": True,
                            "legal_validation_status": "needs_review",
                        }),
                        eid,
                    ),
                )

            for pid, topic in de_policy_updates:
                conn.execute(
                    """
                    UPDATE policy_candidates
                    SET topic = %s,
                        metadata = metadata || %s::jsonb
                    WHERE policy_id = %s
                    """,
                    (
                        topic,
                        Jsonb({
                            "topic_recovery_method":
                                "original_pathway",
                            "eligibility_rule_review_required": True,
                        }),
                        pid,
                    ),
                )

            for pid, text, metadata in ca_policies:
                conn.execute(
                    """
                    UPDATE policy_candidates
                    SET metadata = metadata || %s::jsonb
                    WHERE policy_id = %s
                    """,
                    (
                        Jsonb({
                            "policy_content_type":
                                "conditions_pending_review",
                            "eligibility_rule_review_required": True,
                            "policy_text_missing_intentionally": True,
                        }),
                        pid,
                    ),
                )

            for eid, quote, metadata in ca_evidence:
                data_type = (
                    "language_score_conversion_table"
                    if eid.startswith("CA_PGWP_LANG_")
                    else "cip_eligibility_table"
                )

                conn.execute(
                    """
                    UPDATE evidence
                    SET metadata = metadata || %s::jsonb
                    WHERE evidence_id = %s
                    """,
                    (
                        Jsonb({
                            "evidence_content_type": data_type,
                            "structured_table_data": True,
                            "prose_exact_quote_not_applicable": True,
                        }),
                        eid,
                    ),
                )

            # 사후 검증
            counts = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM programs),
                    (SELECT COUNT(*) FROM policy_candidates),
                    (SELECT COUNT(*) FROM evidence),
                    (
                        SELECT COUNT(*)
                        FROM policy_candidates
                        WHERE cardinality(source_evidence_ids) = 0
                    ),
                    (
                        SELECT COUNT(*)
                        FROM policy_candidates
                        WHERE country = 'germany'
                          AND (topic IS NULL OR btrim(topic) = '')
                    ),
                    (
                        SELECT COUNT(*)
                        FROM evidence
                        WHERE country = 'germany'
                          AND (exact_quote IS NULL
                               OR btrim(exact_quote) = '')
                    )
                """
            ).fetchone()

            if counts != (40, 590, 1241, 0, 0, 0):
                raise RuntimeError(
                    f"사후 검증 실패: {counts}"
                )

            approvals = conn.execute(
                """
                SELECT COUNT(*)
                FROM policy_candidates
                WHERE legal_validation_approved
                   OR approved_for_eligibility_decision
                   OR approved_for_embedding
                   OR approved_for_user_answers
                """
            ).fetchone()[0]

            if approvals != 0:
                raise RuntimeError(
                    "승인 플래그가 변경됨"
                )

            print("=== DATA QUALITY BATCH RESULT ===")
            print("JAPAN_PROVENANCE_UPDATED:", len(jp_updates))
            print("GERMANY_QUOTES_REPAIRED:", len(de_ev_updates))
            print("GERMANY_TOPICS_REPAIRED:", len(de_policy_updates))
            print("CANADA_POLICIES_CLASSIFIED:", len(ca_policies))
            print("CANADA_TABLES_CLASSIFIED:", len(ca_evidence))
            print("PROGRAMS:", counts[0])
            print("POLICIES:", counts[1])
            print("EVIDENCE:", counts[2])
            print("UNLINKED_POLICIES:", counts[3])
            print("GERMANY_MISSING_TOPICS:", counts[4])
            print("GERMANY_MISSING_QUOTES:", counts[5])
            print("APPROVED_POLICIES:", approvals)
            print("POSTCHECK: PASS")

    print("TRANSACTION: COMMITTED")


if __name__ == "__main__":
    main()