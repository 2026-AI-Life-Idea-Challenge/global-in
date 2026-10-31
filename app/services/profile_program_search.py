"""Map the common profile to the existing paginated program candidate search."""

from app.models.user_profile import UserProfile
from app.retrieval.program_search import search_programs


def search_programs_for_profile(
    profile: UserProfile,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Return candidates, without assessing personal eligibility.

    Missing context fields stay None. Only the student alias is converted;
    filter and pagination validation remain with search_programs(). Purpose
    and nationalities do not constrain this country/category lookup.
    """
    if not isinstance(profile, UserProfile):
        raise ValueError("profile은 UserProfile 인스턴스여야 합니다.")

    context = profile.to_search_context()
    category = context.get("target_visa_type")
    if category == "student":
        category = "study"

    return search_programs(
        country=context.get("target_country"),
        category=category,
        limit=limit,
        offset=offset,
    )
