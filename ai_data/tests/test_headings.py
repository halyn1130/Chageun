import unittest
from chageun_ai.core import is_dangling_heading, carry_dangling_headings


def chunk(cid, head, body, section='편의 장치 > 클러스터 > 경고등 및 표시등', kind='manual', doc='k5'):
    return {'schema_version': 1, 'chunk_id': cid, 'text': f'{head}\n{body}',
            'metadata': {'kind': kind, 'doc_id': doc, 'section': section, 'lights': []}}


HEAD = '[기아 K5] 편의 장치 > 클러스터 > 경고등 및 표시등'


class HeadingTests(unittest.TestCase):
    def test_heading_detection(self):
        for line in ('엔진 경고등', '경고', '주의', '전자식 파킹 브레이크 경고등'):
            self.assertTrue(is_dangling_heading(line), line)
        for line in ('경고등이 켜집니다.', '자세한 내용을 참고하십시오', '마모 상태*2', '연료게이지 점검 ○ ○', '',
                     '이 문장은 서른 글자를 훌쩍 넘기는 긴 설명이라 제목으로 보지 않는 문장입니다 그렇다고 마침표는 없고'):
            self.assertFalse(is_dangling_heading(line), line)

    def test_stranded_heading_moves_to_its_continuation(self):
        a = chunk('a', HEAD, '파워 스티어링 경고등은 3초간 켜졌다가 꺼집니다.\n엔진 경고등')
        b = chunk('b', HEAD + ' (계속)', '엔진 전자제어 장치에 이상이 있을 때 켜집니다.')
        out, changed = carry_dangling_headings([a, b], lights=[])
        self.assertEqual(out[0]['text'], f'{HEAD}\n파워 스티어링 경고등은 3초간 켜졌다가 꺼집니다.')
        self.assertEqual(out[1]['text'], f'{HEAD} (계속)\n엔진 경고등\n엔진 전자제어 장치에 이상이 있을 때 켜집니다.')
        self.assertEqual(changed, ['a', 'b'])
        self.assertEqual([c['chunk_id'] for c in out], ['a', 'b'])  # ids kept for evaluation sets
        self.assertIn('엔진 경고등', a['text'])  # input list is not modified

    def test_nothing_moves_across_sections_documents_laws_or_into_a_new_section(self):
        cases = [
            [chunk('a', HEAD, '본문입니다.\n엔진 경고등'), chunk('b', HEAD, '새 섹션 첫 청크.')],          # not a continuation
            [chunk('a', HEAD, '본문입니다.\n엔진 경고등'), chunk('b', HEAD + ' (계속)', '설명.', doc='avante')],
            [chunk('a', HEAD, '본문입니다.\n3. 승차를 거부하는 행위', kind='law'), chunk('b', HEAD + ' (계속)', '4. 다음 항목', kind='law')],
            [chunk('a', HEAD, '엔진 경고등'), chunk('b', HEAD + ' (계속)', '설명.')],                     # would empty chunk a
            [chunk('a', HEAD, '설명이 끝났습니다.'), chunk('b', HEAD + ' (계속)', '이어지는 설명.')],
        ]
        for pair in cases:
            out, changed = carry_dangling_headings(pair, lights=[])
            self.assertEqual(changed, [])
            self.assertEqual([c['text'] for c in out], [c['text'] for c in pair])


if __name__ == '__main__':
    unittest.main()
