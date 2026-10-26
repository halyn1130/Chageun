import test from 'node:test'
import assert from 'node:assert/strict'
import { answerBlocks, splitAnswer } from '../src/answerSections.js'

test('inline numbered instructions become a separate introduction and four steps', () => {
 const blocks = answerBlocks('앞유리 김서림을 없애려면 다음 단계를 따르세요. 1. 첫 단계. 2. 둘째 단계. 3. 셋째 단계. 4. 넷째 단계.')
 assert.equal(blocks[0].text, '앞유리 김서림을 없애려면 다음 단계를 따르세요.')
 assert.deepEqual(blocks[1].items, ['첫 단계.', '둘째 단계.', '셋째 단계.', '넷째 단계.'])
})
test('parenthesised and circled lists work inside existing answer sections', () => {
 for (const text of ['(1) 첫째 (2) 둘째', '1) 첫째 2) 둘째', '① 첫째 ② 둘째']) {
  const section=splitAnswer('지금 할 일: '+text).sections[0]
  assert.deepEqual(answerBlocks(section.content)[0].items,['첫째','둘째'])
 }
})
test('numbers, source text and nonsequential markers remain unaltered', () => {
 for(const text of ['G1.6 엔진, 1.6 mm, 2026.10.25, 15,000km 또는 12개월', '1. 첫째 3. 셋째', '제1조. 적용 기준'])
  assert.deepEqual(answerBlocks(text),[{type:'paragraph',text}])
})
test('paragraph boundaries keep warnings separate and bullet lines remain a list', () => {
 const blocks=answerBlocks('1. 첫째 2. 둘째\n\n주의: 조건을 확인하세요.\n\n- 하나\n- 둘')
 assert.equal(blocks[0].type,'ordered')
 assert.equal(blocks[1].text,'주의: 조건을 확인하세요.')
 assert.deepEqual(blocks[2],{type:'unordered',items:['하나','둘']})
})

test('four numbered steps keep their list structure across blank lines', () => {
 const blocks = answerBlocks('1. 첫 단계\n\n2. 둘째 단계\n\n3. 셋째 단계\n\n4. 넷째 단계\n\n주의: 별도 안내')
 assert.deepEqual(blocks[0], {type: 'ordered', items: ['첫 단계','둘째 단계','셋째 단계','넷째 단계']})
 assert.equal(blocks[1].text, '주의: 별도 안내')
})
