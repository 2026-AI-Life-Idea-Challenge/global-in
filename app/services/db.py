"""
app/services/db.py

PostgreSQL 연결 서비스.
에이전트와 Retrieval 에서 직접 psycopg 를 반복 작성하지 않도록
공통 연결 헬퍼를 제공합니다.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return url


@contextmanager
def get_conn() -> Generator[psycopg.Connection, None, None]:
    """
    dict_row 팩토리를 적용한 동기 커넥션 컨텍스트 매니저.

    사용 예:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM programs").fetchall()
    """
    with psycopg.connect(_database_url(), row_factory=dict_row) as conn:
        yield conn


def query(sql: str, params: tuple | list | None = None) -> list[dict[str, Any]]:
    """단순 SELECT 쿼리를 실행하고 결과를 반환합니다."""
    with get_conn() as conn:
        return conn.execute(sql, params or ()).fetchall()


def query_one(
    sql: str,
    params: tuple | list | None = None,
) -> dict[str, Any] | None:
    """단일 행 SELECT. 없으면 None 반환."""
    with get_conn() as conn:
        return conn.execute(sql, params or ()).fetchone()


def execute(sql: str, params: tuple | list | None = None) -> None:
    """INSERT / UPDATE / DELETE 실행. 결과 반환 없음."""
    with get_conn() as conn:
        conn.execute(sql, params or ())
        conn.commit()
