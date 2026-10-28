"""A(자격 검토)·B(탐색·근거) 연결 전 임시 대역.

C 상담 흐름을 먼저 돌려보기 위한 예시 데이터다. A·B 실제 기능이 준비되면
graph.py에서 이 함수들 대신 실제 함수를 연결한다.
"""

from app.models.consult import Citation, EligibilityPayload, Outcome, ProgramCandidate, RequirementPayload, UserProfile

# ---------- B: 프로그램 탐색 · 근거 검색 ----------

_CA_IEC = Citation(
    chunk_id="stub::ca_iec::chunk0",
    title="International Experience Canada",
    source_url="https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec.html",
)
_AU_WHV = Citation(
    chunk_id="stub::au_417::chunk0",
    title="Working Holiday visa (subclass 417)",
    source_url="https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417",
)

_PROGRAMS = [
    ProgramCandidate(
        program_id="CA:iec_working_holiday",
        name="캐나다 워킹홀리데이 (IEC)",
        country="canada",
        purpose="working_holiday",
        summary="(예시) 캐나다에서 일하며 체류할 수 있는 프로그램",
        citations=[_CA_IEC],
    ),
    ProgramCandidate(
        program_id="AU:working_holiday",
        name="호주 워킹홀리데이 (417)",
        country="australia",
        purpose="working_holiday",
        summary="(예시) 호주에서 일하며 여행할 수 있는 비자",
        citations=[_AU_WHV],
    ),
]

_CITATIONS_BY_PREFIX = {"CA": [_CA_IEC], "AU": [_AU_WHV]}


def search_programs(query: str, profile: UserProfile) -> list[ProgramCandidate]:
    return [
        p
        for p in _PROGRAMS
        if (profile.target_country is None or p.country == profile.target_country)
        and (profile.purpose is None or p.purpose == profile.purpose)
    ]


def search_citations(program_id: str, requirement_ids: list[str]) -> dict[str, list[Citation]]:
    """A가 '추가 확인 필요'로 넘긴 requirement별 근거 (A 명세: unknown_requirement_ids 기준 RAG)."""
    found = _CITATIONS_BY_PREFIX.get(program_id.split(":")[0], [])
    return {rid: found for rid in requirement_ids}


# ---------- A: 자격 검토 ----------

# 예시값. 실제 연령 기준은 A가 DB 근거로 확정한다.
_AGE_LIMIT = {"CA:iec_working_holiday": (18, 35), "AU:working_holiday": (18, 30)}
_POLICY_ID = {"CA:iec_working_holiday": "REVIEW:POLICY:CA_IEC_WH_POL_01", "AU:working_holiday": "REVIEW:POLICY:AU_WH_POL_01"}


def check_eligibility(profile: dict, program_ids: list[str], as_of: str) -> list[EligibilityPayload]:
    return [_evaluate(profile, pid) for pid in program_ids]


def _evaluate(profile: dict, program_id: str) -> EligibilityPayload:
    prefix = program_id.split(":")[0]
    low, high = _AGE_LIMIT.get(program_id, (18, 30))
    age = profile.get("age")
    if age is None:
        age_outcome: Outcome = "추가 확인 필요"
    elif low <= age <= high:
        age_outcome = "조건 충족"
    else:
        age_outcome = "조건 미충족"

    requirements = [
        RequirementPayload(requirement_id=f"RULE:AGE:{prefix}_WH_AGE_01", outcome=age_outcome, judgeability="rule_based"),
        RequirementPayload(requirement_id=_POLICY_ID[program_id], outcome="추가 확인 필요", judgeability="conditional"),
    ]
    return EligibilityPayload(
        program_id=program_id,
        overall=_overall([r.outcome for r in requirements]),
        requirements=requirements,
        unknown_requirement_ids=[r.requirement_id for r in requirements if r.outcome == "추가 확인 필요"],
    )


def _overall(outcomes: list[Outcome]) -> Outcome:
    # A 명세의 우선순위: 미충족 > 추가 확인 필요 > 충족
    if "조건 미충족" in outcomes:
        return "조건 미충족"
    if "추가 확인 필요" in outcomes:
        return "추가 확인 필요"
    return "조건 충족"
