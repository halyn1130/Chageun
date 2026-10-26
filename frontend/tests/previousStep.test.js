import test from 'node:test'
import assert from 'node:assert/strict'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { useChageun } from '../src/composables/useChageun.js'

test('previous step restores a usable prompt and can be revisited after changing the answer', async () => {
 const oldStorage=globalThis.localStorage, oldWindow=globalThis.window, oldFetch=globalThis.fetch
 globalThis.localStorage={getItem:()=>null}
 globalThis.window={location:{origin:'http://localhost'}}
 globalThis.fetch=async()=>new Response(JSON.stringify({status:'answered',answer:'안내 결과',sources:[]}),{status:200})
 try {
  let state
  await renderToString(createSSRApp({setup(){state=useChageun();return ()=>h('div')}}))
  state.screen.value='diagnostics'
  await state.ask('전조등 상향등은 어떻게 켜?', {newQuestion:true})
  let prior
  for(let i=0;i<8 && state.currentMessage.value.followup_question;i++) {
   prior=JSON.parse(JSON.stringify(state.currentMessage.value))
   await state.replyTo(state.currentMessage.value,'모르겠어요')
  }
  assert.ok(prior)
  assert.equal(state.currentMessage.value.followup_question,undefined)
  assert.equal(state.canReturnToPreviousStep.value,true)
  state.returnToPreviousStep()
  assert.equal(state.currentMessage.value.followup_question,prior.followup_question)
  assert.equal(state.activePromptId.value,state.currentMessage.value.id)
  await state.replyTo(state.currentMessage.value,'모르겠어요')
  assert.equal(state.currentMessage.value.followup_question,undefined)
  state.returnToPreviousStep()
  assert.equal(state.currentMessage.value.followup_question,prior.followup_question)
  state.cancelQuestion()
  assert.equal(state.canReturnToPreviousStep.value,false)
 } finally {
  globalThis.localStorage=oldStorage;globalThis.window=oldWindow;globalThis.fetch=oldFetch
 }
})
