from psycopg.rows import dict_row

from app.services.database import get_connection


SUPPORTED_COUNTRIES = frozenset(
    {"japan", "australia", "usa", "germany", "canada"}
)
SUPPORTED_CATEGORIES = frozenset(
    {"employment", "study", "working_holiday"}
)


def _validate_filter(
    field_name: str,
    value: str | None,
    supported_values: frozenset[str],
) -> None:
    if value is None:
        return

    if not isinstance(value, str) or value not in supported_values:
        allowed = ", ".join(sorted(supported_values))
        raise ValueError(
            f"{field_name}는 None 또는 다음 값이어야 합니다: {allowed}"
        )


def search_programs(
    country: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """국가·유형에 맞는 프로그램 후보를 조회한다.

    None인 필터는 생략한다.
    반환 결과는 프로그램 후보이며 신청 자격 판정 결과가 아니다.
    """
    _validate_filter("country", country, SUPPORTED_COUNTRIES)
    _validate_filter("category", category, SUPPORTED_CATEGORIES)

    # bool은 int의 하위 타입이므로 정확한 int만 허용한다.
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit은 1 이상 100 이하의 정수여야 합니다.")

    if type(offset) is not int or offset < 0:
        raise ValueError("offset은 0 이상의 정수여야 합니다.")

    conditions: list[str] = []
    parameters: list[str | int] = []

    if country is not None:
        conditions.append("country = %s")
        parameters.append(country)

    if category is not None:
        conditions.append("category = %s")
        parameters.append(category)

    query = """
        SELECT program_id, name, country, category
        FROM public.programs
    """

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY program_id ASC LIMIT %s OFFSET %s"
    parameters.extend([limit, offset])

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchall()
