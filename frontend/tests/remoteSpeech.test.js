import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createRemoteSpeech } from '../src/remoteSpeech.js'

function setup(fetcher) {
  const players = [], revoked = [], requests = [], ended = [], errors = []
  class Audio {
    constructor(url) { this.url = url; players.push(this) }
    play() { return Promise.resolve() }
    pause() { this.paused = true }
    removeAttribute() {}
    load() {}
  }
  const platform = { Audio, URL: { createObjectURL: () => 'blob:test', revokeObjectURL: url => revoked.push(url) },
    fetch: async (...args) => { requests.push(args); return fetcher ? fetcher(...args) : new Response(new Blob(['audio']), { headers: { 'content-type': 'audio/wav' } }) } }
  const remote = createRemoteSpeech({ platform, getToken: () => 'test-jwt' })
  const callbacks = { onEnd: () => ended.push(true), onError: message => errors.push(message) }
  return { remote, platform, players, revoked, requests, ended, errors, callbacks }
}

test('authenticated WAV plays and revokes its URL when finished', async () => {
  const x = setup()
  await x.remote.speak('안내', x.callbacks)
  assert.equal(x.requests[0][0], '/voice/tts')
  assert.equal(x.requests[0][1].headers.Authorization, 'Bearer test-jwt')
  assert.deepEqual(JSON.parse(x.requests[0][1].body), { text: '안내' })
  assert.equal(x.ended.length, 0)
  x.players[0].onended()
  assert.equal(x.ended.length, 1)
  assert.deepEqual(x.revoked, ['blob:test'])
})

test('stop aborts pending synthesis and ignores a late audio response', async () => {
  let resolve
  const x = setup(() => new Promise(done => { resolve = done }))
  const pending = x.remote.speak('안내', x.callbacks)
  x.remote.stop()
  assert.equal(x.requests[0][1].signal.aborted, true)
  resolve(new Response('audio', { headers: { 'content-type': 'audio/wav' } }))
  await pending
  assert.equal(x.players.length, 0)
  assert.equal(x.ended.length, 0)
})

test('stop during playback clears callbacks and pauses audio', async () => {
  const x = setup()
  await x.remote.speak('안내', x.callbacks)
  const late = x.players[0].onended
  x.remote.stop()
  late()
  assert.equal(x.players[0].paused, true)
  assert.equal(x.players[0].onended, null)
  assert.equal(x.ended.length, 0)
  assert.deepEqual(x.revoked, ['blob:test'])
})

test('provider failures and invalid audio never play or resume recognition', async () => {
  for (const response of [new Response('{"detail":"음성 생성 실패"}', {status:503}), new Response('{}', {headers:{'content-type':'application/json'}})]) {
    const x = setup(() => response)
    await x.remote.speak('안내', x.callbacks)
    assert.equal(x.errors.length,1)
    assert.equal(x.players.length,0)
    assert.equal(x.ended.length,0)
  }
})

test('browser autoplay rejection is reported and releases audio', async () => {
  const x = setup()
  x.platform.Audio.prototype.play = () => Promise.reject(Object.assign(new Error('blocked'), {name:'NotAllowedError'}))
  await x.remote.speak('안내', x.callbacks)
  assert.match(x.errors[0], /답변 듣기/)
  assert.deepEqual(x.revoked, ['blob:test'])
})

test('saved account voice is resolved for each utterance', async () => {
 const x=setup(); let selected='voice-a'
 const remote=createRemoteSpeech({platform:x.platform,getToken:()=> 'test-jwt',getVoice:async()=>selected})
 await remote.speak('첫 안내',x.callbacks)
 assert.equal(JSON.parse(x.requests[0][1].body).voice_id,'voice-a')
 selected='voice-b'; await remote.speak('다음 안내',x.callbacks)
 assert.equal(JSON.parse(x.requests[1][1].body).voice_id,'voice-b')
 remote.stop()
})
test('closing while preference loads prevents stale synthesis', async () => {
 const x=setup();let resolve
 const remote=createRemoteSpeech({platform:x.platform,getToken:()=> 'test-jwt',getVoice:()=>new Promise(done=>resolve=done)})
 const pending=remote.speak('안내',x.callbacks);remote.stop();resolve('voice-a');await pending
 assert.equal(x.requests.length,0)
})
