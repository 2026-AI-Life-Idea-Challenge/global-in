
import os
import re
import sys
from collections import Counter
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

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

WORKING_HOLIDAY_IDS = {
    "AU:subclass_417_first",
    "AU:subclass_417_second",
    "AU:subclass_417_third",
    "AU:subclass_462_first",
    "AU:subclass_462_second",
    "AU:subclass_462_third",
    "CA:iec_working_holiday",
    "DE:working_holiday",
    "JP:JP-WH-01",
    "US:US-WH-01",
}

STUDY_IDS = {
    "AU:subclass_500",
    "CA:study_permit",
    "DE:study_visa",
    "DE:seeking_higher_education_place",
    "JP:JP-ST-01",
    "US:US-ST-01",
    "US:US-ST-03",
}

AUSTRALIA_STREAMS = {
    "186_direct_entry": "direct_entry",
    "186_labour_agreement": "labour_agreement",
    "186_trt": "temporary_residence_transition",
    "189_points_tested": "points_tested",
    "191_regional_provisional": "regional_provisional",
    "417_first": "first",
    "417_second": "second",
    "417_third": "third",
    "462_first": "first",
    "462_second": "second",
    "462_third": "third",
    "482_core_skills": "core_skills",
    "482_labour_agreement": "labour_agreement",
    "482_specialist_skills": "specialist_skills",
    "494_employer_sponsored": "employer_sponsored",
    "494_labour_agreement": "labour_agreement",
}


