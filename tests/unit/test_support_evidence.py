"""지원제도 근거 조회 계약을 DB 연결 없이 검증한다."""

from copy import deepcopy
import unittest
from unittest.mock import MagicMock, patch

import psycopg
from psycopg.rows import dict_row

from app.retrieval import support_evidence as search


EVIDENCE_FIELDS = {
    "support_program_id", "document_id", "revision_id", "chunk_id", "ordinal",
    "title", "body", "knowledge_kind", "source_references", "source_urls",
    "document_active", "chunk_active", "document_embedding_approved",
    "chunk_embedding_approved", "answer_approved", "content_review_status",
    "document_release_id", "chunk_release_id",
}


def evidence_row(**changes):
    return {
        "support_program_id": "SUPPORT_EXAMPLE", "document_id": "document",
        "revision_id": "revision", "chunk_id": "chunk-1", "ordinal": 0,
        "title": "Original title", "body": "Original body", "knowledge_kind": "reviewed_policy",
        "source_references": [{"source_url": "https://example.test/original#section",
                               "title": "Original source", "verified_at": "2026-10-28"}],
        "document_active": True, "chunk_active": True,
        "document_embedding_approved": False, "chunk_embedding_approved": False,
        "answer_approved": False, "content_review_status": "checked_scope_limited",
        "document_release_id": "document-release", "chunk_release_id": "chunk-release",
        **changes,
    }


