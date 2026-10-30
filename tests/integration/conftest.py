"""
tests/integration/conftest.py

에이전트 통합 테스트 공통 설정.
외부 의존성(DB, LLM API, pgvector)을 sys.modules 스텁으로 차단합니다.
"""
from __future__ import annotations

import sys
import types


def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


# ── anthropic ──────────────────────────────────────────────────────────────
_anthropic = _make_stub("anthropic")
_anthropic.Anthropic = object  # type: ignore[attr-defined]

# ── psycopg ────────────────────────────────────────────────────────────────
_psycopg = _make_stub("psycopg")
_psycopg_rows = _make_stub("psycopg.rows")

# ── pgvector ──────────────────────────────────────────────────────────────
_pgvector = _make_stub("pgvector")
_pgvector_psycopg = _make_stub("pgvector.psycopg")

# ── langgraph ─────────────────────────────────────────────────────────────
_lg = _make_stub("langgraph")
_lg_graph = _make_stub("langgraph.graph")
_lg_graph.StateGraph = object  # type: ignore[attr-defined]
_lg_graph.END = "END"  # type: ignore[attr-defined]
