"""지원제도 조회의 입력·원본 보존·DB 호출 계약을 외부 연결 없이 검증한다."""

from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import MagicMock, patch

import psycopg
from psycopg.rows import dict_row

from app.retrieval import support_search as search


class SupportSearchTests(unittest.TestCase):
    def _db(self, rows):
        manager = MagicMock()
        connection = manager.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = rows

        def execute(query, parameters):
            self.assertIs(connection.read_only, True)

        cursor.execute.side_effect = execute
        return manager, connection, cursor

    def test_country_names_use_explicit_profile_country_codes(self):
        for country, code in (
            ("japan", "JP"), ("australia", "AU"), ("usa", "US"),
            ("germany", "DE"), ("canada", "CA"),
        ):
            with self.subTest(country=country):
                manager, connection, cursor = self._db([])
                with patch.object(search, "get_connection", return_value=manager):
                    search.search_support_programs(destination_country=country)
                query, parameters = cursor.execute.call_args.args
                self.assertEqual(parameters, [code, 20, 0])
                self.assertIn("%s = ANY(p.destination_countries)", query)
                self.assertNotIn("s.country =", query)
                connection.cursor.assert_called_once_with(row_factory=dict_row)

    def test_program_filter_and_country_are_combined_without_interpolating_values(self):
        program_id = "not-a-program'; SELECT 1; --"
        manager, _, cursor = self._db([])
        with patch.object(search, "get_connection", return_value=manager):
            search.search_support_programs("australia", f"  {program_id}\t", 7, 3)
        query, parameters = cursor.execute.call_args.args
        self.assertEqual(parameters, ["AU", program_id, 7, 3])
        self.assertNotIn(program_id, query)
        self.assertIn("AND", query)
        self.assertIn("matched.program_id = %s", query)

    def test_none_omits_each_filter_and_pagination_is_forwarded(self):
        for kwargs, expected in (
            ({}, [20, 0]),
            ({"limit": 1, "offset": 0}, [1, 0]),
            ({"limit": 100, "offset": 31}, [100, 31]),
            ({"program_id": " example "}, ["example", 20, 0]),
            ({"destination_country": "canada"}, ["CA", 20, 0]),
        ):
            with self.subTest(kwargs=kwargs):
                manager, _, cursor = self._db([])
                with patch.object(search, "get_connection", return_value=manager):
                    search.search_support_programs(**kwargs)
                query, parameters = cursor.execute.call_args.args
                self.assertEqual(parameters, expected)
                if kwargs.get("destination_country") is None:
                    self.assertNotIn("= ANY(p.destination_countries)", query)
                if kwargs.get("program_id") is None:
                    self.assertNotIn("matched.program_id =", query)

    def test_invalid_inputs_raise_value_error_before_connecting(self):
        cases = (
            [{"destination_country": value} for value in (
                "", " \t", "AU", "Australia", " australia ", "multi_country",
                "unknown", True, 1, [], {},
            )]
            + [{"program_id": value} for value in ("", " \t", True, 1, [], {})]
            + [{"limit": value} for value in (0, -1, 101, True, False, 1.5, "20", None)]
            + [{"offset": value} for value in (-1, True, False, 1.5, "0", None)]
        )
        with patch.object(search, "get_connection") as db:
            for kwargs in cases:
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    search.search_support_programs(**kwargs)
        db.assert_not_called()

    def test_original_profiles_sources_statuses_and_all_links_are_preserved(self):
        rows = [{
            "support_program_id": "EXAMPLE", "country": "multi_country",
            "name": "Original name", "provider": None, "source_file": "original.json",
            "review_status": "checked", "metadata": {"approved": False},
            "publisher_countries": ["KR"], "destination_countries": ["AU", "US"],
            "korean_applicability": "explicit_korean_scope", "availability": status,
            "source_verified_at": date(2026, 10, 28), "profile_release_id": "release-a",
            "profile": {
                "source": {"source_url": "https://example.test/source#section"},
                "additional_sources": [{"source_url": "https://example.test/other"}],
                "application_end": None, "automatic_eligibility_approved": False,
            },
            "program_links": [{
                "program_id": program_id, "relationship": "context_only",
                "eligibility_implied": False, "conditions": ["independent review"],
                "source_urls": ["https://example.test/link#original"],
                "release_id": "release-b",
            } for program_id in ("program-a", "program-b")],
        } for status in ("CLOSED", "UNKNOWN", "OPEN", "UPCOMING")]
        before = deepcopy(rows)
        manager, _, _ = self._db(rows)
        with patch.object(search, "get_connection", return_value=manager):
            result = search.search_support_programs(program_id="program-a")
        self.assertIs(result, rows)
        self.assertEqual(result, before)
        self.assertEqual(len(result[0]["program_links"]), 2)

    def test_missing_profile_and_empty_links_are_not_filled(self):
        rows = [{"support_program_id": "NO_PROFILE", "profile": None,
                 "availability": None, "source_verified_at": None, "program_links": []}]
        manager, _, _ = self._db(rows)
        with patch.object(search, "get_connection", return_value=manager):
            self.assertIs(search.search_support_programs(), rows)
        self.assertIsNone(rows[0]["profile"])
        self.assertEqual(rows[0]["program_links"], [])

    def test_empty_results_are_returned_as_empty_list(self):
        manager, _, _ = self._db([])
        with patch.object(search, "get_connection", return_value=manager):
            self.assertEqual(search.search_support_programs(program_id="not-registered"), [])

    def test_read_only_precedes_sql_and_resources_close_on_success(self):
        manager, connection, cursor = self._db([])
        with patch.object(search, "get_connection", return_value=manager):
            search.search_support_programs()
        cursor.execute.assert_called_once()
        connection.cursor.return_value.__exit__.assert_called_once_with(None, None, None)
        manager.__exit__.assert_called_once_with(None, None, None)

    def test_connection_error_propagates(self):
        error = psycopg.OperationalError("connection failed")
        with patch.object(search, "get_connection", side_effect=error), \
                self.assertRaises(psycopg.OperationalError) as caught:
            search.search_support_programs()
        self.assertIs(caught.exception, error)

    def test_sql_and_fetch_errors_propagate_and_resources_close(self):
        for step in ("execute", "fetchall"):
            with self.subTest(step=step):
                manager, connection, cursor = self._db([])
                error = psycopg.ProgrammingError("query failed")
                getattr(cursor, step).side_effect = error
                with patch.object(search, "get_connection", return_value=manager), \
                        self.assertRaises(psycopg.ProgrammingError) as caught:
                    search.search_support_programs()
                self.assertIs(caught.exception, error)
                self.assertIs(connection.cursor.return_value.__exit__.call_args.args[1], error)
                self.assertIs(manager.__exit__.call_args.args[1], error)


if __name__ == "__main__":
    unittest.main()
