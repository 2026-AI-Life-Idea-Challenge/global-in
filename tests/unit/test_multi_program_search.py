"""Offline contracts for global retrieval: no DB, model, network or keys."""

from contextlib import contextmanager
from copy import deepcopy
import unittest
from unittest.mock import patch

from psycopg import IsolationLevel

from app.retrieval import multi_program_search as search


def program(key="a", country="australia", category="working_holiday"):
    return {"program_id": key, "name": key, "country": country, "category": category}


def chunk(key="a", links=("a",), similarity=0.5, keyword_score=0.2):
    return {
        "document_id": "doc-" + key, "revision_id": "rev", "chunk_id": key,
        "ordinal": 0, "title": "Title", "body": "Same body for distinct chunks.",
        "knowledge_kind": "policy", "program_ids": list(links),
        "source_references": [
            {"source_url": "https://example.org/#part", "resolved_source_url": "https://other.org/"},
            {"source_url": "https://example.org/#part"}, {"source_url": " "}, {},
        ],
        "document_active": True, "chunk_active": True,
        "document_embedding_approved": False, "chunk_embedding_approved": False,
        "answer_approved": False, "content_review_status": None,
        "document_release_id": "doc-release", "chunk_release_id": "chunk-release",
        "similarity": similarity, "keyword_score": keyword_score,
    }


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        self.connection.open_cursors += 1
        return self

    def __exit__(self, *args):
        self.connection.open_cursors -= 1

    def execute(self, query, parameters):
        connection = self.connection
        if not connection.read_only or connection.isolation_level != IsolationLevel.REPEATABLE_READ:
            raise AssertionError("Every SQL must run in a read-only repeatable-read transaction")
        connection.executed.append((query, deepcopy(parameters)))
        index = len(connection.executed) - 1
        if connection.error_at == index:
            raise connection.error
        self.rows = deepcopy(connection.responses[index])

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, responses):
        self.responses = responses
        self.executed = []
        self.read_only = False
        self.isolation_level = None
        self.open_cursors = 0
        self.closed = False
        self.error_at = None
        self.error = RuntimeError("query failed")

    def cursor(self, **kwargs):
        return FakeCursor(self)


