"""지원제도 목록과 등록된 프로그램 연결을 읽기 전용으로 조회한다."""

from psycopg.rows import dict_row

from app.retrieval.program_search import SUPPORTED_COUNTRIES, _validate_filter
from app.services.database import get_connection


DESTINATION_COUNTRY_CODES = {
    "japan": "JP",
    "australia": "AU",
    "usa": "US",
    "germany": "DE",
    "canada": "CA",
}


def search_support_programs(
    destination_country: str | None = None,
    program_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """조건에 맞는 지원제도를 ID순으로 중복 없이 반환한다.

    목적지국은 기존 국가명(japan/australia/usa/germany/canada)을 받아
    프로필의 destination_countries 국가 코드 배열에서 조회한다.
    None인 필터는 생략하며, 두 필터를 지정하면 AND로 적용한다.
    program_id의 앞뒤 공백은 제거한다. limit은 1..100, offset은 0 이상이다.

    기본 정보와 metadata, 원본 profile, 프로필의 국가 배열·적용 범위·
    availability·source_verified_at·profile_release_id를 보존한다.
    출처는 profile의 source/additional_sources에 원본 그대로 남는다.
    프로필이 없으면 해당 필드는 None이며, 국가 조건이 없으면 유지한다.
    날짜·시각은 psycopg가 반환하는 date/datetime 타입을 유지한다.

    program_links에는 각 지원제도의 전체 등록 연결을 program_id순으로
    반환한다. program_id 필터가 있어도 다른 등록 연결을 숨기지 않는다.
    연결이 없으면 빈 목록이다. 페이지는 연결 수가 아닌 지원제도 수로 센다.

    CLOSED/UNKNOWN이나 승인 상태로 제외하지 않는다. 연결 및
    eligibility_implied는 개인의 자격 판정이나 승인 여부가 아니다.
    []는 검색 결과/등록 연결이 없다는 뜻이며, 이용 가능한 제도가 없다는
    판정이 아니다. DB 및 SQL 오류는 호출자에게 그대로 전달한다.
    """
    _validate_filter("destination_country", destination_country, SUPPORTED_COUNTRIES)
    if program_id is not None:
        if not isinstance(program_id, str) or not program_id.strip():
            raise ValueError("program_id는 None 또는 비어 있지 않은 문자열이어야 합니다.")
        program_id = program_id.strip()
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit은 1 이상 100 이하의 정수여야 합니다.")
    if type(offset) is not int or offset < 0:
        raise ValueError("offset은 0 이상의 정수여야 합니다.")

    conditions: list[str] = []
    parameters: list[str | int] = []
    if destination_country is not None:
        conditions.append("%s = ANY(p.destination_countries)")
        parameters.append(DESTINATION_COUNTRY_CODES[destination_country])
    if program_id is not None:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM public.program_support_links AS matched
                WHERE matched.support_program_id = s.support_program_id
                  AND matched.program_id = %s
            )
        """)
        parameters.append(program_id)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    # Select one support per row and paginate before aggregating its links.
    query = """
        WITH selected AS (
            SELECT s.support_program_id, s.country, s.name, s.provider,
                   s.source_file, s.review_status, s.metadata,
                   s.created_at, s.updated_at,
                   p.publisher_countries, p.destination_countries,
                   p.korean_applicability, p.availability, p.source_verified_at,
                   p.profile, p.release_id AS profile_release_id
            FROM public.support_programs AS s
            LEFT JOIN public.support_program_profiles AS p
              ON p.support_program_id = s.support_program_id
    """ + where_clause + """
            ORDER BY s.support_program_id ASC
            LIMIT %s OFFSET %s
        )
        SELECT selected.*,
               COALESCE((
                   SELECT jsonb_agg(jsonb_build_object(
                       'program_id', l.program_id,
                       'relationship', l.relationship,
                       'eligibility_implied', l.eligibility_implied,
                       'conditions', l.conditions,
                       'source_urls', l.source_urls,
                       'release_id', l.release_id
                   ) ORDER BY l.program_id)
                   FROM public.program_support_links AS l
                   WHERE l.support_program_id = selected.support_program_id
               ), '[]'::jsonb) AS program_links
        FROM selected
        ORDER BY selected.support_program_id ASC
    """
    parameters.extend([limit, offset])

    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchall()
