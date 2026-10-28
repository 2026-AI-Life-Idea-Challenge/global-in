"""준비 안내 에이전트: A의 검토 결과 + 근거 → 준비 항목(체크리스트)과 안내 문장.

규칙: 근거 없는 항목은 지어내지 않고 '근거 부족'으로 표시한다.
"""

from collections.abc import Callable

from app.models.consult import Citation, EligibilityPayload, PrepItem, ProgramCandidate

# (program_id, requirement_ids) → requirement별 근거
CitationSearch = Callable[[str, list[str]], dict[str, list[Citation]]]


def build_prep_items(
    programs: list[ProgramCandidate],
    results: list[EligibilityPayload],
    search_citations: CitationSearch,
) -> list[PrepItem]:
    by_id = {p.program_id: p for p in programs}
    items: list[PrepItem] = []
    for result in results:
        program = by_id.get(result.program_id)
        citations_by_req = search_citations(result.program_id, result.unknown_requirement_ids)

        for req in result.requirements:
            if req.outcome == "조건 미충족":
                items.append(PrepItem(
                    id=f"{result.program_id}::{req.requirement_id}",
                    program_id=result.program_id,
                    title=f"조건 미충족: {req.requirement_id}",
                    description="이 조건을 충족하지 않아 신청이 어려워요. 다른 국가나 목적의 프로그램을 확인해 보세요.",
                    status="blocked",
                ))
            elif req.outcome == "추가 확인 필요":
                citations = citations_by_req.get(req.requirement_id, [])
                description = "공식 안내에서 직접 확인이 필요한 조건이에요."
                if not citations:
                    description += " (근거 부족: 관련 공식 자료를 찾지 못했어요)"
                items.append(PrepItem(
                    id=f"{result.program_id}::{req.requirement_id}",
                    program_id=result.program_id,
                    title=f"확인 필요: {req.requirement_id}",
                    description=description,
                    status="check_needed",
                    citations=citations,
                ))

        if result.overall != "조건 미충족" and program:
            items.append(PrepItem(
                id=f"{result.program_id}::apply",
                program_id=result.program_id,
                title=f"{program.name} 신청 절차·서류 확인",
                description="공식 안내 페이지에서 신청 일정과 제출 서류를 확인하세요.",
                status="todo",
                citations=program.citations,
            ))
    return items


def build_reply(programs: list[ProgramCandidate], results: list[EligibilityPayload], changed_fields: list[str]) -> str:
    names = {p.program_id: p.name for p in programs}
    lines = []
    if changed_fields:
        lines.append(f"바뀐 정보({', '.join(changed_fields)})로 다시 검토했어요.")
    for r in results:
        lines.append(f"- {names.get(r.program_id, r.program_id)}: {r.overall}")
    if any(r.overall == "조건 미충족" for r in results):
        lines.append("충족하지 못한 조건이 있어요. 다른 나라나 목적으로 바꿔서 다시 찾아볼 수 있어요.")
    lines.append("아래 준비 항목과 출처를 확인해 주세요.")
    return "\n".join(lines)
