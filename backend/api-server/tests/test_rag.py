import unittest
from unittest.mock import patch

import httpx
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import CurrentUser
from app.routers import rag


class RagProxyTests(unittest.TestCase):
    def test_vehicle_and_records_come_from_owned_database_rows(self):
        vehicle = dict(id=2, manufacturer='기아', model='K5', model_year='2024',
                       powertrain='가솔린 1.6T', mileage_km=36200)
        result = dict(conversation_id='c_test', status='answered', answer='서버 응답')
        maintenance = dict(lookup_status='ok', items=['wiper'], records=[{'item': 'wiper'}])
        context = dict(original_question='와이퍼 기록은?', vehicle={**vehicle, 'mileage_km': 1})
        req = rag.RagRequest(question='와이퍼 기록은?', vehicle_id=2, conversation_id='c_test', context=context)
        user, db = CurrentUser(7, 'test'), object()
        with patch.object(rag, 'get_owned_vehicle', return_value=vehicle) as owned, \
             patch.object(rag, 'latest_maintenance', return_value=maintenance), \
             patch.object(rag, 'load_history', return_value=[{'role': 'user', 'content': '이전 질문'}]), \
             patch.object(rag.httpx, 'post', return_value=httpx.Response(200, json=result)) as post, \
             patch.object(rag, 'save_turn') as save:
            self.assertEqual(rag.rag_query(req, user, HTTPAuthorizationCredentials(scheme='Bearer', credentials='test'), db), result)
            owned.assert_called_once_with(db, user, 2)
            body = post.call_args.kwargs['json']
            self.assertEqual(body['vehicle']['mileage_km'], 36200)
            self.assertEqual(body['vehicle']['model_year'], '2024')
            self.assertEqual(body['maintenance'], maintenance)
            self.assertEqual(body['history'][0]['content'], '이전 질문')
            save.assert_called_once_with(db, user, 'c_test', req.question, result['answer'])

    def test_explicit_ui_no_vehicle_does_not_use_primary_but_legacy_omission_does(self):
        user, db = CurrentUser(7, 'test'), object()
        for context, should_pick in [(dict(original_question='질문입니다', vehicle=None), False), (None, True)]:
            req = rag.RagRequest(question='질문입니다', context=context)
            with patch.object(rag, 'pick_vehicle', return_value=None) as pick, \
                 patch.object(rag, 'latest_maintenance', return_value={'lookup_status': 'no_vehicle'}) as maintenance, \
                 patch.object(rag.httpx, 'post', return_value=httpx.Response(200, json={'status': 'need_vehicle', 'answer': '차량 선택'})) as post, \
                 patch.object(rag, 'save_turn'):
                rag.rag_query(req, user, HTTPAuthorizationCredentials(scheme='Bearer', credentials='test'), db)
                self.assertEqual(pick.called, should_pick)
                self.assertIsNone(post.call_args.kwargs['json']['vehicle'])
                maintenance.assert_called_once_with(db, None)
