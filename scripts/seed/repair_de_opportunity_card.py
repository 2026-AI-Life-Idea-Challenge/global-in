
import hashlib
import json
import os
import re
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
RAW_REL = (
    "data/raw/germany/employment/"
    "opportunity_card_make_it_in_germany_en.txt"
)
JSON_REL = (
    "data/processed/germany/employment/"
    "opportunity_card_evidence_draft.json"
)

PROGRAM = "DE:opportunity_card"

PATHWAYS = {
    "DE_OPP_POL_01": {
        "pathway": "recognised_skilled_worker",
        "topic": "eligibility_recognised_skilled_worker",
        "evidence_id": "DE_OPP_OFFICIAL_PATHWAY_01",
        "lines": [(39, 47)],
        "required": [
            "fully recognised in Germany",
            "points system",
            "language skills",
        ],
        "policy_text": (
            "Opportunity Card, recognised skilled worker pathway: "
            "Applicants with a German vocational or academic "
            "qualification, or a foreign vocational or academic "
            "qualification fully recognised in Germany, can use "
            "this pathway without the points system. "
            "Proof of language skills is not required for this "
            "pathway. Sufficient financial resources remain "
            "a separate common requirement."
        ),
    },
    "DE_OPP_POL_02": {
        "pathway": "points_system",
        "topic": "eligibility_points_system",
        "evidence_id": "DE_OPP_OFFICIAL_PATHWAY_02",
        "lines": [(31, 36), (52, 66)],
        "required": [
            "six points",
            "recognised",
            "vocational",
        ],
        "policy_text": (
            "Opportunity Card, points-system pathway: "
            "Applicants without a German qualification or "
            "qualification fully recognised in Germany must "
            "meet the relevant foreign qualification and "
            "language prerequisites and obtain at least "
            "six points under the points system. "
            "Sufficient financial resources are also required. "
            "Detailed qualification, language, and points "
            "criteria require separate validation before "
            "any eligibility decision."
        ),
    },
}


def compact(value):
    return re.sub(r"\s+", "", value or "").casefold()


def get_source_url(data):
    # 기존 JSON에 기록된 공식 출처만 사용한다.
    serialized = json.dumps(data, ensure_ascii=False)
    urls = re.findall(
        r"https?://[^\s\"<>]+",
        serialized,
    )

    matches = [
        url.rstrip("),.;")
        for url in urls
        if "make-it-in-germany.com/" in url.lower()
    ]

    if not matches:
        raise RuntimeError(
            "가공 JSON에서 Make it in Germany 공식 URL을 찾지 못함"
        )

    # Opportunity Card를 직접 다루는 출처 우선
    relevant = [
        url for url in matches
        if "opportunity-card" in url.lower()
    ]

    return relevant[0] if relevant else matches[0]


def quote_from_ranges(lines, ranges):
    chunks = []

    for start, end in ranges:
        if start < 1 or end > len(lines):
            raise RuntimeError(
                f"원본 줄 범위 오류: {start}-{end}"
            )

        chunks.append(
            "\n".join(lines[start - 1:end])
        )

    return "\n\n".join(chunks)


