import unittest
from datetime import date
from chageun_ai.maintenance import maintenance_answer, add_months
from chageun_ai.agent import rag_query
CAR={'id':1,'manufacturer':'기아','model':'K5','model_year':'2026','powertrain':'G2.0','mileage_km':36200}
RECORDS={'lookup_status':'ok','records':[{'item':'engine_oil','performed_at':'2026-01-24','mileage_km':25000}]}
class MaintenanceTests(unittest.TestCase):
    def test_normal_and_severe(self):
        answer,sources=maintenance_answer(CAR,RECORDS,'engine_oil',today=date(2026,10,24))
        self.assertIn('3개월 남음',answer)
        self.assertIn('3,200km 초과',answer)
        self.assertIn('사용자 설정',answer)
        self.assertIn('2027-01-24',answer)
        self.assertIn('2026',sources[0]['title'])
        answer,_=maintenance_answer(CAR,RECORDS,'engine_oil','severe',date(2026,10,24))
        self.assertIn('3,700km 초과',answer)
    def test_missing_invalid_and_unknown(self):
        self.assertIsNone(maintenance_answer({**CAR,'powertrain':'G1.6T'},RECORDS,'engine_oil'))
        self.assertIn('고정 교환일을 계산하지',maintenance_answer(CAR,RECORDS,'tire')[0])
        self.assertIn('등록해',maintenance_answer(CAR,{'lookup_status':'empty'},'engine_oil')[0])
        self.assertIn('계산할 수 없',maintenance_answer({**CAR,'mileage_km':20000},RECORDS,'engine_oil')[0])
        self.assertIn('입력 필요',maintenance_answer({**CAR,'mileage_km':None},RECORDS,'engine_oil')[0])
    def test_latest_record_and_leap_year(self):
        records={'lookup_status':'ok','records':[*RECORDS['records'],{'item':'engine_oil','performed_at':'2026-10-24','mileage_km':36200}]}
        self.assertIn('8,000km 남음',maintenance_answer(CAR,records,'engine_oil',today=date(2026,10,24))[0])
        self.assertEqual(add_months(date(2024,2,29),12),date(2025,2,28))
    def test_tool_uses_server_records_without_generating_numbers(self):
        def forbidden(*args): self.fail('no LLM calculation or retrieval needed for reviewed rule')
        result=rag_query({'question':'내 엔진오일 언제 갈아','vehicle':CAR,'maintenance':RECORDS},lambda *args:('maintenance_due',{'item':'engine_oil','condition':'normal'}),forbidden,forbidden)
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['action']['vehicle_id'],1)
        self.assertTrue(result['sources'])
        self.assertEqual(result['answer'],result['speech_text'])
