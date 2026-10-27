
import hashlib
import os
import re
from pathlib import Path

import psycopg
import pymupdf
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "data/raw/usa/employment/west/west_2026_first_half_notice.pdf"
PROGRAM_ID = "US:US-WEST-01"
SOURCE_URL = "https://www.niied.go.kr/web/main/nid/niied_board/5570"
SOURCE_FILE = PDF.relative_to(ROOT).as_posix()

# 기존 Evidence 재사용: 7개 정책
REUSE = {
    "DOC-COMMON-001": ["WEST-P02-R-B019"],
    "DOC-COMMON-002": ["WEST-P02-R-B019"],
    "DOC-COMMON-003": ["WEST-P02-R-B021"],
    "DOC-COMMON-004": ["WEST-P02-R-B021"],
    "DOC-COND-001": ["WEST-P02-R-B021", "WEST-P02-R-B025"],
    "DOC-COND-002": ["WEST-P02-R-B021", "WEST-P02-R-B026"],
    "RESTRICT-004": ["WEST-P01-R-B055"],
}

# 신규 Evidence: 4개 정책
# 원본 PDF 텍스트에서 공백 제거 후 동일 문구인지 검사
NEW_QUOTES = {
    "APPLY-001": "단기·중기 프로그램 중복지원 불가",
    "RESTRICT-001": "복수 국적자",
    "RESTRICT-002": "외국 소재 대학(교) 학생",
    "RESTRICT-003": "WEST 프로그램 기 참가자",
}

# 기존 Evidence의 직접적 근거 문구
REUSE_QUOTE_CHECKS = {
    "WEST-P02-R-B019": ["WEST", "자기소개서", "증명서"],
    "WEST-P02-R-B021": ["성적증명서", "공인영어성적증명서", "지원구간"],
    "WEST-P02-R-B025": ["취업취약계층", "증빙자료"],
    "WEST-P02-R-B026": ["졸업생", "증빙"],
    "WEST-P01-R-B055": ["WEST", "참가비", "포기자"],
}


def compact(value):
    return re.sub(r"\s+", "", value or "")


def policy_id(suffix):
    return f"US-WEST-01-POL-2026H1-{suffix}"


def evidence_id(suffix):
    return f"WEST-2026H1-RECOVERED-{suffix}"


