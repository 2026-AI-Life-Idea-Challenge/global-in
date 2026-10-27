
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.models.program_mapping import (
    VERIFIED_PROGRAM_DISPLAY_NAMES,
    PROGRAM_DISPLAY_NAME_SOURCES,
    validate_program_display_name_registry,
)

COUNTRY_CODES = {
    "AU": "australia",
    "JP": "japan",
    "US": "usa",
    "DE": "germany",
    "CA": "canada",
}


def main():
    load_dotenv(ROOT / ".env")

    errors = validate_program_display_name_registry()
    if errors:
        raise ValueError(f"Registry validation failed: {errors}")

    if set(VERIFIED_PROGRAM_DISPLAY_NAMES) != set(PROGRAM_DISPLAY_NAME_SOURCES):
        raise ValueError("Program IDs and source IDs do not match")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured in .env")

    programs = []

    for program_id, name in VERIFIED_PROGRAM_DISPLAY_NAMES.items():
        prefix = program_id.split(":", 1)[0]
        country = COUNTRY_CODES.get(prefix)

        if country is None:
            raise ValueError(f"Unknown country prefix: {program_id}")

        source = PROGRAM_DISPLAY_NAME_SOURCES[program_id]

        programs.append(
            (
                program_id,
                country,
                name,
                "needs_review",
                {
                    "display_name_source": source,
                    "seed_origin": "app.models.program_mapping",
                },
            )
        )

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for program in programs:
                cur.execute(
                    """
                    INSERT INTO programs (
                        program_id,
                        country,
                        name,
                        review_status,
                        metadata
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s::jsonb
                    )
                    ON CONFLICT (program_id)
                    DO UPDATE SET
                        country = EXCLUDED.country,
                        name = EXCLUDED.name,
                        metadata = programs.metadata ||
                                   EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        program[0],
                        program[1],
                        program[2],
                        program[3],
                        psycopg.types.json.Json(program[4]),
                    ),
                )

        print(f"Seed completed: {len(programs)} programs")


if __name__ == "__main__":
    main()