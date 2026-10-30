"""
app/agent/eligibility/fetcher.py

DB에서 자격 검토에 필요한 데이터를 조회합니다.
- eligibility_rule_sets  : 프로그램별 룰셋 (coverage_complete 포함)
- eligibility_requirements: 개별 요건 정의 (expression 포함)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import psycopg2
import psycopg2.extras


@dataclass
class RuleSet:
    rule_set_id: str
    target_type: str
    target_id: str
    coverage_complete: bool
    definition: dict[str, Any]
    release_id: str


@dataclass
class RequirementRecord:
    requirement_id: str
    target_type: str
    target_id: str
    judgeability: str          # rule_based | manual_check | conditional
    definition: dict[str, Any] # Full requirement, including expression and source dates.
    release_id: str


def fetch_rule_set(
    conn_or_url: psycopg2.extensions.connection | str,
    target_type: str,
    target_id: str,
) -> RuleSet | None:
    """target_type + target_id로 룰셋 1개 조회."""
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT rule_set_id, target_type, target_id,
                       coverage_complete, definition, release_id
                FROM eligibility_rule_sets
                WHERE target_type = %s AND target_id = %s
                LIMIT 1
                """,
                (target_type, target_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return RuleSet(**dict(row))
    finally:
        if _close:
            _conn.close()


def fetch_requirements(
    conn_or_url: psycopg2.extensions.connection | str,
    target_type: str,
    target_id: str,
) -> list[RequirementRecord]:
    """target_type + target_id에 속하는 모든 요건 조회."""
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT requirement_id, target_type, target_id,
                       judgeability, definition, release_id
                FROM eligibility_requirements
                WHERE target_type = %s AND target_id = %s
                ORDER BY requirement_id
                """,
                (target_type, target_id),
            )
            rows = cur.fetchall()
        return [RequirementRecord(**dict(r)) for r in rows]
    finally:
        if _close:
            _conn.close()


def fetch_requirements_by_ids(
    conn_or_url: psycopg2.extensions.connection | str,
    requirement_ids: list[str],
) -> list[RequirementRecord]:
    """requirement_id 목록으로 요건 조회 (rule_set.definition이 id 목록만 가질 때 사용)."""
    if not requirement_ids:
        return []
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT requirement_id, target_type, target_id,
                       judgeability, definition, release_id
                FROM eligibility_requirements
                WHERE requirement_id = ANY(%s)
                ORDER BY requirement_id
                """,
                (requirement_ids,),
            )
            rows = cur.fetchall()
        return [RequirementRecord(**dict(r)) for r in rows]
    finally:
        if _close:
            _conn.close()


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _get_conn(
    conn_or_url: psycopg2.extensions.connection | str,
) -> tuple[psycopg2.extensions.connection, bool]:
    """(connection, should_close) 반환."""
    if isinstance(conn_or_url, str):
        return psycopg2.connect(conn_or_url), True
    return conn_or_url, False
