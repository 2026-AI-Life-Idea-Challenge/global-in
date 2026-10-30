"""
app/retrieval/filters.py

pgvector 검색 전 Metadata Filtering 조건 생성.
Vector Similarity 검색 전 범위를 좁혀 다른 국가·프로그램 혼입을 최소화합니다.
"""
from __future__ import annotations

from typing import Any


def build_filters(
    destination_country: str | None = None,
    issuer_country: str | None = None,
    program_id: str | None = None,
    support_program_id: str | None = None,
    purpose: str | None = None,
    target_nationality: str | None = None,
    information_topic: str | None = None,
    source_type: str | None = None,
) -> dict[str, Any]:
    """
    검색 조건 딕셔너리를 생성합니다.
    None 인 필드는 제외 (필터링하지 않음).
    """
    filters: dict[str, Any] = {}

    if destination_country:
        filters["destination_country"] = destination_country
    if issuer_country:
        filters["issuer_country"] = issuer_country
    if program_id:
        filters["program_id"] = program_id
    if support_program_id:
        filters["support_program_id"] = support_program_id
    if purpose:
        filters["purpose"] = purpose
    if target_nationality:
        filters["target_nationality"] = target_nationality
    if information_topic:
        filters["information_topic"] = information_topic
    if source_type:
        filters["source_type"] = source_type

    return filters


def filters_to_sql_where(
    filters: dict[str, Any],
    table_alias: str = "c",
) -> tuple[str, list[Any]]:
    """
    filters 딕셔너리를 SQL WHERE 절 문자열과 파라미터 리스트로 변환합니다.

    Args:
        filters: build_filters() 반환값
        table_alias: 테이블 별칭 (기본: "c")

    Returns:
        (where_clause, params)
        where_clause 예: "AND c.destination_country = %s AND c.purpose = %s"
    """
    clauses: list[str] = []
    params: list[Any] = []

    for col, val in filters.items():
        if isinstance(val, list):
            placeholders = ", ".join(["%s"] * len(val))
            clauses.append(f"{table_alias}.{col} = ANY(ARRAY[{placeholders}])")
            params.extend(val)
        else:
            clauses.append(f"{table_alias}.{col} = %s")
            params.append(val)

    where = (" AND " + " AND ".join(clauses)) if clauses else ""
    return where, params