def main():
    load_dotenv(ROOT / ".env")

    raw_path = ROOT / RAW_REL
    json_path = ROOT / JSON_REL

    raw_bytes = raw_path.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    lines = raw_bytes.decode("utf-8-sig").splitlines()

    data = json.loads(
        json_path.read_text(encoding="utf-8-sig")
    )

    source_url = get_source_url(data)

    if data.get("program") != "opportunity_card":
        raise RuntimeError(
            f"원본 JSON 프로그램 값 불일치: {data.get('program')}"
    )

    pathway_by_policy = {
        entry["policy_candidate_id"]: entry
        for entry in data["eligibility_pathways"]
    }

    prepared = {}

    for pid, spec in PATHWAYS.items():
        pathway = pathway_by_policy.get(pid)

        if not pathway:
            raise RuntimeError(
                f"원본 JSON 경로 누락: {pid}"
            )

        if pathway.get("pathway_id") != spec["pathway"]:
            raise RuntimeError(
                f"신청 경로 불일치: {pid}"
            )

        if pathway.get("eligibility_rule") is not None:
            raise RuntimeError(
                f"원본 JSON 규칙 상태 변경됨: {pid}"
            )

        quote = quote_from_ranges(
            lines, spec["lines"]
        )

        for term in spec["required"]:
            if compact(term) not in compact(quote):
                raise RuntimeError(
                    f"{pid}: 공식 원문 검증 실패: {term}"
                )

        prepared[pid] = {
            **spec,
            "quote": quote,
        }

    # 두 경로에 공통으로 적용되는 재정 요건 확인
    full_text = "\n".join(lines)

    if not all(
        compact(term) in compact(full_text)
        for term in [
            "financial resources",
            "2026",
            "€1,091",
        ]
    ):
        raise RuntimeError(
            "공통 재정 요건 원문 검증 실패"
        )

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL 없음")

    with psycopg.connect(db_url) as conn:
        with conn.transaction():
            rows = conn.execute(
                """
                SELECT
                    policy_id, policy_text, topic,
                    metadata, review_status,
                    legal_validation_approved,
                    approved_for_eligibility_decision,
                    approved_for_embedding,
                    approved_for_user_answers
                FROM policy_candidates
                WHERE program_id = %s
                  AND cardinality(source_evidence_ids) = 0
                FOR UPDATE
                """,
                (PROGRAM,),
            ).fetchall()

            if {r[0] for r in rows} != set(PATHWAYS):
                raise RuntimeError(
                    "독일 미연결 정책 목록 불일치"
                )

            for row in rows:
                pid = row[0]
                metadata = row[3] or {}
                original = metadata.get("original_policy") or {}

                if row[1] is not None or row[2] is not None:
                    raise RuntimeError(
                        f"정책이 이미 수정됨: {pid}"
                    )

                if original.get("pathway_id") != PATHWAYS[pid]["pathway"]:
                    raise RuntimeError(
                        f"원본 신청 경로 불일치: {pid}"
                    )

                if row[4] != "needs_review" or any(row[5:9]):
                    raise RuntimeError(
                        f"검토·승인 상태 불일치: {pid}"
                    )

            new_ids = [
                p["evidence_id"]
                for p in prepared.values()
            ]

            collisions = conn.execute(
                """
                SELECT evidence_id FROM evidence
                WHERE evidence_id = ANY(%s)
                """,
                (new_ids,),
            ).fetchall()

            if collisions:
                raise RuntimeError(
                    f"Evidence ID 충돌: {collisions}"
                )

            print("=== GERMANY OPPORTUNITY PRECHECK ===")
            print("TARGET POLICIES:", len(rows))
            print("OFFICIAL_SOURCE:", source_url)
            print("SOURCE_SHA256:", raw_sha)
            print("SOURCE_LINES:", len(lines))
            print("PATHWAY_QUOTES_VERIFIED:", len(prepared))
            print("PRECHECK: PASS")

            for pid, spec in prepared.items():
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
                        spec["evidence_id"],
                        PROGRAM,
                        "germany",
                        spec["evidence_id"],
                        "DE-OPPORTUNITY-CARD-MIG",
                        source_url,
                        RAW_REL,
                        raw_sha,
                        spec["quote"],
                        "lines: " + ", ".join(
                            f"{a}-{b}"
                            for a, b in spec["lines"]
                        ),
                        "needs_review",
                        Jsonb({
                            "pathway_id": spec["pathway"],
                            "source_policy_id": pid,
                            "source_kind": "official_local_snapshot",
                            "current_legal_status_verified": False,
                            "legal_validation_status": "needs_review",
                            "eligibility_decision_approved": False,
                            "source_snapshot_sha256": raw_sha,
                            "financial_reference_year": 2026,
                        }),
                    ),
                )

                result = conn.execute(
                    """
                    UPDATE policy_candidates
                    SET
                        topic = %s,
                        policy_text = %s,
                        source_evidence_ids = ARRAY[%s]::text[],
                        metadata =
                            COALESCE(metadata, '{}'::jsonb)
                            || %s::jsonb
                    WHERE policy_id = %s
                      AND program_id = %s
                      AND policy_text IS NULL
                      AND topic IS NULL
                      AND cardinality(source_evidence_ids) = 0
                      AND review_status = 'needs_review'
                      AND NOT legal_validation_approved
                      AND NOT approved_for_eligibility_decision
                      AND NOT approved_for_embedding
                      AND NOT approved_for_user_answers
                    """,
                    (
                        spec["topic"],
                        spec["policy_text"],
                        spec["evidence_id"],
                        Jsonb({
                            "recovery_status": "draft_recovered",
                            "pathway_id": spec["pathway"],
                            "eligibility_rule_review_required": True,
                            "current_legal_status_verified": False,
                            "source_snapshot_sha256": raw_sha,
                        }),
                        pid,
                        PROGRAM,
                    ),
                )

                if result.rowcount != 1:
                    raise RuntimeError(
                        f"독일 정책 복구 실패: {pid}"
                    )

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

            invalid = conn.execute(
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

            unapproved = conn.execute(
                """
                SELECT COUNT(*)
                FROM policy_candidates
                WHERE policy_id = ANY(%s)
                  AND review_status = 'needs_review'
                  AND NOT legal_validation_approved
                  AND NOT approved_for_eligibility_decision
                  AND NOT approved_for_embedding
                  AND NOT approved_for_user_answers
                """,
                (list(PATHWAYS),),
            ).fetchone()[0]

            if totals[2] != 0 or invalid != 0 or unapproved != 2:
                raise RuntimeError(
                    "최종 검증 실패: "
                    f"totals={totals}, invalid={invalid}, "
                    f"unapproved={unapproved}"
                )

            print("=== GERMANY RECOVERY RESULT ===")
            print("CREATED EVIDENCE:", len(prepared))
            print("RECOVERED POLICIES:", len(prepared))
            print("REVIEW_PENDING POLICIES:", unapproved)

            print("=== GLOBAL DATABASE CHECK ===")
            print("TOTAL EVIDENCE:", totals[0])
            print("TOTAL POLICIES:", totals[1])
            print("UNLINKED POLICIES:", totals[2])
            print("INVALID EVIDENCE REFERENCES:", invalid)
            print("POSTCHECK: PASS")

    print("TRANSACTION: COMMITTED")


if __name__ == "__main__":
    main()