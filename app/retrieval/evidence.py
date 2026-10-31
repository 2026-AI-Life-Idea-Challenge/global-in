"""
app/retrieval/evidence.py

Retrieval Result 를 Validated Evidence 로 변환·검증하는 공통 기능.

Retrieval 결과가 바로 Evidence 가 되는 것은 아닙니다.
- 질문 관련성
- 국가 일치
- Program / SupportProgram 일치
- 공식 출처 여부
- 적용 시점
등을 확인합니다.
"""
from __future__ import annotations

from datetime import date
from typing import Any


_OFFICIAL_SOURCE_TYPES = {
    "law",
    "administrative_guidance",
    "program_notice",
    "official_guide",
    "faq",
    "embassy_notice",
    "education_information",
}


def validate_evidence(
    doc: dict[str, Any],
    filters: dict[str, Any],
    as_of: str | None = None,
) -> dict[str, Any]:
    """
    단일 Retrieval Result 를 검증하고 ValidatedEvidence 형식으로 반환합니다.

    Args:
        doc: retriever 반환 chunk dict
        filters: 검색 시 사용한 Metadata 필터
        as_of: 자격 기준일 (YYYY-MM-DD). 없으면 오늘 날짜 사용.

    Returns:
        {is_valid: bool, validation_notes: str, ...doc fields}
    """
    today = as_of or date.today().isoformat()
    notes: list[str] = []
    is_valid = True

    # 1. 공식 출처 여부
    source_type = doc.get("source_type") or ""
    if source_type and source_type not in _OFFICIAL_SOURCE_TYPES:
        notes.append(f"비공식 출처 유형: {source_type}")
        is_valid = False

    # 2. 국가 일치 확인
    dest = filters.get("destination_country")
    if dest and doc.get("destination_country") and doc["destination_country"] != dest:
        notes.append(f"국가 불일치: 필요={dest}, 문서={doc['destination_country']}")
        is_valid = False

    # 3. Program 일치 확인
    prog = filters.get("program_id")
    if prog and doc.get("program_id") and doc["program_id"] != prog:
        notes.append(f"Program 불일치: 필요={prog}, 문서={doc['program_id']}")
        is_valid = False

    # 4. 적용 종료일 확인 (effective_until 이 과거면 경고)
    eff_until = doc.get("effective_until")
    if eff_until:
        try:
            if date.fromisoformat(eff_until) < date.fromisoformat(today):
                notes.append(f"적용 기간 만료: {eff_until}")
                is_valid = False
        except ValueError:
            pass

    # 5. verified_at 없으면 경고 (무효는 아님)
    if not doc.get("verified_at"):
        notes.append("Global-In 확인일 정보 없음")

    return {
        **doc,
        "is_valid": is_valid,
        "validation_notes": "; ".join(notes) if notes else "검증 통과",
    }


def validate_all(
    docs: list[dict[str, Any]],
    filters: dict[str, Any],
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    """
    여러 Retrieval Result 를 일괄 검증합니다.
    is_valid=True 인 것만 반환하며, 없으면 빈 리스트를 반환합니다.
    """
    validated = [validate_evidence(d, filters, as_of) for d in docs]
    return [v for v in validated if v["is_valid"]]