def main():
    load_dotenv(ROOT / ".env")

    if not PDF.is_file():
        raise FileNotFoundError(PDF)

    pdf_bytes = PDF.read_bytes()
    pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()

    expected_sha = (
        "6f11ae189a6ec58bde63eb52c2e7eba80b6ec4"
        "ffde1f0620f1dca95200542c31"
    )

    if pdf_sha != expected_sha:
        raise RuntimeError("WEST 원본 PDF SHA-256 불일치")

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        if len(doc) != 11:
            raise RuntimeError("WEST PDF 페이지 수 불일치")

        # 2026 상반기 모집요강의 첫 번째 물리 페이지
        page_text = doc[0].get_text("text", sort=True)

    pdf_compact = compact(page_text)

    for suffix, quote in NEW_QUOTES.items():
        if compact(quote) not in pdf_compact:
            raise RuntimeError(
                f"원본 PDF 문구 불일치: {suffix}"
            )

    required_existing = set()
    for ids in REUSE.values():
        required_existing.update(ids)

    required_policies = {
        policy_id(suffix)
        for suffix in list(REUSE) + list(NEW_QUOTES)
    }

    print("=== WEST RECOVERY ===")
    print("PDF SHA256:", pdf_sha)
    print("SOURCE PERIOD: 2026_H1")
    print("NEW SOURCE QUOTES VERIFIED:", len(NEW_QUOTES))

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL 없음")

    # 아래 모든 DB 작업은 단일 트랜잭션으로 처리
    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            policies = conn.execute(
                """
                SELECT
                    policy_id,
                    review_status,
                    legal_validation_approved,
                    approved_for_eligibility_decision,
                    approved_for_embedding,
                    approved_for_user_answers,
                    source_evidence_ids
                FROM policy_candidates
                WHERE program_id = %s
                  AND cardinality(source_evidence_ids) = 0
                FOR UPDATE
                """,
                (PROGRAM_ID,),
            ).fetchall()

            found_ids = {row[0] for row in policies}

            if found_ids != required_policies:
                raise RuntimeError(
                    "WEST 미연결 정책 ID가 예상과 다름: "
                    + str(sorted(found_ids ^ required_policies))
                )

            for row in policies:
                if row[1] != "needs_review":
                    raise RuntimeError(
                        f"검토 상태 확인 필요: {row[0]}"
                    )

                if any(row[2:6]):
                    raise RuntimeError(
                        f"이미 승인된 정책 발견: {row[0]}"
                    )

            existing = conn.execute(
                """
                SELECT
                    evidence_id,
                    program_id,
                    country,
                    source_url,
                    source_file,
                    exact_quote,
                    review_status
                FROM evidence
                WHERE evidence_id = ANY(%s)
                """,
                (sorted(required_existing),),
            ).fetchall()

            if len(existing) != len(required_existing):
                raise RuntimeError(
                    "재사용 Evidence 중 누락된 ID 존재"
                )

            evidence_country = None

            for eid, prog, country, url, file, quote, status in existing:
                if prog != PROGRAM_ID:
                    raise RuntimeError(
                        f"Evidence 프로그램 불일치: {eid}"
                    )

                if url != SOURCE_URL or file != SOURCE_FILE:
                    raise RuntimeError(
                        f"Evidence 출처 불일치: {eid}"
                    )

                if status != "needs_review":
                    raise RuntimeError(
                        f"Evidence 검토 상태 불일치: {eid}"
                    )

                for term in REUSE_QUOTE_CHECKS[eid]:
                    if compact(term) not in compact(quote):
                        raise RuntimeError(
                            f"기존 원문 직접 확인 실패: {eid}, {term}"
                        )

                if evidence_country is None:
                    evidence_country = country
                elif evidence_country != country:
                    raise RuntimeError(
                        "기존 Evidence 국가 코드 불일치"
                    )

            new_ids = [
                evidence_id(suffix)
                for suffix in NEW_QUOTES
            ]

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
                    f"신규 Evidence ID 충돌: {duplicates}"
                )

            print("UNLINKED POLICIES:", len(policies))
            print("REUSABLE EVIDENCE:", len(existing))
            print("NEW EVIDENCE:", len(NEW_QUOTES))
            print("PRECHECK: PASS")

            # 4건 신규 Evidence 삽입
            for suffix, quote in NEW_QUOTES.items():
                pid = policy_id(suffix)
                eid = evidence_id(suffix)

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
                        eid,
                        PROGRAM_ID,
                        evidence_country,
                        eid,
                        "NIIED-WEST-2026H1",
                        SOURCE_URL,
                        SOURCE_FILE,
                        pdf_sha,
                        quote,
                        "physical_pdf_page=0; "
                        f"search_phrase={quote}",
                        "needs_review",
                        Jsonb({
                            "source_period": "2026_H1",
                            "historical_notice": True,
                            "source_policy_id": pid,
                            "original_pdf_sha256": pdf_sha,
                            "quote_normalization": "whitespace_removed_for_verification",
                            "source_verification": "local_pdf_text_match",
                            "legal_validation_status": "needs_review",
                            "current_policy_verified": False,
                            "approved_for_user_answers": False,
                        }),
                    ),
                )

            # 기존 7건 + 신규 4건 정책 연결
            mappings = dict(REUSE)

            for suffix in NEW_QUOTES:
                mappings[suffix] = [evidence_id(suffix)]

            for suffix, ids in mappings.items():
                result = conn.execute(
                    """
                    UPDATE policy_candidates
                    SET
                        source_evidence_ids = %s,
                        metadata =
                            COALESCE(metadata, '{}'::jsonb)
                            || %s::jsonb
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
                        ids,
                        Jsonb({
                            "source_period": "2026_H1",
                            "historical_notice": True,
                            "current_policy_verified": False,
                        }),
                        policy_id(suffix),
                        PROGRAM_ID,
                    ),
                )

                if result.rowcount != 1:
                    raise RuntimeError(
                        f"정책 연결 실패: {suffix}"
                    )

            # 사후 검증: WEST 미연결 정책
            remaining = conn.execute(
                """
                SELECT COUNT(*)
                FROM policy_candidates
                WHERE program_id = %s
                  AND cardinality(source_evidence_ids) = 0
                """,
                (PROGRAM_ID,),
            ).fetchone()[0]

            if remaining != 0:
                raise RuntimeError(
                    f"WEST 미연결 정책 잔여: {remaining}"
                )

            # 사후 검증: 연결된 Evidence 실제 존재 여부
            missing_refs = conn.execute(
                """
                SELECT COUNT(*)
                FROM policy_candidates pc
                CROSS JOIN LATERAL
                    unnest(pc.source_evidence_ids) AS eid
                LEFT JOIN evidence e
                    ON e.evidence_id = eid
                   AND e.program_id = pc.program_id
                WHERE pc.program_id = %s
                  AND e.evidence_id IS NULL
                """,
                (PROGRAM_ID,),
            ).fetchone()[0]

            if missing_refs != 0:
                raise RuntimeError(
                    f"존재하지 않는 Evidence 연결: {missing_refs}"
                )

            # 사후 검증: 회차 및 승인 상태
            status = conn.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (
                        WHERE cardinality(source_evidence_ids) = 0
                    ),
                    COUNT(*) FILTER (
                        WHERE legal_validation_approved
                           OR approved_for_eligibility_decision
                           OR approved_for_embedding
                           OR approved_for_user_answers
                    )
                FROM policy_candidates
                WHERE program_id = %s
                """,
                (PROGRAM_ID,),
            ).fetchone()

            if status[1] != 0 or status[2] != 0:
                raise RuntimeError(
                    f"정책 사후 검증 실패: {status}"
                )

            print("=== WEST RECOVERY RESULT ===")
            print("INSERTED EVIDENCE:", len(NEW_QUOTES))
            print("LINKED POLICIES:", len(mappings))
            print("WEST TOTAL POLICIES:", status[0])
            print("WEST UNLINKED:", status[1])
            print("INVALID EVIDENCE REFS:", missing_refs)
            print("APPROVED POLICIES:", status[2])
            print("POSTCHECK: PASS")

    print("TRANSACTION: COMMITTED")


if __name__ == "__main__":
    main()