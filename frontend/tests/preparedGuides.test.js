import test from 'node:test'
import assert from 'node:assert/strict'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { useChageun } from '../src/composables/useChageun.js'
import { resolvePreparedGuide, keepPreparedEligibility } from '../src/preparedGuides.js'
import catalog from '../src/preparedGuides.json' with { type: 'json' }
const now = new Date('2026-10-25T12:00:00+09:00')
const car = {id:1,manufacturer:'기아',model:'K5',model_year:2026,powertrain:'G2.0'}
const flow = {preparedEligible:true,category:'controls',topicId:'lights',vehicleId:1,details:{operation:'상향등 전환'}}
test('prepared guides require explicit menu eligibility and exact vehicle and option',()=>{
 assert.ok(resolvePreparedGuide(flow,car,now))
 for(const other of [null,{...car,model_year:2025},{...car,powertrain:'LPI2.0'},{...car,id:2}]) assert.equal(resolvePreparedGuide(flow,other,now),null)
 for(const other of [{...flow,preparedEligible:false},{...flow,serverFollowup:true},{...flow,details:{operation:'상향등 전환했는데 안 돼'}},{...flow,details:{operation:'확인하지 못함'}}]) assert.equal(resolvePreparedGuide(other,car,now),null)
 assert.equal(keepPreparedEligibility(flow,{suggestions:['상향등 전환']},'상향등 전환했는데 안 돼'),false)
})
test('all prepared entries carry sources, short speech and resolve only with matched conditions',()=>{
 for(const entry of catalog.entries){
  const vehicle=entry.vehicle ? {...entry.vehicle,id:1,model:entry.vehicle.models[0]}:null
  const answer=resolvePreparedGuide({preparedEligible:true,category:entry.category,topicId:entry.topicId,vehicleId:1,details:Object.fromEntries(Object.entries(entry.match).map(([key,value])=>[key,Array.isArray(value)?value[0]:value]))},vehicle,now)
  assert.ok(answer,entry.topicId)
  assert.ok(answer.sources.every(s=>s.url.startsWith('https://') && s.chunk_id && s.page))
  assert.ok(answer.speech_text.length<500)
 }
})
test('law guides expire for review and fall back instead of serving stale text',()=>{
 const rule={preparedEligible:true,category:'rules',topicId:'roundabout',details:{}}
 assert.ok(resolvePreparedGuide(rule,null,now))
 assert.equal(resolvePreparedGuide(rule,null,new Date('2026-11-24T00:00:00+09:00')),null)
})
test('menu answer avoids RAG; previous step can change selection; free text still calls RAG',async()=>{
 const saved={localStorage:globalThis.localStorage,window:globalThis.window,fetch:globalThis.fetch}
 globalThis.localStorage={getItem:()=>null}
 globalThis.window={location:{origin:'http://localhost'}}
 let ragCalls=0
 globalThis.fetch=async url=>{
  if(String(url).includes('rag-query')) ragCalls++
  return new Response(JSON.stringify(String(url).includes('rag-query')?{status:'answered',answer:'RAG 응답',sources:[]}:[]),{status:200})
 }
 try {
  let state
  await renderToString(createSSRApp({setup(){state=useChageun();return ()=>h('div')}}))
  state.screen.value='diagnostics'
  state.vehicles.value=[car]
  state.chatVehicleId.value=1
  await state.ask('전조등과 상향등 버튼은 어떻게 써?',{newQuestion:true,preparedMenu:true,category:'controls',topicId:'lights',intent:'controls'})
  await state.replyTo(state.currentMessage.value,'상향등 전환')
  assert.equal(state.currentMessage.value.answerMode,'prepared')
  assert.equal(ragCalls,0)
  state.returnToPreviousStep()
  await state.replyTo(state.currentMessage.value,'전조등 켜기')
  assert.equal(state.currentMessage.value.answerMode,'prepared')
  assert.match(state.currentMessage.value.answer,/끝부분/)
  assert.equal(ragCalls,0)
  state.returnToPreviousStep()
  await state.replyTo(state.currentMessage.value,'상향등 전환했는데 안 켜져요')
  assert.equal(ragCalls,1)
  await state.ask('전조등과 상향등 버튼은 어떻게 써?',{newQuestion:true,category:'controls',topicId:'lights',intent:'controls'})
  await state.replyTo(state.currentMessage.value,'상향등 전환')
  assert.equal(ragCalls,2)
  await state.ask('유리에 김이 서렸어. 김서림 어떻게 없애?',{newQuestion:true,preparedMenu:true,category:'controls',topicId:'defrost',intent:'controls'})
  await state.replyTo(state.currentMessage.value,'잘 모르겠어요')
  assert.equal(state.currentMessage.value.answerMode,'prepared')
  assert.equal(state.currentMessage.value.followup_question,undefined)
  assert.match(state.currentMessage.value.answer,/앞유리:/)
  assert.match(state.currentMessage.value.answer,/뒷유리:/)
  assert.equal(ragCalls,2)

 } finally {Object.assign(globalThis,saved)}
})

