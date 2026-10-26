import unittest
from chageun_ai.evaluation import evaluate_pipeline

ANSWERED = {'status': 'answered', 'answer': '매 15,000 km 또는 12개월', 'action': None,
            'sources': [{'title': 't', 'page': 'p.9-8', 'url': 'u'}]}


def case(**kw):
    return {'id': 'X', 'question': '가상 질문', 'category': 'rag', 'status': 'reviewed', 'expected_status': ['answered'],
            'expected_action': None, 'expected_chunk_ids': ['a'], 'expected_sources': ['p.9-8'],
            'required_facts': ['15,000km', '12개월'], **kw}


class EvaluationTests(unittest.TestCase):
    def test_checks_status_source_facts_and_retrieval(self):
        report = evaluate_pipeline([case()], lambda request: (ANSWERED, ['z', 'a']))
        self.assertEqual((report['pass_rate'], report['failed'], report['provisional']), (1, [], False))
        report = evaluate_pipeline([case(required_facts=['10,000'])], lambda request: (ANSWERED, ['a']))
        self.assertEqual(report['failed'], ['X'])
        self.assertEqual(report['check_rates']['facts'], 0)
        report = evaluate_pipeline([case()], lambda request: (dict(ANSWERED, sources=[]), ['b']))
        self.assertEqual((report['check_rates']['retrieval'], report['check_rates']['source']), (0, 0))

    def test_action_subset_drafts_and_stability(self):
        routed = {'status': 'tool_result', 'action': {'type': 'show_route', 'route': {}}, 'sources': []}
        c = case(category='map_tool', expected_status=['tool_result'], expected_action={'type': 'show_route'},
                 expected_chunk_ids=[], expected_sources=[], required_facts=[])
        self.assertEqual(evaluate_pipeline([c], lambda request: (routed, []))['pass_rate'], 1)
        self.assertEqual(evaluate_pipeline([dict(c, status='draft')], lambda request: (routed, []))['evaluated'], 0)
        flip = iter([routed, {'status': 'not_found', 'action': None, 'sources': []}])
        report = evaluate_pipeline([dict(c, status='draft')], lambda request: (next(flip), []), runs=2, include_drafts=True)
        self.assertEqual((report['pass_rate'], report['unstable'], report['provisional']), (.5, ['X'], True))


if __name__ == '__main__':
    unittest.main()
