"""
app/retrieval/ranking.py

Retrieval 결과의 Ranking / Re-ranking 로직.
초기에는 Vector Similarity Score 기준으로 정렬하고,
Metadata 일치 보너스를 부여하는 방식을 사용합니다.
"""
from __future__ import annotations

from typing import Any


_SOURCE_TYPE_PRIORITY = {
    "law": 5,
    "embassy_notice": 4,
    "administrative_guidance": 3,
    "program_notice": 3,
    "official_guide": 2,
    "faq": 1,
    "education_information": 1,
}


def rank(
    results: list[dict[str, Any]],
    filters: dict[str, Any],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    검색 결과에 보너스 점수를 부여하고 상위 top_k 개를 반환합니다.

    보너스 기준:
    - Metadata 필드 일치 (destination_country, program_id 등)
    - source_type 우선순위 (law > embassy_notice > ...)

    Args:
        results: retriever 에서 반환된 chunk dict 리스트
        filters: build_filters() 에서 생성된 필터 조건
        top_k: 반환할 최대 개수

    Returns:
        최종 점수로 정렬된 상위 결과
    """
    ranked = []

    for doc in results:
        base_score: float = doc.get("score", 0.0)
        bonus: float = 0.0

        # Metadata 필드 일치 보너스
        for key, val in filters.items():
            doc_val = doc.get(key)
            if doc_val and doc_val == val:
                bonus += 0.05

        # source_type 우선순위 보너스
        st = doc.get("source_type") or ""
        bonus += _SOURCE_TYPE_PRIORITY.get(st, 0) * 0.01

        ranked.append({**doc, "final_score": base_score + bonus})

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked[:top_k]
