"""
app/services/llm.py

LLM 클라이언트 서비스 (Anthropic Claude).
모든 에이전트가 이 모듈을 통해 LLM 을 호출합니다.
"""
from __future__ import annotations

import os
from typing import Any

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# 기본 모델 (환경 변수로 재정의 가능)
_DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")


def chat(
    messages: list[dict[str, str]],
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> str:
    """
    단순 Chat 완성 요청.

    Args:
        messages: [{"role": "user"|"assistant", "content": "..."}] 형식
        system: 시스템 프롬프트 (선택)
        model: 사용할 모델 ID (없으면 기본값 사용)
        max_tokens: 최대 생성 토큰 수
        temperature: 샘플링 온도

    Returns:
        모델의 텍스트 응답 (str)
    """
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": model or _DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    return response.content[0].text


def extract_json(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """
    JSON 추출에 특화된 호출.
    응답이 JSON 블록만 포함하도록 시스템 프롬프트를 보강합니다.
    """
    json_system = (
        (system + "\n\n" if system else "")
        + "반드시 유효한 JSON 만 출력하세요. "
          "코드 블록(```), 설명 텍스트 없이 JSON 객체 또는 배열만 반환합니다."
    )
    raw = chat(
        messages=[{"role": "user", "content": prompt}],
        system=json_system,
        model=model,
        max_tokens=max_tokens,
        temperature=0.0,
    )
    # 마크다운 코드 블록 제거 (모델이 무시할 경우 대비)
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return raw.strip()
