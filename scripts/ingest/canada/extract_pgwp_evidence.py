
"""
Canada PGWP official eligibility evidence extraction.

Source: IRCC PGWP 'Who can apply' page.
All policy candidates are unapproved drafts.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data/raw/canada/employment"
    / "pgwp_eligibility_ircc_en.txt"
)

OUTPUT = (
    ROOT / "data/processed/canada/employment"
    / "pgwp_evidence_draft.json"
)

SOURCE_URL = (
    "https://www.canada.ca/en/"
    "immigration-refugees-citizenship/services/"
    "study-canada/work/after-graduation/eligibility.html"
)

REQUIRED_LINES = {
    20: "Who can apply",
    34: "General eligibility",
    37: "PGWP-eligible designated learning institution",
    40: "within 180 days",
    41: "study permit was valid",
    52: "Distance learning",
    72: "Lock-in date between September 1, 2022",
    75: "Lock-in date on or after September 1, 2024",
    89: "Curriculum licensing agreements",
    102: "Taking leave from your studies",
    111: "Transfers between schools",
    129: "Who’s not eligible for a PGWP",
    142: "Eligibility requirements based on study program",
    145: "Canadian Language Benchmarks (CLB) 7",
    165: "on or after November 1, 2024",
    172: "Canadian Language Benchmarks (CLB) 5",
    185: "If you graduated from a flight school",
    192: "Eligibility requirements based on your physical location",
    211: "Field of study requirements",
    227: "Date modified: 2026-06-24",
}

EVIDENCE_RANGES = [
    ("general_eligibility", 34, 42),
    ("accelerated_study_programs", 44, 50),
    ("distance_learning_and_lock_in_dates", 52, 87),
    ("public_private_curriculum_licensing", 89, 100),
    ("leave_transfers_and_special_programs", 102, 128),
    ("ineligible_applicant_categories", 129, 141),
    ("bachelor_master_doctoral_programs", 142, 153),
    ("other_university_programs", 155, 168),
    ("college_polytechnic_and_non_university", 170, 183),
    ("flight_school_programs", 185, 190),
    ("application_location_and_status", 192, 209),
    ("eligible_field_of_study_context", 211, 219),
]

POLICY_DEFINITIONS = [
    (
        "CA_PGWP_POL_01",
        "general_eligibility",
        [
            "pgwp_eligible_dli_and_program",
            "minimum_program_duration",
            "full_time_study_and_final_term_exception",
            "completion_confirmation_date",
            "pgwp_application_within_180_days",
            "study_permit_validity_during_relevant_period",
        ],
        ["general_eligibility"],
    ),
    (
        "CA_PGWP_POL_02",
        "degree_and_program_classification",
        [
            "bachelor_master_doctoral",
            "other_university",
            "college_polytechnic_non_university",
            "pgwp_eligible_flight_school",
        ],
        [
            "bachelor_master_doctoral_programs",
            "other_university_programs",
            "college_polytechnic_and_non_university",
            "flight_school_programs",
        ],
    ),
    (
        "CA_PGWP_POL_03",
        "language_requirements",
        [
            "clb_nclc_level_by_program",
            "four_language_skills",
            "pgwp_application_date_transition",
            "approved_language_tests_and_validity",
        ],
        [
            "bachelor_master_doctoral_programs",
            "other_university_programs",
            "college_polytechnic_and_non_university",
            "flight_school_programs",
        ],
    ),
    (
        "CA_PGWP_POL_04",
        "field_of_study_requirements",
        [
            "study_permit_application_date",
            "degree_based_exemption",
            "eligible_cip_code",
            "current_eligible_field_list",
        ],
        [
            "bachelor_master_doctoral_programs",
            "other_university_programs",
            "college_polytechnic_and_non_university",
            "eligible_field_of_study_context",
        ],
    ),
    (
        "CA_PGWP_POL_05",
        "distance_learning_and_location",
        [
            "lock_in_date",
            "study_in_canada_percentage",
            "in_person_percentage",
            "outside_canada_study_deduction",
            "historic_covid_policy_scope",
            "application_from_inside_or_outside_canada",
        ],
        [
            "distance_learning_and_lock_in_dates",
            "application_location_and_status",
        ],
    ),
    (
        "CA_PGWP_POL_06",
        "special_cases_and_exclusions",
        [
            "accelerated_program",
            "public_private_partnership_start_dates",
            "authorized_leave",
            "dli_transfer",
            "prior_pgwp",
            "non_pgwp_eligible_programs",
        ],
        [
            "accelerated_study_programs",
            "public_private_curriculum_licensing",
            "leave_transfers_and_special_programs",
            "ineligible_applicant_categories",
        ],
    ),
    (
        "CA_PGWP_POL_07",
        "immigration_status_and_application_process",
        [
            "study_permit_expiry",
            "restoration_of_status_if_applicable",
            "application_documents",
            "application_fees",
            "work_authorization_while_waiting",
            "pgwp_validity_length",
        ],
        [
            "general_eligibility",
            "application_location_and_status",
        ],
    ),
]


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    source_hash = hashlib.sha256(raw).hexdigest()

    if len(text) < 10000 or len(lines) < 227:
        raise ValueError("PGWP source appears incomplete")

    if re.search(r"<!DOCTYPE|<html|<script", text, re.I):
        raise ValueError("Expected plain-text IRCC source")

    for number, marker in REQUIRED_LINES.items():
        if marker not in lines[number - 1]:
            raise ValueError(
                f"PGWP source mismatch at line {number}: {marker}"
            )

    evidence = []

    for index, (topic, first, last) in enumerate(
        EVIDENCE_RANGES, 1
    ):
        quote = "\n".join(
            lines[first - 1:last]
        ).strip()

        if len(quote) < 50:
            raise ValueError(
                f"Evidence unexpectedly short: {topic}"
            )

        evidence.append({
            "evidence_id": f"CA_PGWP_EVD_{index:02d}",
            "topic": topic,
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    evidence_ids = {
        item["topic"]: item["evidence_id"]
        for item in evidence
    }

    policies = []

    for policy_id, topic, conditions, topics in POLICY_DEFINITIONS:
        policies.append({
            "policy_id": policy_id,
            "topic": topic,
            "conditions_to_review": conditions,
            "source_evidence_ids": [
                evidence_ids[t] for t in topics
            ],
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result = {
        "country": "Canada",
        "program": "post_graduation_work_permit",
        "program_abbreviation": "PGWP",
        "program_category": "employment",
        "related_program": "study_permit",
        "official_source": {
            "authority": (
                "Immigration, Refugees and Citizenship Canada"
            ),
            "source_url": SOURCE_URL,
            "source_language": "en",
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "source_last_modified": "2026-06-24",
            "char_count": len(text),
            "line_count": len(lines),
        },
        "evidence": evidence,
        "policy_candidates": policies,
        "source_requirement_checks": {
            str(number): marker in lines[number - 1]
            for number, marker in REQUIRED_LINES.items()
        },
        "application_availability": {
            "status": "not_verified",
            "last_checked": None,
            "review_status": "needs_review",
        },
        "follow_up_sources_required": [
            "language_level_test_equivalencies",
            "eligible_fields_of_study_and_cip_codes",
            "program_and_dli_pgwp_eligibility",
            "required_documents",
            "application_procedure",
            "application_fees",
            "permit_duration",
            "work_authorization_while_waiting",
        ],
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    if not (
        len(evidence) == 12
        and len(policies) == 7
        and len(REQUIRED_LINES) == 20
        and len(evidence_ids) == len(evidence)
        and all(result["source_requirement_checks"].values())
        and all(
            item["review_status"] == "needs_review"
            and item["eligibility_rule"] is None
            and item["legal_validation_approved"] is False
            and item["approved_for_eligibility_decision"] is False
            for item in policies
        )
    ):
        raise ValueError("PGWP data consistency check failed")
    
    # PGWP language conversion tables from official IRCC HTML.
    # These are evidence tables, not approved eligibility rules.

    from bs4 import BeautifulSoup

    language_path = (
        ROOT / "data/raw/canada/employment"
        / "pgwp_language_results_official.html"
    )

    if not language_path.is_file():
        raise FileNotFoundError(language_path)

    language_raw = language_path.read_bytes()
    language_text = language_raw.decode("utf-8-sig")
    language_hash = hashlib.sha256(language_raw).hexdigest()

    soup = BeautifulSoup(language_text, "html.parser")
    html_tables = soup.find_all("table")

    if len(html_tables) != 6:
        raise ValueError(
            f"Expected 6 language tables, found {len(html_tables)}"
        )

    table_definitions = [
        ("CELPIP_General", "CLB", None),
        ("IELTS_General_Training", "CLB", None),
        ("PTE_Core", "CLB", None),
        (
            "TEF_Canada_new",
            "NCLC",
            "after_2023_12_10",
        ),
        (
            "TEF_Canada_previous",
            "NCLC",
            "2019_10_01_to_2023_12_10",
        ),
        ("TCF_Canada", "NCLC", None),
    ]

    skills = [
        "reading",
        "writing",
        "listening",
        "speaking",
    ]

    language_evidence = []
    language_tables = []

    for index, (table, definition) in enumerate(
        zip(html_tables, table_definitions), 1
    ):
        test_name, benchmark, date_scope = definition

        parsed_rows = [
            [
                cell.get_text(" ", strip=True)
                for cell in tr.find_all(["th", "td"])
            ]
            for tr in table.find_all("tr")
        ]

        if not parsed_rows:
            raise ValueError(f"Empty language table: {test_name}")

        expected_header = [
            f"{benchmark} level",
            "Reading",
            "Writing",
            "Listening",
            "Speaking",
        ]

        if parsed_rows[0] != expected_header:
            raise ValueError(
                f"Unexpected table header: {test_name}"
            )

        level_rows = {}

        for row in parsed_rows[1:]:
            if len(row) != 5:
                raise ValueError(
                    f"Invalid table row: {test_name}: {row}"
                )

            level = str(int(row[0]))

            if level in level_rows:
                raise ValueError(
                    f"Duplicate benchmark level: {test_name}"
                )

            level_rows[level] = dict(zip(skills, row[1:]))

        if not {"5", "7"}.issubset(level_rows):
            raise ValueError(
                f"Missing required benchmark level: {test_name}"
            )

        table_id = f"CA_PGWP_LANGUAGE_TABLE_{index:02d}"
        evidence_id = f"CA_PGWP_LANG_EVD_{index:02d}"

        language_evidence.append({
            "evidence_id": evidence_id,
            "topic": "language_score_conversion",
            "test_name": test_name,
            "benchmark": benchmark,
            "source_file": (
                language_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": language_hash,
            "html_table_index": index,
            "table_id": table_id,
            "header": parsed_rows[0],
            "rows": parsed_rows[1:],
            "review_status": "needs_review",
        })

        language_tables.append({
            "table_id": table_id,
            "test_name": test_name,
            "benchmark": benchmark,
            "test_date_scope": date_scope,
            "scores_by_level": level_rows,
            "source_evidence_id": evidence_id,
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    # Check key scores directly against the source-derived tables.
    if (
        language_tables[1]["scores_by_level"]["7"]
        != dict.fromkeys(skills, "6.0")
    ):
        raise ValueError("IELTS CLB 7 conversion mismatch")

    if language_tables[2]["scores_by_level"]["7"] != {
        "reading": "60-68",
        "writing": "69-78",
        "listening": "60-70",
        "speaking": "68-75",
    }:
        raise ValueError("PTE Core CLB 7 conversion mismatch")

    if language_tables[3]["scores_by_level"]["7"] != {
        "reading": "434-461",
        "writing": "428-471",
        "listening": "434-461",
        "speaking": "456-493",
    }:
        raise ValueError("TEF Canada NCLC 7 mismatch")

    result["language_conversion_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/work/after-graduation/"
            "eligibility/language-results.html"
        ),
        "source_file": (
            language_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": language_hash,
        "html_table_count": len(html_tables),
        "review_status": "needs_review",
    }

    result["language_conversion_evidence"] = language_evidence
    result["language_conversion_tables"] = language_tables

    result["language_conversion_review"] = {
        "all_four_skills_assessed_separately": True,
        "language_requirement_pgwp_application_date": (
            "2024-11-01"
        ),
        "tef_boundary_date_review_required": True,
        "tef_boundary_date": "2023-12-10",
        "test_result_validity_verified": False,
        "automatic_conversion_approved": False,
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(language_evidence) == 6
        and len(language_tables) == 6
        and len({
            item["evidence_id"]
            for item in language_evidence
        }) == 6
        and all(
            item["review_status"] == "needs_review"
            and item["eligibility_rule"] is None
            and item["legal_validation_approved"] is False
            and item["approved_for_eligibility_decision"] is False
            for item in language_tables
        )
    ):
        raise ValueError(
            "PGWP language conversion integration failed"
        )
    
    # Official PGWP CIP list.
    # Preserve source rows and both application-date columns.
    # Duplicate CIP codes can belong to multiple categories.
    # No automatic eligibility decision is permitted.

    from collections import Counter, defaultdict
    from bs4 import BeautifulSoup

    cip_path = (
        ROOT / "data/raw/canada/employment"
        / "pgwp_field_of_study_official.html"
    )

    if not cip_path.is_file():
        raise FileNotFoundError(cip_path)

    cip_raw = cip_path.read_bytes()
    cip_hash = hashlib.sha256(cip_raw).hexdigest()
    cip_soup = BeautifulSoup(cip_raw, "html.parser")

    cip_tables = cip_soup.find_all("table")

    if len(cip_tables) != 1:
        raise ValueError(
            f"Expected one CIP table, found {len(cip_tables)}"
        )

    table = cip_tables[0]

    parsed_rows = [
        [
            cell.get_text(" ", strip=True)
            for cell in tr.find_all(["th", "td"])
        ]
        for tr in table.find_all("tr")
    ]

    expected_header = [
        "Category",
        "CIP Code",
        "CIP Title",
        "Study permit eligibility",
        "PGWP eligibility",
    ]

    if not parsed_rows or parsed_rows[0] != expected_header:
        raise ValueError("Unexpected CIP table header")

    source_rows = parsed_rows[1:]

    if len(source_rows) != 1107:
        raise ValueError(
            f"Unexpected CIP row count: {len(source_rows)}"
        )

    always_eligible_phrases = {
        "Your CIP code is eligible.",
        "Your field of study is eligible",
    }

    def classify_cip_status(value, application_type):
        if value in always_eligible_phrases:
            return "listed_as_eligible"

        prefix = (
            "Your program is eligible if you submitted "
            f"your {application_type} application "
        )

        if not value.startswith(prefix):
            raise ValueError(
                f"Unknown CIP eligibility wording: {value}"
            )

        if (
            "Before November 1, 2024" in value
            and "After June 25, 2025" in value
        ):
            return "conditional_2025_06_25"

        if (
            "Before November 1, 2024" in value
            and "After December 17, 2024" in value
        ):
            return "conditional_2024_12_17"

        raise ValueError(
            f"Unknown conditional CIP wording: {value}"
        )

    cip_records = []
    cip_by_code = defaultdict(list)

    for row_number, cells in enumerate(source_rows, 1):
        if len(cells) != 5:
            raise ValueError(
                f"Invalid CIP row {row_number}: {cells}"
            )

        (
            category,
            cip_code,
            cip_title,
            study_status,
            pgwp_status,
        ) = cells

        if not re.fullmatch(r"\d{2}\.\d{4}", cip_code):
            raise ValueError(
                f"Invalid CIP code at row {row_number}"
            )

        study_type = classify_cip_status(
            study_status, "study permit"
        )
        pgwp_type = classify_cip_status(
            pgwp_status, "PGWP"
        )

        if study_type != pgwp_type:
            raise ValueError(
                f"Unmatched application conditions: {cip_code}"
            )

        record = {
            "source_row_number": row_number,
            "category": category,
            "cip_code": cip_code,
            "cip_title": cip_title,
            "study_permit_eligibility_text": study_status,
            "pgwp_eligibility_text": pgwp_status,
            "status_classification": study_type,
            "requires_date_specific_review": (
                study_type != "listed_as_eligible"
            ),
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        }

        cip_records.append(record)
        cip_by_code[cip_code].append(row_number)

    duplicate_codes = {
        code: row_numbers
        for code, row_numbers in sorted(cip_by_code.items())
        if len(row_numbers) > 1
    }

    category_counts = dict(
        sorted(
            Counter(
                item["category"] for item in cip_records
            ).items()
        )
    )

    status_counts = dict(
        sorted(
            Counter(
                item["status_classification"]
                for item in cip_records
            ).items()
        )
    )

    expected_status_counts = {
        "listed_as_eligible": 979,
        "conditional_2025_06_25": 119,
        "conditional_2024_12_17": 9,
    }

    expected_category_counts = {
        "Agriculture and agri-food": 43,
        "Education": 69,
        "Healthcare and social services": 594,
        "Science, technology, engineering and math (STEM)": 314,
        "Trade": 66,
        "Transport": 21,
    }

    if (
        len(cip_records) != 1107
        or len(cip_by_code) != 1096
        or len(duplicate_codes) != 11
        or status_counts != expected_status_counts
        or category_counts != expected_category_counts
    ):
        raise ValueError(
            "PGWP CIP source totals differ from reviewed values"
        )

    # Verify repeated codes have the same title and status,
    # while retaining all their categories and source rows.

    for code, row_numbers in duplicate_codes.items():
        group = [
            cip_records[number - 1]
            for number in row_numbers
        ]

        comparison = {
            (
                item["cip_title"],
                item["study_permit_eligibility_text"],
                item["pgwp_eligibility_text"],
            )
            for item in group
        }

        if len(comparison) != 1:
            raise ValueError(
                f"Conflicting duplicate CIP code: {code}"
            )

    cip_code_index = {
        code: {
            "source_row_numbers": row_numbers,
            "categories": sorted({
                cip_records[number - 1]["category"]
                for number in row_numbers
            }),
        }
        for code, row_numbers in sorted(cip_by_code.items())
    }

    cip_evidence_id = "CA_PGWP_CIP_EVD_01"

    result["cip_official_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/work/after-graduation/"
            "eligibility/field-of-study.html"
        ),
        "source_file": cip_path.relative_to(ROOT).as_posix(),
        "source_sha256": cip_hash,
        "html_table_count": 1,
        "table_header": expected_header,
        "review_status": "needs_review",
    }

    result["cip_evidence"] = [{
        "evidence_id": cip_evidence_id,
        "topic": "pgwp_eligible_cip_codes",
        "source_file": cip_path.relative_to(ROOT).as_posix(),
        "source_sha256": cip_hash,
        "html_table_index": 1,
        "data_row_count": len(cip_records),
        "unique_cip_count": len(cip_by_code),
        "review_status": "needs_review",
    }]

    result["cip_code_records"] = cip_records
    result["cip_code_index"] = cip_code_index

    result["cip_code_statistics"] = {
        "source_data_rows": len(cip_records),
        "unique_cip_codes": len(cip_by_code),
        "duplicate_cip_codes": len(duplicate_codes),
        "duplicate_code_details": duplicate_codes,
        "category_counts": category_counts,
        "status_counts": status_counts,
        "conditional_source_rows": 128,
        "source_evidence_id": cip_evidence_id,
        "review_status": "needs_review",
    }

    result["cip_eligibility_review"] = {
        "study_permit_application_date_required": True,
        "pgwp_application_date_required": True,
        "cip_code_format": "XX.XXXX",
        "historical_eligibility_review_required": True,
        "conditional_statuses": [
            "conditional_2025_06_25",
            "conditional_2024_12_17",
        ],
        "date_boundary_interpretation_approved": False,
        "field_of_study_exemptions_verified": False,
        "automatic_cip_eligibility_decision": False,
        "source_evidence_id": cip_evidence_id,
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(result["cip_evidence"]) == 1
        and len(result["cip_code_records"]) == 1107
        and len(result["cip_code_index"]) == 1096
        and all(
            item["review_status"] == "needs_review"
            and item["eligibility_rule"] is None
            and item["legal_validation_approved"] is False
            and item["approved_for_eligibility_decision"] is False
            for item in cip_records
        )
    ):
        raise ValueError("PGWP CIP integration failed")
    
    # PGWP field-of-study exemptions and application-date evidence.
    # Use the existing official HTML; do not create a new source.
    # Exemptions concern the field-of-study requirement only.

    field_heading = next(
        (
            node
            for node in cip_soup.find_all(
                ["h2", "h3", "h4", "summary"]
            )
            if node.get_text(" ", strip=True).casefold()
            == (
                "Who doesn’t need to meet "
                "the field of study requirement"
            ).casefold()
        ),
        None,
    )

    if field_heading is None:
        raise ValueError(
            "Field-of-study exemption heading not found"
        )

    exemption_quote = field_heading.parent.get_text(
        " ", strip=True
    )

    exemption_markers = [
        "You submitted your PGWP application "
        "before November 1, 2024",
        "PGWP-eligible flight school",
        "bachelor’s degree, master’s degree or doctoral degree",
        "You applied for a study permit "
        "before November 1, 2024",
    ]

    if not all(
        marker in exemption_quote
        for marker in exemption_markers
    ):
        raise ValueError(
            "Incomplete field-of-study exemption content"
        )

    field_page_text = cip_soup.get_text(
        " ", strip=True
    )

    date_marker = (
        "You must graduate from a program "
        "that’s on the list of currently eligible "
        "Classification of Instructional Programs "
        "(CIP) codes"
    )

    date_start = field_page_text.find(date_marker)

    if date_start < 0:
        raise ValueError(
            "CIP application-date guidance not found"
        )

    date_quote = field_page_text[
        date_start:date_start + 650
    ]

    date_markers = [
        "study permit application",
        "PGWP application",
        "may still be eligible",
    ]

    if not all(
        marker in date_quote
        for marker in date_markers
    ):
        raise ValueError(
            "Incomplete CIP application-date guidance"
        )

    field_evidence = [
        {
            "evidence_id": "CA_PGWP_FIELD_EVD_01",
            "topic": "field_of_study_exemptions",
            "source_file": (
                cip_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": cip_hash,
            "source_section": (
                "Who doesn’t need to meet "
                "the field of study requirement"
            ),
            "exact_quote": exemption_quote,
            "review_status": "needs_review",
        },
        {
            "evidence_id": "CA_PGWP_FIELD_EVD_02",
            "topic": "cip_application_date_eligibility",
            "source_file": (
                cip_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": cip_hash,
            "source_section": (
                "How to meet the field of study requirement"
            ),
            "exact_quote": date_quote,
            "review_status": "needs_review",
        },
    ]

    result["field_of_study_evidence"] = field_evidence

    result["field_of_study_exemptions"] = {
        "pgwp_application_before": "2024-11-01",
        "study_permit_application_before": "2024-11-01",
        "exempt_degree_types": [
            "bachelor",
            "master",
            "doctoral",
        ],
        "pgwp_eligible_flight_school_exemption": True,
        "exemption_scope": "field_of_study_only",
        "source_evidence_id": "CA_PGWP_FIELD_EVD_01",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    result["field_of_study_date_review"] = {
        "study_permit_application_date_relevant": True,
        "pgwp_application_date_relevant": True,
        "historical_cip_eligibility_must_be_preserved": True,
        "source_evidence_id": "CA_PGWP_FIELD_EVD_02",
        "conditional_cip_source_evidence_id": (
            "CA_PGWP_CIP_EVD_01"
        ),
        "date_boundary_interpretation_approved": False,
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    result["cip_eligibility_review"].update({
        "field_of_study_exemptions_verified": True,
        "exemption_source_evidence_id": (
            "CA_PGWP_FIELD_EVD_01"
        ),
        "date_rule_source_evidence_id": (
            "CA_PGWP_FIELD_EVD_02"
        ),
        "date_boundary_interpretation_approved": False,
        "automatic_cip_eligibility_decision": False,
    })

    if not (
        len(field_evidence) == 2
        and len({
            item["evidence_id"]
            for item in field_evidence
        }) == 2
        and result["field_of_study_exemptions"][
            "exemption_scope"
        ] == "field_of_study_only"
        and all(
            result[key]["review_status"] == "needs_review"
            and result[key]["eligibility_rule"] is None
            and result[key]["legal_validation_approved"] is False
            and result[key][
                "approved_for_eligibility_decision"
            ] is False
            for key in (
                "field_of_study_exemptions",
                "field_of_study_date_review",
            )
        )
    ):
        raise ValueError(
            "PGWP field-of-study integration failed"
        )
    
    # PGWP document requirements: IRCC official evidence.
    # Keep mandatory and conditional submissions separate.
    # All extracted requirements remain unapproved drafts.

    documents_path = (
        ROOT / "data/raw/canada/employment"
        / "pgwp_documents_ircc_en.txt"
    )

    if not documents_path.is_file():
        raise FileNotFoundError(documents_path)

    documents_raw = documents_path.read_bytes()
    documents_text = documents_raw.decode("utf-8-sig")
    documents_lines = documents_text.splitlines()
    documents_hash = hashlib.sha256(
        documents_raw
    ).hexdigest()

    required_document_lines = {
        18: "Get the right documents",
        19: "You need these documents",
        21: "completed your studies",
        22: "full-time studies",
        23: "November 1, 2024",
        24: "eligible field of study",
        25: "upfront medical exam",
        28: "Proof that you completed your studies",
        37: "Proof that you were enrolled",
        42: "Proof of language results",
        45: "optional document",
        55: "less than 2 years old",
        72: "Proof that you graduated",
        79: "Client Information",
        83: "Proof of upfront medical exam",
        96: "Date modified: 2026-06-24",
    }

    for number, marker in required_document_lines.items():
        if (
            len(documents_lines) < number
            or marker not in documents_lines[number - 1]
        ):
            raise ValueError(
                f"PGWP documents source mismatch: line {number}"
            )

    document_ranges = [
        ("document_requirements_overview", 18, 26),
        ("proof_of_program_completion", 28, 35),
        ("proof_of_full_time_studies", 37, 41),
        ("language_test_documents", 42, 71),
        ("field_of_study_documents", 72, 81),
        ("upfront_medical_exam", 83, 88),
    ]

    document_evidence = []

    for index, (topic, first, last) in enumerate(
        document_ranges, 1
    ):
        quote = "\n".join(
            documents_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"PGWP document evidence too short: {topic}"
            )

        document_evidence.append({
            "evidence_id": f"CA_PGWP_DOC_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                documents_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": documents_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["document_requirements_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/work/after-graduation/"
            "get-documents.html"
        ),
        "source_language": "en",
        "source_file": (
            documents_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": documents_hash,
        "source_last_modified": "2026-06-24",
        "char_count": len(documents_text),
        "line_count": len(documents_lines),
        "review_status": "needs_review",
    }

    result["document_evidence"] = document_evidence

    result["document_requirements_review"] = {
        "program_completion": {
            "submission_type": "required",
            "accepted_evidence_to_review": [
                "degree_diploma_or_certificate",
                "official_school_completion_letter",
                "official_transcript_or_school_website_copy",
            ],
            "pgwp_eligible_dli_and_program_required": True,
            "source_evidence_id": "CA_PGWP_DOC_EVD_02",
        },
        "full_time_studies": {
            "submission_type": "required",
            "accepted_evidence_to_review": [
                "official_dli_transcript",
                "dli_website_official_transcript_copy",
            ],
            "source_evidence_id": "CA_PGWP_DOC_EVD_03",
        },
        "language_results": {
            "submission_type": "conditional_required",
            "pgwp_application_on_or_after": "2024-11-01",
            "pgwp_eligible_flight_school_exception": True,
            "language_result_age": "less_than_2_years",
            "language_result_age_reference": (
                "pgwp_application_submission_date"
            ),
            "four_language_abilities_required": True,
            "in_person_test_required": True,
            "online_checklist_may_show_optional": True,
            "source_evidence_id": "CA_PGWP_DOC_EVD_04",
        },
        "field_of_study": {
            "submission_type": "conditional_required",
            "depends_on_field_requirement": True,
            "cip_program_description_evidence": True,
            "upload_section": "Client Information",
            "source_evidence_id": "CA_PGWP_DOC_EVD_05",
        },
        "upfront_medical_exam": {
            "submission_type": "conditional",
            "occupational_medical_requirement": True,
            "work_restriction_implications": True,
            "source_evidence_id": "CA_PGWP_DOC_EVD_06",
        },
        "additional_documents": {
            "submission_type": "may_be_requested",
            "requested_after_application_possible": True,
            "source_evidence_id": "CA_PGWP_DOC_EVD_01",
        },
    }

    for group in result["document_requirements_review"].values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["document_submission_review"] = {
        "disability_related_language_test_process": (
            "separate_official_source_required"
        ),
        "conditional_requirements_must_not_be_treated_as_universal": True,
        "application_document_checklist_may_be_incomplete": True,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in document_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(document_evidence) == 6
        and len(result["document_requirements_review"]) == 6
        and len({
            item["evidence_id"]
            for item in document_evidence
        }) == 6
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in result[
                "document_requirements_review"
            ].values()
        )
    ):
        raise ValueError(
            "PGWP document evidence integration failed"
        )
    
    # IRCC PGWP application process evidence.
    # Application eligibility, status restoration, and
    # authorization to work while processing are separate.
    # All extracted rules remain unapproved.

    application_path = (
        ROOT / "data/raw/canada/employment"
        / "pgwp_application_ircc_en.txt"
    )

    if not application_path.is_file():
        raise FileNotFoundError(application_path)

    application_raw = application_path.read_bytes()
    application_text = application_raw.decode("utf-8-sig")
    application_lines = application_text.splitlines()
    application_hash = hashlib.sha256(
        application_raw
    ).hexdigest()

    required_application_lines = {
        19: "How to apply",
        20: "within Canada or from another country",
        22: "180 days",
        25: "90 days",
        29: "$255",
        30: "$396.25",
        31: "receipt",
        32: "can’t work until",
        36: "valid (not expired)",
        39: "apply on paper",
        41: "passport expired",
        47: "proof of language ability",
        70: "Apply online",
        81: "guide 5487",
        83: "guide 5580",
        94: "optional document",
        96: "Client information",
        103: "open work permit holder fee",
        114: "Biometrics fee",
        128: "If you can’t apply online",
        143: "Date modified: 2026-08-28",
    }

    for number, marker in required_application_lines.items():
        if (
            len(application_lines) < number
            or marker not in application_lines[number - 1]
        ):
            raise ValueError(
                f"PGWP application source mismatch: line {number}"
            )

    application_ranges = [
        ("application_location_and_deadline", 19, 22),
        ("status_restoration_and_work_restrictions", 24, 36),
        ("pgwp_extension_and_condition_changes", 38, 47),
        ("medical_related_work_restrictions", 49, 68),
        ("online_application_and_document_upload", 70, 98),
        ("application_fees_and_account", 100, 125),
        ("paper_application_exceptions", 128, 135),
    ]

    application_evidence = []

    for index, (topic, first, last) in enumerate(
        application_ranges, 1
    ):
        quote = "\n".join(
            application_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"PGWP application evidence too short: {topic}"
            )

        application_evidence.append({
            "evidence_id": f"CA_PGWP_APP_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                application_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": application_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    pgwp_fee_match = re.search(
        r"correct fee \(\$([\d,.]+)\)",
        application_text,
    )

    restoration_fee_match = re.search(
        r"restore your status as a student "
        r"\(\$([\d,.]+)\)",
        application_text,
    )

    if not pgwp_fee_match or not restoration_fee_match:
        raise ValueError(
            "PGWP and restoration fees not found in official source"
        )

    pgwp_fee = float(
        pgwp_fee_match.group(1).replace(",", "")
    )
    restoration_fee = float(
        restoration_fee_match.group(1).replace(",", "")
    )

    if pgwp_fee != 255 or restoration_fee != 396.25:
        raise ValueError(
            "PGWP application fees differ from reviewed source"
        )

    result["application_process_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/work/after-graduation/apply.html"
        ),
        "source_language": "en",
        "source_file": (
            application_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": application_hash,
        "source_last_modified": "2026-08-28",
        "char_count": len(application_text),
        "line_count": len(application_lines),
        "review_status": "needs_review",
    }

    result["application_evidence"] = application_evidence

    application_review = {
        "application_location_and_deadline": {
            "application_locations": [
                "inside_canada",
                "outside_canada",
            ],
            "pgwp_application_deadline_days": 180,
            "deadline_reference": (
                "program_completion_confirmation"
            ),
            "source_evidence_id": "CA_PGWP_APP_EVD_01",
        },
        "status_restoration": {
            "conditional_restoration_window_days": 90,
            "restoration_window_reference": (
                "study_permit_expiry"
            ),
            "status_restoration_is_conditional": True,
            "restoration_receipt_upload_required": True,
            "separate_restoration_application_required": False,
            "pgwp_fee_cad": pgwp_fee,
            "student_status_restoration_fee_cad": (
                restoration_fee
            ),
            "source_evidence_id": "CA_PGWP_APP_EVD_02",
        },
        "work_while_processing": {
            "application_time_study_permit_validity_required": True,
            "study_permit_validity_alone_is_sufficient": False,
            "additional_requirements_need_verification": True,
            "restoration_applicant_cannot_work_before_approval": True,
            "automatic_work_authorization": False,
            "source_evidence_id": "CA_PGWP_APP_EVD_02",
        },
        "pgwp_extension_and_conditions": {
            "extension_general_renewal_allowed": False,
            "passport_expiry_exception": True,
            "extension_or_condition_change_application": (
                "paper"
            ),
            "passport_expiry_extension_language_proof": (
                "not_required_per_source"
            ),
            "medical_related_conditions_need_review": True,
            "source_evidence_ids": [
                "CA_PGWP_APP_EVD_03",
                "CA_PGWP_APP_EVD_04",
            ],
        },
        "online_application": {
            "default_application_method": "online",
            "inside_canada_instruction_guide": "5580",
            "outside_canada_instruction_guide": "5487",
            "ircc_secure_account_required": True,
            "personalized_document_checklist": True,
            "conditional_language_proof_even_if_optional": True,
            "field_of_study_upload_section": (
                "Client Information"
            ),
            "source_evidence_id": "CA_PGWP_APP_EVD_05",
        },
        "fees": {
            "currency": "CAD",
            "pgwp_application_total": pgwp_fee,
            "conditional_student_restoration_total": (
                restoration_fee
            ),
            "combined_if_restoration_required": (
                pgwp_fee + restoration_fee
            ),
            "biometrics_fee_additional_if_applicable": True,
            "third_party_costs_excluded": True,
            "source_evidence_ids": [
                "CA_PGWP_APP_EVD_02",
                "CA_PGWP_APP_EVD_06",
            ],
        },
        "paper_application": {
            "general_online_exceptions": [
                "disability_preventing_online_application",
                "online_application_problem",
            ],
            "pgwp_extension_or_condition_change": (
                "paper"
            ),
            "source_evidence_ids": [
                "CA_PGWP_APP_EVD_03",
                "CA_PGWP_APP_EVD_07",
            ],
        },
    }

    for group in application_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["application_process_review"] = application_review

    result["application_legal_review"] = {
        "pgwp_application_eligibility": "separate_review",
        "immigration_status_and_restoration": (
            "separate_review"
        ),
        "work_authorization_while_processing": (
            "separate_review"
        ),
        "work_while_processing_official_source_required": True,
        "fee_change_reverification_required": True,
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(application_evidence) == 7
        and len(application_review) == 7
        and application_review["fees"][
            "combined_if_restoration_required"
        ] == 651.25
        and application_review[
            "work_while_processing"
        ]["automatic_work_authorization"] is False
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group[
                "approved_for_eligibility_decision"
            ] is False
            for group in application_review.values()
        )
    ):
        raise ValueError(
            "PGWP application process integration failed"
        )
    
    # IRCC PGWP After You Apply evidence.
    # Work authorization, re-entry and family permits are
    # separate from PGWP application eligibility.
    # All requirements remain unapproved review data.

    after_apply_path = (
        ROOT / "data/raw/canada/employment"
        / "pgwp_after_apply_ircc_en.txt"
    )

    if not after_apply_path.is_file():
        raise FileNotFoundError(after_apply_path)

    after_apply_raw = after_apply_path.read_bytes()
    after_apply_text = after_apply_raw.decode("utf-8-sig")
    after_apply_lines = after_apply_text.splitlines()
    after_apply_hash = hashlib.sha256(
        after_apply_raw
    ).hexdigest()

    required_after_apply_lines = {
        18: "After you apply",
        25: "Work while we process your application",
        26: "work full-time",
        28: "valid study permit",
        29: "completed your study program",
        30: "work off campus",
        31: "WP-EXT for PGWP",
        33: "validity period of the letter expires",
        37: "wait until your work permit arrives",
        39: "stop working the day we notify you",
        41: "Get your visitor visa or eTA",
        42: "outside Canada",
        46: "apply for a new visitor visa separately",
        48: "we’ll issue you one",
        50: "Travel outside Canada",
        51: "may not be let back",
        53: "Leaving and re-entering Canada",
        55: "border services officer",
        64: "12 months",
        69: "spouse or common-law partner",
        70: "may be eligible for an open work permit",
        83: "Date modified: 2026-04-24",
    }

    for number, marker in required_after_apply_lines.items():
        if (
            len(after_apply_lines) < number
            or marker not in after_apply_lines[number - 1]
        ):
            raise ValueError(
                "PGWP after-apply source mismatch "
                f"at line {number}: {marker}"
            )

    after_apply_ranges = [
        ("work_while_processing", 25, 39),
        ("visitor_visa_and_eta_after_approval", 41, 48),
        ("travel_and_reentry", 50, 68),
        ("spouse_or_partner_work_permit", 69, 70),
        ("permanent_residence_pathways", 72, 75),
    ]

    after_apply_evidence = []

    for index, (topic, first, last) in enumerate(
        after_apply_ranges, 1
    ):
        quote = "\n".join(
            after_apply_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"After-apply evidence too short: {topic}"
            )

        after_apply_evidence.append({
            "evidence_id": f"CA_PGWP_AFTER_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                after_apply_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": after_apply_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["after_apply_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/work/after-graduation/"
            "after-you-apply.html"
        ),
        "source_language": "en",
        "source_file": (
            after_apply_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": after_apply_hash,
        "source_last_modified": "2026-04-24",
        "char_count": len(after_apply_text),
        "line_count": len(after_apply_lines),
        "review_status": "needs_review",
    }

    result["after_apply_evidence"] = after_apply_evidence

    after_apply_review = {
        "work_while_processing": {
            "conditions_all_required": [
                "valid_study_permit_at_pgwp_application",
                "study_program_completed",
                "eligible_for_off_campus_work_without_permit",
                "did_not_exceed_permitted_work_hours",
            ],
            "work_scope_if_conditions_met": "full_time",
            "work_until_application_decision": True,
            "automatic_work_authorization": False,
            "source_evidence_id": "CA_PGWP_AFTER_EVD_01",
        },
        "wp_ext_letter": {
            "letter": "WP-EXT for PGWP (IMM 0127 E)",
            "letter_expiry_alone_ends_work_authorization": False,
            "underlying_work_conditions_still_required": True,
            "additional_proof_via_ircc_webform": True,
            "source_evidence_id": "CA_PGWP_AFTER_EVD_01",
        },
        "application_refusal": {
            "stop_working_on_refusal_notification": True,
            "work_without_authorization_prohibited": True,
            "source_evidence_id": "CA_PGWP_AFTER_EVD_01",
        },
        "visa_and_eta_after_approval": {
            "outside_canada": (
                "new_visitor_visa_or_eta_on_approval"
            ),
            "inside_canada_visitor_visa": (
                "separate_application_if_needed_for_travel"
            ),
            "inside_canada_eta": (
                "eta_issued_on_pgwp_approval_if_required"
            ),
            "source_evidence_id": "CA_PGWP_AFTER_EVD_02",
        },
        "travel_and_reentry": {
            "valid_entry_document_required": True,
            "entry_not_guaranteed_by_pgwp": True,
            "travel_alone_ends_work_eligibility": False,
            "underlying_work_conditions_still_required": True,
            "border_officer_assessment_required": True,
            "medical_results_validity_months_if_required": 12,
            "source_evidence_id": "CA_PGWP_AFTER_EVD_03",
        },
        "spouse_or_partner": {
            "open_work_permit_may_be_available": True,
            "automatic_family_work_permit": False,
            "separate_eligibility_review_required": True,
            "source_evidence_id": "CA_PGWP_AFTER_EVD_04",
        },
        "permanent_residence": {
            "separate_immigration_pathways_exist": True,
            "automatic_permanent_residence": False,
            "source_evidence_id": "CA_PGWP_AFTER_EVD_05",
        },
    }

    for group in after_apply_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["after_apply_review"] = after_apply_review

    # Close the earlier evidence-collection gap, but not
    # the separate legal-approval requirement.
    result["application_process_review"][
        "work_while_processing"
    ].update({
        "additional_requirements_need_verification": False,
        "official_conditions_collected": True,
        "after_apply_source_evidence_id": (
            "CA_PGWP_AFTER_EVD_01"
        ),
        "automatic_work_authorization": False,
    })

    result["application_legal_review"].update({
        "work_while_processing_official_source_required": False,
        "work_while_processing_evidence_collected": True,
        "work_authorization_approval_required": True,
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    })

    if not (
        len(after_apply_evidence) == 5
        and len(after_apply_review) == 7
        and len({
            item["evidence_id"]
            for item in after_apply_evidence
        }) == 5
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in after_apply_review.values()
        )
        and after_apply_review[
            "work_while_processing"
        ]["automatic_work_authorization"] is False
    ):
        raise ValueError(
            "PGWP after-apply integration failed"
        )
    
    # IRCC PGWP permit duration evidence.
    # Maximum possible validity is not a guaranteed duration.
    # Passport expiry and program type are separate conditions.
    # All requirements remain unapproved review data.

    validity_path = (
        ROOT / "data/raw/canada/employment"
        / "pgwp_validity_ircc_en.txt"
    )

    if not validity_path.is_file():
        raise FileNotFoundError(validity_path)

    validity_raw = validity_path.read_bytes()
    validity_text = validity_raw.decode("utf-8-sig")
    validity_lines = validity_text.splitlines()
    validity_hash = hashlib.sha256(
        validity_raw
    ).hexdigest()

    required_validity_lines = {
        18: "About the post-graduation work permit",
        21: "doesn’t automatically",
        28: "How long is a post-graduation work permit valid?",
        29: "expiry date of your passport",
        31: "February 15, 2024",
        32: "3-year PGWP",
        34: "at least 8 months",
        36: "certificate or diploma",
        38: "For all other programs",
        39: "less than 2 years",
        40: "same length as your study program",
        44: "2 years or more",
        45: "valid for 3 years",
        47: "more than 1 program",
        50: "higher language requirement",
        55: "at least 8 months",
        56: "already had one",
        58: "If your passport expires",
        61: "apply to extend your PGWP",
        63: "apply on paper",
        71: "Date modified: 2026-03-09",
    }

    for number, marker in required_validity_lines.items():
        if (
            len(validity_lines) < number
            or marker not in validity_lines[number - 1]
        ):
            raise ValueError(
                "PGWP validity source mismatch "
                f"at line {number}: {marker}"
            )

    validity_ranges = [
        ("pgwp_general_duration_context", 18, 29),
        ("masters_degree_three_year_exception", 31, 36),
        ("other_program_duration", 38, 45),
        ("multiple_eligible_programs", 47, 56),
        ("passport_expiry_and_extension", 58, 63),
    ]

    validity_evidence = []

    for index, (topic, first, last) in enumerate(
        validity_ranges, 1
    ):
        quote = "\n".join(
            validity_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"PGWP validity evidence too short: {topic}"
            )

        validity_evidence.append({
            "evidence_id": f"CA_PGWP_VALID_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                validity_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": validity_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["validity_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/work/after-graduation/about.html"
        ),
        "source_language": "en",
        "source_file": (
            validity_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": validity_hash,
        "source_last_modified": "2026-03-09",
        "char_count": len(validity_text),
        "line_count": len(validity_lines),
        "review_status": "needs_review",
    }

    result["validity_evidence"] = validity_evidence

    validity_review = {
        "general_duration": {
            "depends_on": [
                "study_program_level",
                "study_program_duration",
                "passport_expiry_date",
                "other_pgwp_eligibility_requirements",
            ],
            "graduation_from_dli_alone_sufficient": False,
            "actual_permit_duration_guaranteed": False,
            "source_evidence_id": "CA_PGWP_VALID_EVD_01",
        },
        "masters_degree": {
            "special_rule_effective_from": "2024-02-15",
            "minimum_program_months": 8,
            "quebec_minimum_hours": 900,
            "maximum_pgwp_years": 3,
            "shorter_than_two_years_may_qualify": True,
            "certificate_or_diploma_excluded": True,
            "all_other_eligibility_requirements_apply": True,
            "actual_permit_duration_guaranteed": False,
            "source_evidence_id": "CA_PGWP_VALID_EVD_02",
        },
        "other_programs": {
            "minimum_program_months": 8,
            "quebec_minimum_hours": 900,
            "under_two_year_program": (
                "up_to_program_length"
            ),
            "two_year_or_longer_program": (
                "up_to_three_years"
            ),
            "actual_permit_duration_guaranteed": False,
            "source_evidence_id": "CA_PGWP_VALID_EVD_03",
        },
        "multiple_programs": {
            "combined_duration_may_be_available": True,
            "each_program_pgwp_eligible": True,
            "each_program_minimum_months": 8,
            "quebec_minimum_hours": 900,
            "higher_language_requirement_applies": True,
            "previous_pgwp_prevents_new_pgwp": True,
            "actual_permit_duration_guaranteed": False,
            "source_evidence_id": "CA_PGWP_VALID_EVD_04",
        },
        "passport_expiry_and_extension": {
            "permit_limited_by_passport_expiry": True,
            "extension_reason": (
                "passport_expired_before_full_eligible_duration"
            ),
            "new_valid_passport_required": True,
            "extension_application_method": "paper",
            "general_pgwp_renewal_allowed": False,
            "actual_extension_approval_guaranteed": False,
            "source_evidence_id": "CA_PGWP_VALID_EVD_05",
        },
    }

    for group in validity_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["validity_review"] = validity_review

    result["validity_legal_review"] = {
        "maximum_duration_is_not_guaranteed": True,
        "program_length_and_credential_review_required": True,
        "passport_expiry_must_be_considered": True,
        "automatic_permit_duration_calculation": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in validity_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(validity_evidence) == 5
        and len(validity_review) == 5
        and len({
            item["evidence_id"]
            for item in validity_evidence
        }) == 5
        and validity_review["masters_degree"][
            "maximum_pgwp_years"
        ] == 3
        and validity_review["passport_expiry_and_extension"][
            "extension_application_method"
        ] == "paper"
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in validity_review.values()
        )
    ):
        raise ValueError(
            "PGWP validity evidence integration failed"
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== CANADA PGWP ELIGIBILITY EVIDENCE ===")
    print("SOURCE CHARS:", len(text))
    print("SOURCE LINES:", len(lines))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("SOURCE CHECKS:", len(REQUIRED_LINES))
    print("SOURCE MODIFIED: 2026-06-24")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()