test('every road-rule menu and its displayed choices has reviewed local guidance',async()=>{
 const {guidanceCategories}=await import('../src/guidance.js')
 const {clarificationFor,continueQuestion,startQuestion}=await import('../src/conversation.js')
 for(const topic of guidanceCategories.find(c=>c.id==='rules').topics){
  const base={...startQuestion(topic.question),category:'rules',topicId:topic.id,intent:'rules',preparedEligible:true}
  const prompt=clarificationFor(base)
  const flows=prompt ? prompt.suggestions.map(reply=>continueQuestion({...base,awaiting:prompt.field},reply)) : [base]
  for(const flow of flows) assert.ok(resolvePreparedGuide(flow,null,now),`${topic.id}: ${JSON.stringify(flow.details)}`)
 }
})
test('warning guide requires matching colour, shape and steady state; unknown stops identification',async()=>{
 const {clarificationFor,continueQuestion,startQuestion}=await import('../src/conversation.js')
 const base={...startQuestion('계기판에 낯선 경고등이 켜졌어',1),category:'warning',topicId:'light',preparedEligible:true}
 let current=base
 for(const reply of ['빨간색','주전자 모양','계속 켜져 있어요']){
  const prompt=clarificationFor(current)
  current=continueQuestion({...current,awaiting:prompt.field},reply)
 }
 assert.equal(clarificationFor(current),null)
 assert.match(resolvePreparedGuide(current,car,now).title,/오일 압력/)
 assert.equal(resolvePreparedGuide({...current,details:{...current.details,color:'노란색'}},car,now),null)
 assert.equal(resolvePreparedGuide({...current,details:{...current.details,blink:'깜빡임'}},car,now),null)
 const unknown=continueQuestion({...base,awaiting:'color'},'잘 모르겠어요')
 assert.equal(clarificationFor(unknown),null)
 assert.equal(resolvePreparedGuide(unknown,car,now).needs_review,true)
 const ambiguous={...base,details:{color:'빨간색',shape:'느낌표 모양'}}
 assert.equal(clarificationFor(ambiguous),null)
 assert.equal(resolvePreparedGuide(ambiguous,car,now).status,'need_review')
 const fuel={...startQuestion('주유등이 켜졌어',1),category:'warning',topicId:'fuel',preparedEligible:true}
 assert.equal(clarificationFor(fuel),null)
 assert.ok(resolvePreparedGuide(fuel,car,now))
 assert.equal(clarificationFor({...fuel,preparedEligible:false}).field,'range')
})

test('all controls menu choices on both cars finish locally without any network request', async () => {
 const {guidanceCategories} = await import('../src/guidance.js')
 const {clarificationFor, startQuestion} = await import('../src/conversation.js')
 const saved={localStorage:globalThis.localStorage,window:globalThis.window,fetch:globalThis.fetch}
 globalThis.localStorage={getItem:()=>null}
 globalThis.window={location:{origin:'http://localhost'}}
 let calls=0
 globalThis.fetch=async()=>{calls++;throw new Error('Menu guidance must not need the network')}
 try {
  let state
  await renderToString(createSSRApp({setup(){state=useChageun();return()=>h('div')}}))
  for (const vehicle of [car,{id:2,manufacturer:'현대',model:'더 뉴 아반떼',model_year:2026,powertrain:'G1.6'}]) {
   state.vehicles.value=[vehicle];state.chatVehicleId.value=vehicle.id
   for(const topic of guidanceCategories.find(c=>c.id==='controls').topics) {
    const options={newQuestion:true,preparedMenu:true,category:'controls',topicId:topic.id,intent:'controls'}
    const prompt=clarificationFor({...startQuestion(topic.question,vehicle.id),...options,preparedEligible:true})
    for(const reply of prompt?.suggestions || [null]) {
     await state.ask(topic.question,options)
     if(reply) await state.replyTo(state.currentMessage.value,reply)
     assert.equal(state.currentMessage.value.answerMode,'prepared',`${vehicle.model} ${topic.id} ${reply}`)
     assert.ok(state.currentMessage.value.answer.length>30)
     assert.ok(state.currentMessage.value.sources.length)
     assert.equal(state.asking.value,false)
    }
   }
  }
  assert.equal(calls,0)
 } finally {Object.assign(globalThis,saved)}
})
