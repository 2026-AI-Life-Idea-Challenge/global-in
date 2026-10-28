"""
app/agent/eligibility/policy_fetcher.py

프로그램 · 정책 · 근거 조회 레이어
A 에이전트에서 사용자에게 프로그램 정보, 관련 정책(knowledge_documents),
근거(evidence)를 제공하기 위한 DB 조회 함수 모음.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import psycopg2
import psycopg2.extras

from app.agent.eligibility.fetcher import _get_conn


# ── 결과 타입 ──────────────────────────────────────────────────────────────────

@dataclass
class ProgramInfo:
    program_id: str
    country: str
    name: str
    category: str | None
    route_id: str | None
    visa_subclass: str | None
    stream: str | None
    review_status: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SupportProgramInfo:
    support_program_id: str
    country: str
    name: str
    provider: str | None
    review_status: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeDocument:
    document_id: str
    revision_id: str
    knowledge_kind: str
    title: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceRecord:
    evidence_id: str
    program_id: str
    country: str
    source_url: str | None
    exact_quote: str | None
    source_location: str | None
    review_status: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyCandidate:
    policy_id: str
    program_id: str
    country: str
    topic: str | None
    policy_text: str | None
    approved_for_eligibility_decision: bool
    approved_for_user_answers: bool
    source_evidence_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreparationItem:
    item_id: str
    target_type: str
    target_id: str
    stage: str
    item_kind: str
    definition: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgramSupportLink:
    program_id: str
    support_program_id: str
    relationship: str
    eligibility_implied: bool
    conditions: dict[str, Any] = field(default_factory=dict)
    source_urls: Any = None


# ── 프로그램 조회 ──────────────────────────────────────────────────────────────

def fetch_program(
    conn_or_url: psycopg2.extensions.connection | str,
    program_id: str,
) -> ProgramInfo | None:
    """program_id로 프로그램 기본 정보 조회."""
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT program_id, country, name, category, route_id,
                       visa_subclass, stream, review_status, metadata
                FROM programs
                WHERE program_id = %s
                """,
                (program_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return ProgramInfo(**dict(row))
    finally:
        if _close:
            _conn.close()


def fetch_programs_by_country(
    conn_or_url: psycopg2.extensions.connection | str,
    country: str,
) -> list[ProgramInfo]:
    """국가별 프로그램 목록 조회."""
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT program_id, country, name, category, route_id,
                       visa_subclass, stream, review_status, metadata
                FROM programs
                WHERE country = %s
                ORDER BY program_id
                """,
                (country,),
            )
            rows = cur.fetchall()
        return [ProgramInfo(**dict(r)) for r in rows]
    finally:
        if _close:
            _conn.close()


def fetch_support_program(
    conn_or_url: psycopg2.extensions.connection | str,
    support_program_id: str,
) -> SupportProgramInfo | None:
    """support_program_id로 지원 프로그램 기본 정보 조회."""
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT support_program_id, country, name, provider,
                       review_status, metadata
                FROM support_programs
                WHERE support_program_id = %s
                """,
                (support_program_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return SupportProgramInfo(**dict(row))
    finally:
        if _close:
            _conn.close()


# ── 지식 문서 조회 ─────────────────────────────────────────────────────────────

def fetch_knowledge_documents(
    conn_or_url: psycopg2.extensions.connection | str,
    target_type: str,
    target_id: str,
    active_only: bool = True,
) -> list[KnowledgeDocument]:
    """
    target_type + target_id에 연결된 knowledge_documents 조회.
    knowledge_document_targets를 통해 JOIN.
    """
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            active_filter = "AND kd.active = TRUE" if active_only else ""
            cur.execute(
                f"""
                SELECT kd.document_id, kd.revision_id, kd.knowledge_kind,
                       kd.title, kd.body, kd.metadata
                FROM knowledge_documents kd
                JOIN knowledge_document_targets kdt
                  ON kd.document_id = kdt.document_id
                 AND kd.revision_id = kdt.revision_id
                WHERE kdt.target_type = %s
                  AND kdt.target_id = %s
                  {active_filter}
                ORDER BY kd.document_id
                """,
                (target_type, target_id),
            )
            rows = cur.fetchall()
        return [KnowledgeDocument(**dict(r)) for r in rows]
    finally:
        if _close:
            _conn.close()


# ── 근거(Evidence) 조회 ────────────────────────────────────────────────────────

def fetch_evidence(
    conn_or_url: psycopg2.extensions.connection | str,
    program_id: str,
) -> list[EvidenceRecord]:
    """program_id에 연결된 근거(evidence) 목록 조회."""
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT evidence_id, program_id, country,
                       source_url, exact_quote, source_location,
                       review_status, metadata
                FROM evidence
                WHERE program_id = %s
                ORDER BY evidence_id
                """,
                (program_id,),
            )
            rows = cur.fetchall()
        return [EvidenceRecord(**dict(r)) for r in rows]
    finally:
        if _close:
            _conn.close()


# ── 정책 후보(PolicyCandidate) 조회 ───────────────────────────────────────────

def fetch_policy_candidates(
    conn_or_url: psycopg2.extensions.connection | str,
    program_id: str,
    approved_only: bool = False,
) -> list[PolicyCandidate]:
    """
    program_id에 연결된 정책 후보 조회.
    approved_only=True이면 approved_for_eligibility_decision=TRUE 행만 반환.
    """
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            approved_filter = (
                "AND approved_for_eligibility_decision = TRUE" if approved_only else ""
            )
            cur.execute(
                f"""
                SELECT policy_id, program_id, country, topic,
                       policy_text, approved_for_eligibility_decision,
                       approved_for_user_answers, source_evidence_ids, metadata
                FROM policy_candidates
                WHERE program_id = %s
                {approved_filter}
                ORDER BY policy_id
                """,
                (program_id,),
            )
            rows = cur.fetchall()
        return [PolicyCandidate(**dict(r)) for r in rows]
    finally:
        if _close:
            _conn.close()


# ── 준비사항(PreparationItem) 조회 ────────────────────────────────────────────

def fetch_preparation_items(
    conn_or_url: psycopg2.extensions.connection | str,
    target_type: str,
    target_id: str,
    stage: str | None = None,
) -> list[PreparationItem]:
    """
    target_type + target_id에 연결된 준비사항 조회.
    stage 파라미터로 필터링 가능 (예: 'before_apply', 'after_apply').
    """
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            stage_filter = "AND stage = %s" if stage else ""
            params = (target_type, target_id) + ((stage,) if stage else ())
            cur.execute(
                f"""
                SELECT item_id, target_type, target_id, stage,
                       item_kind, definition
                FROM preparation_items
                WHERE target_type = %s
                  AND target_id = %s
                  {stage_filter}
                ORDER BY item_id
                """,
                params,
            )
            rows = cur.fetchall()
        return [PreparationItem(**dict(r)) for r in rows]
    finally:
        if _close:
            _conn.close()


# ── 연계 지원 프로그램 조회 ────────────────────────────────────────────────────

def fetch_linked_support_programs(
    conn_or_url: psycopg2.extensions.connection | str,
    program_id: str,
) -> list[ProgramSupportLink]:
    """program_id에 연계된 지원 프로그램 링크 조회."""
    _conn, _close = _get_conn(conn_or_url)
    try:
        with _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT program_id, support_program_id, relationship,
                       eligibility_implied, conditions, source_urls
                FROM program_support_links
                WHERE program_id = %s
                ORDER BY support_program_id
                """,
                (program_id,),
            )
            rows = cur.fetchall()
        return [ProgramSupportLink(**dict(r)) for r in rows]
    finally:
        if _close:
            _conn.close()


# ── 통합 조회 (에이전트 노드용) ────────────────────────────────────────────────

@dataclass
class ProgramContext:
    """
    A 에이전트가 자격 검토 시 필요한 프로그램 전체 컨텍스트.
    한 번의 조회로 프로그램 + 정책 + 근거 + 지식문서를 모두 담음.
    """
    program_info: ProgramInfo | None
    knowledge_documents: list[KnowledgeDocument] = field(default_factory=list)
    approved_policies: list[PolicyCandidate] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    preparation_items: list[PreparationItem] = field(default_factory=list)
    linked_support_programs: list[ProgramSupportLink] = field(default_factory=list)


def fetch_program_context(
    conn_or_url: psycopg2.extensions.connection | str,
    program_id: str,
    target_type: str = "PROGRAM",
) -> ProgramContext:
    """
    A 에이전트 노드에서 호출하는 통합 조회 함수.
    프로그램 + 지식문서 + 정책(approved) + 근거 + 준비사항 + 연계 지원프로그램을 한 번에 반환.

    Parameters
    ----------
    conn_or_url : str | connection
        DB URL 또는 기존 커넥션
    program_id : str
        조회 대상 프로그램 ID (예: "AU:subclass_186_direct_entry")
    target_type : str
        "PROGRAM" | "SUPPORT_PROGRAM"
    """
    _conn, _close = _get_conn(conn_or_url)
    try:
        program_info = fetch_program(_conn, program_id)
        knowledge_docs = fetch_knowledge_documents(_conn, target_type, program_id)
        approved_policies = fetch_policy_candidates(_conn, program_id, approved_only=True)
        evidence = fetch_evidence(_conn, program_id)
        prep_items = fetch_preparation_items(_conn, target_type, program_id)
        linked = fetch_linked_support_programs(_conn, program_id)

        return ProgramContext(
            program_info=program_info,
            knowledge_documents=knowledge_docs,
            approved_policies=approved_policies,
            evidence=evidence,
            preparation_items=prep_items,
            linked_support_programs=linked,
        )
    finally:
        if _close:
            _conn.close()
