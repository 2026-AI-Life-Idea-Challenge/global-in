"""Optional embeddings must not discard verified keyword evidence."""
import unittest
from unittest.mock import patch

from app.retrieval import hybrid_search as search
from app.retrieval import query_embedding


class EmbeddingFallbackTests(unittest.TestCase):
    def test_keyword_results_keep_source_filter_and_ranking(self):
        def row(key, urls):
            return {**dict.fromkeys(search.EVIDENCE_FIELDS), 'chunk_id': key,
                    'program_id': 'test', 'source_urls': urls, 'keyword_score': 1.0}
        rows = [row('unlinked', []), row('official', ['https://example.org'])]
        with patch.object(search, 'search_program_evidence_by_keyword', return_value=rows), \
             patch.object(search, 'embed_query_local', side_effect=query_embedding.LocalEmbeddingUnavailable()), \
             patch.object(search, 'search_program_evidence_by_vector') as vector:
            result = search.search_program_evidence_hybrid('test', 'prepare', require_source_url=True)
        self.assertEqual([item['chunk_id'] for item in result], ['official'])
        self.assertEqual(result[0]['keyword_rank'], 1)
        self.assertIsNone(result[0]['vector_rank'])
        vector.assert_not_called()

    def test_inference_errors_are_not_silently_ignored(self):
        with patch.object(search, 'search_program_evidence_by_keyword', return_value=[]), \
             patch.object(search, 'embed_query_local', side_effect=RuntimeError('inference failed')):
            with self.assertRaisesRegex(RuntimeError, 'inference failed'):
                search.search_program_evidence_hybrid('test', 'prepare')

    def test_missing_cache_is_reported_as_optional_model_unavailable(self):
        with patch.object(query_embedding, '_get_local_components', side_effect=OSError('no cache')):
            with self.assertRaises(query_embedding.LocalEmbeddingUnavailable):
                query_embedding.embed_query_local('prepare')