class SearchTests(unittest.TestCase):
    def test_local_model_unavailable_keeps_keyword_evidence(self):
        self.embed.side_effect = search.LocalEmbeddingUnavailable('no local model')
        rows = search.search_programs_evidence_hybrid('age', require_source_url=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['keyword_rank'], 1)
        self.assertIsNone(rows[0]['vector_rank'])
        self.assertEqual(len(self.connection.executed), 2)

    def setUp(self):
        self.connection = FakeConnection([[program()], [chunk()], [chunk()]])

        @contextmanager
        def connection():
            try:
                yield self.connection
            finally:
                self.connection.closed = True

        self.db_patch = patch.object(search, "get_connection", side_effect=connection)
        self.embed_patch = patch.object(search, "embed_query_local", return_value=[1.0] + [0.0] * 1023)
        self.db = self.db_patch.start()
        self.embed = self.embed_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.embed_patch.stop)

    def test_invalid_inputs_before_model_and_db(self):
        cases = [{"text": value} for value in (None, True, 1, [], "", " \t")]
        cases += [{"country": value} for value in ("", "Australia", "unknown", True, [])]
        cases += [{"category": value} for value in ("", "tourism", True, [])]
        cases += [{"limit": value} for value in (0, 101, True, 1.5, "5", None)]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                search.search_programs_evidence_hybrid(**{"text": "age", **change})
        self.db.assert_not_called()
        self.embed.assert_not_called()

    def test_filters_parameterized_readonly_and_single_embedding(self):
        text = "  funds ' ; --  "
        result = search.search_programs_evidence_hybrid(text, "australia", "working_holiday")
        self.embed.assert_called_once_with(text)
        self.db.assert_called_once()
        candidate_sql, candidate_parameters = self.connection.executed[0]
        self.assertEqual(candidate_parameters, ["australia", "working_holiday"])
        self.assertIn("country = %s", candidate_sql)
        self.assertIn("category = %s", candidate_sql)
        self.assertTrue(all(text not in sql for sql, _ in self.connection.executed))
        self.assertTrue(all("LIMIT" not in sql.upper() for sql, _ in self.connection.executed))
        self.assertEqual(self.connection.executed[1][1][:2], ("PROGRAM", ["a"]))
        self.assertEqual(self.connection.executed[2][1][-1], search.MODEL_NAME)
        self.assertEqual(result[0]["program_ids"], ["a"])
        self.assertEqual(result[0]["programs"], [program()])
        self.assertNotIn("program_id", result[0])
        self.assertTrue(self.connection.closed)
        self.assertEqual(self.connection.open_cursors, 0)

    def test_optional_filters_are_independently_omitted(self):
        for country, category, parameters in (
            (None, None, []), (None, "study", ["study"]), ("canada", None, ["canada"]),
        ):
            self.connection.executed.clear()
            with self.subTest(country=country, category=category):
                search.search_programs_evidence_hybrid("age", country, category)
                sql, values = self.connection.executed[0]
                self.assertEqual(values, parameters)
                self.assertEqual("country = %s" in sql, country is not None)
                self.assertEqual("category = %s" in sql, category is not None)

    def test_no_candidate_skips_embedding_and_other_queries(self):
        self.connection.responses = [[]]
        self.assertEqual(search.search_programs_evidence_hybrid("age"), [])
        self.embed.assert_not_called()
        self.assertEqual(len(self.connection.executed), 1)
        self.assertTrue(self.connection.closed)

    def test_no_evidence_is_empty_but_still_only_one_embedding(self):
        self.connection.responses = [[program()], [], []]
        self.assertEqual(search.search_programs_evidence_hybrid("age"), [])
        self.embed.assert_called_once()

    def test_empty_keyword_query_skips_keyword_sql_not_vector(self):
        self.connection.responses = [[program()], [chunk()]]
        result = search.search_programs_evidence_hybrid("the and")
        self.assertIsNone(result[0]["keyword_rank"])
        self.assertIsNone(result[0]["keyword_score"])
        self.assertEqual(len(self.connection.executed), 2)
        self.embed.assert_called_once_with("the and")

    def test_all_125_programs_and_151_ranked_chunks_reach_fusion(self):
        programs = [program(str(index)) for index in range(125)]
        vector = [chunk(f"c{index:03}", ("124",), 1 - index / 200) for index in range(151)]
        winner = deepcopy(vector[-1])
        winner["keyword_score"] = 1.0
        self.connection.responses = [programs, [winner], vector]
        result = search.search_programs_evidence_hybrid("age", limit=1)
        self.assertEqual(result[0]["chunk_id"], "c150")
        self.assertEqual(result[0]["vector_rank"], 151)
        self.assertEqual(result[0]["keyword_rank"], 1)
        self.assertEqual(len(self.connection.executed[2][1][1]), 125)
        self.assertAlmostEqual(result[0]["rrf_score"], 1 / 211 + 1 / 61)
        self.embed.assert_called_once()

    def test_db_errors_propagate_and_resources_close(self):
        for index in range(3):
            self.connection.executed.clear()
            self.connection.closed = False
            self.connection.error_at = index
            with self.subTest(index=index), self.assertRaises(RuntimeError) as caught:
                search.search_programs_evidence_hybrid("age")
            self.assertIs(caught.exception, self.connection.error)
            self.assertTrue(self.connection.closed)
            self.assertEqual(self.connection.open_cursors, 0)

    def test_loading_and_connection_errors_are_not_empty_results(self):
        error = RuntimeError("model failed")
        self.embed.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            search.search_programs_evidence_hybrid("age")
        self.assertIs(caught.exception, error)
        self.assertTrue(self.connection.closed)
        self.assertEqual(self.connection.open_cursors, 0)
        self.db.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            search.search_programs_evidence_hybrid("age")
        self.assertIs(caught.exception, error)


