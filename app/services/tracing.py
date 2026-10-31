"""Langfuse 트레이싱.

LANGFUSE_PUBLIC_KEY와 LANGFUSE_SECRET_KEY가 모두 있을 때만 켜진다. 없으면 일반 OpenAI 클라이언트와
빈 설정을 돌려주고 함수를 감싸지 않으므로 동작이 바뀌지 않는다. 키는 프로세스 시작 시점의 환경변수로 판단한다.

상담 한 턴 = trace 하나:
  handle-consult-turn (agent)          ← 사용자 메시지 / 최종 답변, session_id·user_id·tags
    run-consult-graph → LangGraph 노드  ← CallbackHandler (chain)
      retrieve-*-evidence (retriever)  ← 하이브리드 검색: 질의, 결과 청크와 순위
      OpenAI 호출 (generation)          ← langfuse.openai: 모델, 토큰, 입출력
"""
from __future__ import annotations

import functools
import inspect
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

ENABLED = bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))

# 매 턴 DB에서 다시 읽는 참조용 카탈로그. 판단 근거가 아니면서 노드 입출력마다 100KB 넘게 반복되므로 개수만 남긴다.
_CATALOG_KEYS = ("catalog_programs", "catalog_supports")
# 조건부 엣지 함수(app.agent.router.route). 그래프 전체 상태를 입력으로 받는 프레임워크 내부 단계라 내보내지 않는다.
_EDGE_SPAN_NAMES = {"route"}
_RETRIEVAL_FIELDS = ("chunk_id", "program_id", "program_ids", "title", "vector_rank", "keyword_rank", "rrf_score")


def _mask(*, data: Any) -> Any:
    if isinstance(data, dict) and any(isinstance(data.get(key), list) for key in _CATALOG_KEYS):
        return {**data, **{key: f"<{len(data[key])}개 생략>" for key in _CATALOG_KEYS if isinstance(data.get(key), list)}}
    return data


if ENABLED:
    from langfuse import Langfuse
    from langfuse.span_filter import is_default_export_span

    # langfuse.openai보다 먼저 클라이언트를 만들어야 아래 설정이 OpenAI generation에도 적용된다.
    Langfuse(mask=_mask, should_export_span=lambda span: span.name not in _EDGE_SPAN_NAMES and is_default_export_span(span))
    from langfuse.openai import OpenAI
else:
    from openai import OpenAI

__all__ = ["ENABLED", "OpenAI", "consult_turn", "generation_name", "retriever"]


def generation_name(name: str) -> dict[str, str]:
    """OpenAI 호출 kwargs. langfuse.openai만 name을 받으므로 꺼져 있으면 아무것도 넘기지 않는다."""
    return {"name": name} if ENABLED else {}


def retriever(name: str, input_keys: tuple[str, ...]) -> Callable[[Callable[..., list[dict]]], Callable[..., list[dict]]]:
    """검색 함수를 retriever observation으로 기록한다.

    입력은 input_keys에 해당하는 인자만, 출력은 청크 식별자와 순위만 남긴다(본문은 답변 generation 입력에 있다).
    """
    def wrap(fn: Callable[..., list[dict]]) -> Callable[..., list[dict]]:
        if not ENABLED:
            return fn
        from langfuse import get_client

        signature = inspect.signature(fn)

        @functools.wraps(fn)
        def run(*args: Any, **kwargs: Any) -> list[dict]:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            query = {key: bound.arguments[key] for key in input_keys}
            with get_client().start_as_current_observation(as_type="retriever", name=name, input=query) as observation:
                rows = fn(*args, **kwargs)
                observation.update(output=[{key: row[key] for key in _RETRIEVAL_FIELDS if key in row} for row in rows])
                return rows
        return run
    return wrap


@contextmanager
def consult_turn(
    *, session_id: str, owner: str, query: str, kind: str,
) -> Iterator[tuple[dict[str, Any], Callable[[str], None]]]:
    """상담 한 턴을 trace 하나로 묶는다.

    graph.invoke에 넘길 kwargs와, 최종 답변을 trace 출력으로 기록하는 함수를 돌려준다.
    Cloud Run은 요청이 끝나면 CPU를 거의 주지 않아 백그라운드 전송이 밀리므로 턴마다 flush한다.
    """
    if not ENABLED:
        yield {}, lambda reply: None
        return

    from langfuse import get_client, propagate_attributes
    from langfuse.langchain import CallbackHandler
    from opentelemetry import context as otel_context

    langfuse = get_client()
    # FastAPI가 만드는 HTTP span(내보내지 않음) 아래에 붙지 않도록 빈 컨텍스트에서 새 trace로 시작한다.
    detached = otel_context.attach(otel_context.Context())
    try:
        with langfuse.start_as_current_observation(as_type="agent", name="handle-consult-turn", input=query) as root, \
                propagate_attributes(trace_name="handle-consult-turn", session_id=session_id,
                                     user_id=owner or None, tags=["consult", kind]):
            yield {"config": {"callbacks": [CallbackHandler()], "run_name": "run-consult-graph"}}, \
                lambda reply: root.update(output=reply)
    finally:
        otel_context.detach(detached)
        langfuse.flush()
