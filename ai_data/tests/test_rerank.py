import json
import os
import unittest
from unittest import mock
from chageun_ai.core import rerank_hits, RERANK_SYSTEM
from chageun_ai import server


def hits(n):
    return [{'chunk': {'chunk_id': f'c{i}', 'text': f'문단 {i}', 'metadata': {'section': f's{i}'}}, 'score': 1 / (i + 1)}
            for i in range(n)]


def ids(result):
    return [h['chunk']['chunk_id'] for h in result]


class RerankTests(unittest.TestCase):
    def test_model_order_is_applied_and_cut_to_keep(self):
        seen = {}

        def ask(system, user):
            seen.update(system=system, user=user)
            return json.dumps({'order': [3, 0, 2, 1]})
        self.assertEqual(ids(rerank_hits('엔진오일 교환 주기는?', hits(4), ask, keep=3)), ['c3', 'c0', 'c2'])
        self.assertEqual(seen['system'], RERANK_SYSTEM)
        self.assertIn('엔진오일 교환 주기는?', seen['user'])
        self.assertIn('[3] (s3)', seen['user'])

    def test_missing_duplicate_and_unknown_numbers_keep_every_hit(self):
        result = rerank_hits('q', hits(4), lambda s, u: '{"order": [2, 2, 9, "1", -1]}', keep=8)
        self.assertEqual(ids(result), ['c2', 'c1', 'c0', 'c3'])

    def test_any_failure_keeps_search_order(self):
        def boom(system, user):
            raise TimeoutError
        for ask in (boom, lambda s, u: 'not json', lambda s, u: '{"rank": [1]}'):
            self.assertEqual(ids(rerank_hits('q', hits(3), ask)), ['c0', 'c1', 'c2'])

    def test_single_hit_skips_the_model(self):
        def never(system, user):
            raise AssertionError('should not be called')
        self.assertEqual(ids(rerank_hits('q', hits(1), never)), ['c0'])


class EngineRetrieveTests(unittest.TestCase):
    """Engine.retrieve without OpenAI: search and the rerank model are stubbed."""

    def engine(self, reply):
        engine = server.Engine.__new__(server.Engine)
        engine.index = 'idx'
        engine.embedding = mock.Mock(embed_query=lambda q: [0.1])
        engine.rerank_llm = mock.Mock(invoke=lambda messages: mock.Mock(content=reply))
        return engine

    def test_off_by_default_returns_top8_unchanged(self):
        with mock.patch.dict(os.environ, {}, clear=False), mock.patch.object(server, 'search', return_value=hits(8)) as s:
            os.environ.pop('RAG_RERANK', None)
            result = self.engine('{"order": [7]}').retrieve('q', {'kind': 'law'})
        self.assertEqual(s.call_args.args[3], 8)
        self.assertEqual(ids(result), [f'c{i}' for i in range(8)])

    def test_on_takes_15_candidates_and_keeps_8_reranked(self):
        with mock.patch.dict(os.environ, {'RAG_RERANK': '1'}), \
                mock.patch.object(server, 'search', return_value=hits(15)) as s:
            result = self.engine('{"order": [14, 13]}').retrieve('q', {'kind': 'law'})
        self.assertEqual(s.call_args.args[3], 15)
        self.assertEqual(ids(result), ['c14', 'c13', 'c0', 'c1', 'c2', 'c3', 'c4', 'c5'])


if __name__ == '__main__':
    unittest.main()