class FusionTests(unittest.TestCase):
    def fuse(self, vector, keyword, limit=100):
        return search._fuse_global_rankings(vector, keyword, [program("a"), program("b")], limit)

    def test_global_order_across_programs_not_local_ranks(self):
        vector = [chunk("b", ("b",), 0.9), chunk("a", ("a",), 0.8)]
        keyword = [chunk("a", ("a",), keyword_score=0.7), chunk("b", ("b",), keyword_score=0.2)]
        result = self.fuse(vector, keyword)
        self.assertEqual([row["chunk_id"] for row in result], ["a", "b"])
        self.assertEqual([row["vector_rank"] for row in result], [2, 1])
        self.assertEqual([row["keyword_rank"] for row in result], [1, 2])
        self.assertEqual(result[0]["rrf_score"], result[1]["rrf_score"])

    def test_shared_chunk_keeps_all_links_and_counts_as_one_rank(self):
        shared = chunk("shared", ("b", "a", "a"), 0.9)
        other = chunk("other", similarity=0.1)
        result = self.fuse([shared, deepcopy(shared), other], [shared], limit=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["program_ids"], ["a", "b"])
        self.assertEqual(result[0]["programs"], [program("a"), program("b")])
        self.assertEqual(result[0]["vector_rank"], 1)
        self.assertAlmostEqual(result[0]["rrf_score"], 2 / 61)
        all_results = self.fuse([shared, deepcopy(shared), other], [])
        self.assertEqual(all_results[1]["vector_rank"], 2)

    def test_same_body_different_chunks_survive_with_stable_ties(self):
        result = self.fuse([chunk("b"), chunk("a")], [])
        self.assertEqual([row["chunk_id"] for row in result], ["a", "b"])
        self.assertEqual(result[0]["body"], result[1]["body"])

    def test_nonmatches_and_missing_model_have_no_source_rank(self):
        result = self.fuse([chunk("a")], [chunk("b", ("b",))])
        by_id = {row["chunk_id"]: row for row in result}
        self.assertIsNone(by_id["a"]["keyword_rank"])
        self.assertIsNone(by_id["a"]["keyword_score"])
        self.assertIsNone(by_id["b"]["vector_rank"])
        self.assertIsNone(by_id["b"]["vector_similarity"])
        self.assertAlmostEqual(by_id["a"]["rrf_score"], 1 / 61)

    def test_sources_false_none_and_release_difference_preserved(self):
        row = chunk()
        original = deepcopy(row)
        result = self.fuse([row], [row])[0]
        self.assertEqual(row, original)
        self.assertEqual(result["source_references"], row["source_references"])
        self.assertEqual(result["source_urls"], ["https://example.org/#part"])
        for field in ("answer_approved", "document_embedding_approved", "chunk_embedding_approved"):
            self.assertIs(result[field], False)
        self.assertIsNone(result["content_review_status"])
        self.assertNotEqual(result["document_release_id"], result["chunk_release_id"])
        row["source_references"] = None
        result = self.fuse([row], [])[0]
        self.assertEqual(result["source_references"], [])
        self.assertEqual(result["source_urls"], [])

    def test_conflicting_metadata_or_program_links_are_not_silently_merged(self):
        for change in ({"body": "changed"}, {"answer_approved": True}, {"program_ids": ["b"]}):
            row = {**chunk(), **change}
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                self.fuse([chunk()], [row])

    def test_empty_and_final_limit(self):
        self.assertEqual(self.fuse([], []), [])
        rows = [chunk(str(index)) for index in range(110)]
        self.assertEqual(len(self.fuse(rows, rows, limit=100)), 100)
        self.assertEqual(self.fuse(rows, rows, limit=1), self.fuse(rows, rows)[:1])


if __name__ == "__main__":
    unittest.main()