class SupportEvidenceTests(unittest.TestCase):
    def _db(self, rows):
        manager = MagicMock()
        connection = manager.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = rows

        def execute(query, parameters):
            self.assertIs(connection.read_only, True)

        cursor.execute.side_effect = execute
        return manager, connection, cursor

    def test_invalid_inputs_raise_value_error_before_db_connection(self):
        cases = (
            [{"support_program_id": value} for value in (None, "", " \t\n", True, 1, [], {})]
            + [{"limit": value} for value in (0, -1, 101, True, False, 1.5, "20", None)]
            + [{"offset": value} for value in (-1, True, False, 1.5, "0", None)]
        )
        with patch.object(search, "get_connection") as db:
            for changes in cases:
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    search.search_support_evidence(**{"support_program_id": "valid", **changes})
        db.assert_not_called()

    def test_id_is_trimmed_and_values_are_only_sent_as_parameters(self):
        support_id = "unknown' OR TRUE --"
        manager, connection, cursor = self._db([])
        with patch.object(search, "get_connection", return_value=manager):
            search.search_support_evidence(f" \t{support_id}\n", limit=7, offset=3)
        query, parameters = cursor.execute.call_args.args
        self.assertEqual(parameters, ("SUPPORT_PROGRAM", support_id, 7, 3))
        self.assertNotIn(support_id, query)
        connection.cursor.assert_called_once_with(row_factory=dict_row)

    def test_default_and_boundary_pagination_are_forwarded(self):
        for kwargs, expected in (({}, (20, 0)), ({"limit": 1}, (1, 0)),
                                 ({"limit": 100, "offset": 9}, (100, 9))):
            with self.subTest(kwargs=kwargs):
                manager, _, cursor = self._db([])
                with patch.object(search, "get_connection", return_value=manager):
                    search.search_support_evidence("example", **kwargs)
                self.assertEqual(cursor.execute.call_args.args[1], ("SUPPORT_PROGRAM", "example", *expected))

    def test_all_evidence_fields_original_body_and_false_flags_are_preserved(self):
        rows = [evidence_row()]
        before = deepcopy(rows[0])
        manager, _, _ = self._db(rows)
        with patch.object(search, "get_connection", return_value=manager):
            result = search.search_support_evidence("SUPPORT_EXAMPLE")
        self.assertEqual(set(result[0]), EVIDENCE_FIELDS)
        for key, value in before.items():
            self.assertEqual(result[0][key], value)
        self.assertIs(result[0]["answer_approved"], False)
        self.assertIs(result[0]["document_embedding_approved"], False)
        self.assertIs(result[0]["chunk_embedding_approved"], False)
        self.assertNotEqual(result[0]["document_release_id"], result[0]["chunk_release_id"])

    def test_sources_keep_original_references_order_fragments_and_exact_urls(self):
        references = [
            {"source_url": "https://example.test/b#fragment", "title": "first"},
            {"source_url": "", "resolved_source_url": "https://example.test/resolved"},
            {"source_url": " \t"}, {"source_url": None}, {"source_url": 123}, {},
            {"resolved_source_url": "https://example.test/fallback"},
            {"source_url": "https://example.test/a"},
            {"source_url": "https://example.test/b#fragment", "title": "second capture"},
            {"source_url": "https://example.test/b#different"},
        ]
        before = deepcopy(references)
        manager, _, _ = self._db([evidence_row(source_references=references)])
        with patch.object(search, "get_connection", return_value=manager):
            result = search.search_support_evidence("example")[0]
        self.assertEqual(result["source_references"], before)
        self.assertEqual(references, before)
        self.assertEqual(result["source_urls"], [
            "https://example.test/b#fragment", "https://example.test/a",
            "https://example.test/b#different",
        ])

    def test_no_sources_do_not_remove_chunks_or_fill_missing_document_states(self):
        for references in (None, []):
            with self.subTest(references=references):
                row = evidence_row(source_references=references, answer_approved=None,
                                   document_embedding_approved=None, content_review_status=None)
                manager, _, _ = self._db([row])
                with patch.object(search, "get_connection", return_value=manager):
                    result = search.search_support_evidence("example")
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["source_references"], [])
                self.assertEqual(result[0]["source_urls"], [])
                for field in ("answer_approved", "document_embedding_approved", "content_review_status"):
                    self.assertIsNone(result[0][field])

    def test_distinct_chunks_with_identical_bodies_are_kept(self):
        rows = [evidence_row(), evidence_row(chunk_id="chunk-2", ordinal=1)]
        manager, _, _ = self._db(rows)
        with patch.object(search, "get_connection", return_value=manager):
            result = search.search_support_evidence("example")
        self.assertEqual([row["chunk_id"] for row in result], ["chunk-1", "chunk-2"])
        self.assertEqual(result[0]["body"], result[1]["body"])

    def test_no_results_return_empty_list(self):
        manager, _, _ = self._db([])
        with patch.object(search, "get_connection", return_value=manager):
            self.assertEqual(search.search_support_evidence("not-registered"), [])

    def test_read_only_is_set_before_sql_and_resources_are_closed(self):
        manager, connection, cursor = self._db([])
        with patch.object(search, "get_connection", return_value=manager):
            search.search_support_evidence("example")
        cursor.execute.assert_called_once()
        connection.cursor.return_value.__exit__.assert_called_once_with(None, None, None)
        manager.__exit__.assert_called_once_with(None, None, None)

    def test_connection_errors_propagate(self):
        failure = psycopg.OperationalError("connection failed")
        with patch.object(search, "get_connection", side_effect=failure), \
                self.assertRaises(psycopg.OperationalError) as caught:
            search.search_support_evidence("example")
        self.assertIs(caught.exception, failure)

    def test_sql_and_fetch_errors_propagate_and_resources_close(self):
        for step in ("execute", "fetchall"):
            with self.subTest(step=step):
                manager, connection, cursor = self._db([])
                failure = psycopg.ProgrammingError("query failed")
                getattr(cursor, step).side_effect = failure
                with patch.object(search, "get_connection", return_value=manager), \
                        self.assertRaises(psycopg.ProgrammingError) as caught:
                    search.search_support_evidence("example")
                self.assertIs(caught.exception, failure)
                self.assertIs(connection.cursor.return_value.__exit__.call_args.args[1], failure)
                self.assertIs(manager.__exit__.call_args.args[1], failure)


if __name__ == "__main__":
    unittest.main()