def classify_program(program_id, country):
    route_id = program_id.split(":", 1)[1]

    if program_id in WORKING_HOLIDAY_IDS:
        category = "working_holiday"
    elif program_id in STUDY_IDS:
        category = "study"
    else:
        category = "employment"

    visa_subclass = None
    stream = None

    if country == "australia":
        match = re.fullmatch(r"subclass_(\d+)(?:_(.*))?", route_id)

        if match is None:
            raise ValueError(f"Invalid Australian program ID: {program_id}")

        visa_subclass = match.group(1)
        suffix = match.group(2)

        if suffix:
            stream = AUSTRALIA_STREAMS.get(
                f"{visa_subclass}_{suffix}"
            )

    return category, route_id, visa_subclass, stream


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

    program_ids = set(VERIFIED_PROGRAM_DISPLAY_NAMES)

    if len(program_ids) != 40:
        raise RuntimeError("Expected 40 programs")

    if not WORKING_HOLIDAY_IDS.issubset(program_ids):
        raise RuntimeError("Unknown working holiday program ID")

    if not STUDY_IDS.issubset(program_ids):
        raise RuntimeError("Unknown study program ID")

    if WORKING_HOLIDAY_IDS.intersection(STUDY_IDS):
        raise RuntimeError("Overlapping program classifications")

    programs = []
    categories = Counter()
    australian_stream_count = 0

    for program_id, name in VERIFIED_PROGRAM_DISPLAY_NAMES.items():
        prefix = program_id.split(":", 1)[0]
        country = COUNTRY_CODES.get(prefix)

        if country is None:
            raise ValueError(f"Unknown country prefix: {program_id}")

        category, route_id, visa_subclass, stream = classify_program(
            program_id, country
        )

        source = PROGRAM_DISPLAY_NAME_SOURCES[program_id]

        programs.append(
            (
                program_id,
                country,
                name,
                category,
                route_id,
                visa_subclass,
                stream,
                "needs_review",
                Jsonb({
                    "display_name_source": source,
                    "seed_origin": "app.models.program_mapping",
                }),
            )
        )

        categories[category] += 1

        if country == "australia" and stream is not None:
            australian_stream_count += 1

    expected_categories = {
        "employment": 23,
        "study": 7,
        "working_holiday": 10,
    }

    if dict(categories) != expected_categories:
        raise RuntimeError(f"Category mismatch: {categories}")

    if australian_stream_count != 16:
        raise RuntimeError(
            f"Australian stream mismatch: {australian_stream_count}"
        )

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            for program in programs:
                conn.execute(
                    """
                    INSERT INTO programs (
                        program_id,
                        country,
                        name,
                        category,
                        route_id,
                        visa_subclass,
                        stream,
                        review_status,
                        metadata
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (program_id)
                    DO UPDATE SET
                        country = EXCLUDED.country,
                        name = EXCLUDED.name,
                        category = EXCLUDED.category,
                        route_id = EXCLUDED.route_id,
                        visa_subclass = EXCLUDED.visa_subclass,
                        stream = EXCLUDED.stream,
                        metadata = programs.metadata || EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    program,
                )

            rows = conn.execute(
                """
                SELECT
                    program_id,
                    country,
                    category,
                    route_id,
                    visa_subclass,
                    stream
                FROM programs
                ORDER BY program_id
                """
            ).fetchall()

            if len(rows) != len(programs):
                raise RuntimeError("Program count mismatch")

            for program_id, country, category, route_id, subclass, stream in rows:
                expected = classify_program(program_id, country)

                if (category, route_id, subclass, stream) != expected:
                    raise RuntimeError(
                        f"Classification mismatch: {program_id}"
                    )

            print("=== PROGRAM SEED RESULT ===")
            print("PROGRAMS:", len(rows))
            print("CATEGORY_COUNTS:", dict(categories))
            print("AUSTRALIA_STREAMS:", australian_stream_count)
            print("POSTCHECK: PASS")

    # Evidence 적재 후 단일 원본 파일을 가진 프로그램만 연결
    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            rows = conn.execute(
                """
                SELECT
                    p.program_id,
                    MIN(e.source_file) AS source_file
                FROM programs p
                JOIN evidence e ON e.program_id = p.program_id
                WHERE e.source_file IS NOT NULL
                GROUP BY p.program_id
                HAVING COUNT(DISTINCT e.source_file) = 1
                """
            ).fetchall()

            linked = 0

            for program_id, source_file in rows:
                if not (ROOT / source_file).is_file():
                    continue

                result = conn.execute(
                    """
                    UPDATE programs
                    SET source_file = %s,
                        updated_at = NOW()
                    WHERE program_id = %s
                      AND source_file IS NULL
                    """,
                    (source_file, program_id),
                )

                linked += result.rowcount

            print("SOURCE_FILES_NEWLY_LINKED:", linked)
    # 기존 가공 JSON에서 실제 원천 프로그램 ID 복구
    import json
    from collections import defaultdict
    from app.models.program_mapping import (
        get_source_program_id,
        normalize_program_id,
    )

    source_ids = defaultdict(set)
    valid_ids = set(VERIFIED_PROGRAM_DISPLAY_NAMES)

    for path in (ROOT / "data" / "processed").rglob("*.json"):
        country = next(
            (name for name in COUNTRY_CODES.values()
             if name in path.relative_to(ROOT).parts),
            None,
        )
        if country is None:
            continue

        try:
            obj = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, ValueError):
            continue

        records = [obj] if isinstance(obj, dict) else (
            obj if isinstance(obj, list) else []
        )

        if isinstance(obj, dict):
            for key in ("programs", "records", "items", "data"):
                value = obj.get(key)
                if isinstance(value, list):
                    records.extend(value)

        for record in records:
            if not isinstance(record, dict):
                continue

            source_id = get_source_program_id(country, record)
            if source_id is None:
                continue

            try:
                normalized_id = normalize_program_id(
                    country, source_id
                )
            except (KeyError, ValueError):
                continue

            if normalized_id in valid_ids:
                source_ids[normalized_id].add(source_id)

    # 일본·미국: 가공 JSON 내부의 명시적 program_id 확인
    remaining_ids = {
        "JP:JP-EM-01",
        "JP:JP-ST-01",
        "JP:JP-WH-01",
        "US:US-EM-01",
        "US:US-EM-02",
        "US:US-EM-03",
        "US:US-ST-01",
        "US:US-ST-03",
        "US:US-WEST-01",
        "US:US-WH-01",
    }

    def has_explicit_id(obj, wanted):
        if isinstance(obj, dict):
            if obj.get("program_id") == wanted:
                return True
            return any(
                has_explicit_id(value, wanted)
                for value in obj.values()
                if isinstance(value, (dict, list))
            )

        if isinstance(obj, list):
            return any(has_explicit_id(value, wanted) for value in obj)

        return False

    for country, prefix in (("japan", "JP"), ("usa", "US")):
        folder = ROOT / "data" / "processed" / country

        for path in folder.rglob("*.json"):
            relative = path.relative_to(ROOT).as_posix()

            if any(
                token in relative.lower()
                for token in (
                    "audit",
                    "review_report",
                    "retrieval_index",
                    "retrieval_quality",
                )
            ):
                continue

            try:
                obj = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, ValueError):
                continue

            for program_id in remaining_ids:
                if not program_id.startswith(prefix + ":"):
                    continue

                raw_id = program_id.split(":", 1)[1]

                if has_explicit_id(obj, raw_id):
                    source_ids[program_id].add(raw_id)

    # 원천 ID가 유일하게 확인된 경우만 업데이트
    confirmed = {
        pid: next(iter(values))
        for pid, values in source_ids.items()
        if len(values) == 1
    }

    if len(confirmed) != 40:
        raise RuntimeError(
            f"Expected 30 confirmed source IDs: {len(confirmed)}"
        )

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            updated = 0

            for pid, source_id in confirmed.items():
                result = conn.execute(
                    """
                    UPDATE programs
                    SET source_program_id = %s,
                        updated_at = NOW()
                    WHERE program_id = %s
                      AND (
                          source_program_id IS NULL
                          OR source_program_id = %s
                      )
                    """,
                    (source_id, pid, source_id),
                )

                if result.rowcount != 1:
                    raise RuntimeError(
                        f"Source ID conflict: {pid}"
                    )

                updated += 1

            stored = conn.execute(
                """
                SELECT program_id, source_program_id
                FROM programs
                """
            ).fetchall()

            by_id = dict(stored)

            for pid, source_id in confirmed.items():
                if by_id.get(pid) != source_id:
                    raise RuntimeError(
                        f"Source ID mismatch: {pid}"
                    )

            print("=== SOURCE ID RECOVERY ===")
            print("CONFIRMED:", len(confirmed))
            print("UPDATED_OR_VERIFIED:", updated)
            print(
                "SOURCE_ID_NULL:",
                sum(value is None for value in by_id.values()),
            )
            print("POSTCHECK: PASS")
    print("TRANSACTION: COMMITTED")


if __name__ == "__main__":
    main()