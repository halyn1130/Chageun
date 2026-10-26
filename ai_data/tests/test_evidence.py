import unittest

from chageun_ai.core import evidence_passage

TABLE = """[도로교통법 시행규칙 [별표 6] 안전표지] 노면표시 508 진로변경제한선표시
·차가 점선이 있는
쪽에서는 진로를
변경 할 수 있으
나, 실선이 있는
쪽에서는 진로변경
을 제한하는 것
·고속도로 및 자동차 전용도
로에서 필요한 지점에 설
치"""


class EvidencePassageTests(unittest.TestCase):
    def test_a_wrapped_table_cell_is_shown_as_its_whole_item(self):
        passage = evidence_passage(TABLE, '변경 할 수 있으')
        self.assertTrue(passage.startswith('·차가 점선이 있는 쪽에서는'))
        self.assertIn('실선이 있는 쪽에서는 진로변경 을 제한하는 것', passage)
        self.assertNotIn('고속도로', passage)

    def test_a_quote_that_is_not_found_is_kept_as_is(self):
        self.assertEqual(evidence_passage(TABLE, '없는 문장'), '없는 문장')

    def test_a_long_prose_section_keeps_only_the_cited_sentences(self):
        text = ('[설명서] 타이어 > 저압\n' + '앞 문장입니다. ' * 30 + '경고등이 켜지면 즉시 속도를\n낮추고, 급커브는 자제하십시오. '
                + '뒤 문장입니다. ' * 30)
        passage = evidence_passage(text, '경고등이 켜지면 즉시 속도를', limit=100)
        self.assertEqual(passage, '경고등이 켜지면 즉시 속도를 낮추고, 급커브는 자제하십시오.')


if __name__ == '__main__':
    unittest.main()
