import time
import unittest
import jwt
from fastapi.testclient import TestClient
from chageun_ai.server import create_app, price_of, usage_summary

SECRET = 'test-secret-that-is-at-least-32-characters'
BODY = {'request_id': 'req_1', 'conversation_id': 'c_1', 'question': '가상 질문입니다', 'vehicle': None,
        'maintenance': {'lookup_status': 'not_requested', 'items': [], 'records': []}, 'history': [], 'location': None}


def token(secret=SECRET, issuer='simple-auth-server', expires_in=60):
    claims = {'iss': issuer, 'sub': '7', 'exp': int(time.time()) + expires_in}
    return {'Authorization': 'Bearer ' + jwt.encode(claims, secret, algorithm='HS256')}


class FakeEngine:
    def __init__(self, ask):
        self.ask = ask


class ServerTests(unittest.TestCase):
    def client(self, ask=lambda request: {'request_id': request['request_id'], 'status': 'answered'}, **kw):
        return TestClient(create_app(lambda: FakeEngine(ask), secret=SECRET, **kw))

    def test_query_passes_body_and_requires_valid_token(self):
        seen = []
        with self.client(lambda request: seen.append(request) or {'request_id': request['request_id'], 'status': 'answered'}) as c:
            self.assertEqual(c.get('/health').json(), {'status': 'ok'})
            self.assertEqual(c.post('/rag-query', json=BODY, headers=token()).json()['request_id'], 'req_1')
            self.assertEqual(seen[0]['maintenance']['records'], [])
            for headers in ({}, token(secret='wrong-secret-that-is-at-least-32-chars'), token(issuer='other'),
                            token(expires_in=-10)):
                r = c.post('/rag-query', json=BODY, headers=headers)
                self.assertEqual(r.status_code, 401)
                self.assertIsInstance(r.json()['detail'], str)
        self.assertEqual(len(seen), 1)

    def test_invalid_body_is_422_with_text_detail(self):
        with self.client() as c:
            r = c.post('/rag-query', json=dict(BODY, question='가'), headers=token())
            self.assertEqual(r.status_code, 422)
            self.assertIn('question', r.json()['detail'])
            self.assertEqual(c.post('/rag-query', json={k: v for k, v in BODY.items() if k != 'maintenance'},
                                    headers=token()).status_code, 422)

    def test_unready_index_failure_and_timeout_are_503(self):
        def broken():
            raise FileNotFoundError('no index')
        with TestClient(create_app(broken, secret=SECRET)) as c:
            self.assertEqual(c.get('/health').status_code, 503)
            self.assertEqual(c.post('/rag-query', json=BODY, headers=token()).status_code, 503)
        with self.client(lambda request: 1 / 0) as c:
            self.assertEqual(c.post('/rag-query', json=BODY, headers=token()).status_code, 503)
        with self.client(lambda request: time.sleep(.3), timeout_s=.05) as c:
            self.assertEqual(c.post('/rag-query', json=BODY, headers=token()).status_code, 503)

    def test_usage_summary_prices_each_call_by_its_dated_model_name(self):
        prices = {'gpt-4o-mini': (0.15, 0.60), 'gpt-4o': (2.50, 10.00)}
        self.assertEqual(price_of('gpt-4o-mini-2024-07-18', prices), (0.15, 0.60))  # not gpt-4o's price
        calls = [{'step': 'answer', 'model': 'gpt-4o-mini-2024-07-18', 'in': 4000, 'out': 100, 'ms': 2000},
                 {'step': 'verify', 'model': 'gpt-4o-2024-08-06', 'in': 2000, 'out': 10, 'ms': 900}]
        summary = usage_summary('req_1', 'answered', calls, 3456.7, prices)
        self.assertEqual((summary['tokens_in'], summary['tokens_out'], summary['total_ms']), (6000, 110, 3457))
        self.assertAlmostEqual(summary['cost_usd'], 0.00066 + 0.0051)
        summary = usage_summary('req_1', 'answered', [{**calls[0], 'model': 'unknown-model'}], 1, prices)
        self.assertIsNone(summary['cost_usd'])  # an unpriced model is not silently counted as free


if __name__ == '__main__':
    unittest.main()
