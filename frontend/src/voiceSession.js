// Browser adapters are injectable so tests never activate a real microphone.
export function createVoiceSession({ platform, onChange, onQuestion }) {
  const Recognition =
    platform.SpeechRecognition || platform.webkitSpeechRecognition
  let epoch = 0
  let active = false
  let recognition = null
  let state = {
    phase: 'idle',
    active: false,
    transcript: '',
    error: '',
    supported: Boolean(Recognition),
  }
  function update(values) {
    state = { ...state, ...values }
    onChange({ ...state })
  }
  function stop() {
    epoch += 1
    active = false
    const previous = recognition
    recognition = null
    if (previous) {
      previous.onend = null
      previous.onresult = null
      previous.onerror = null
      previous.onstart = null
      previous.abort()
    }
    platform.speechSynthesis?.cancel()
    update({ phase: 'idle', active: false, transcript: '', error: '' })
  }
  function fail(message) {
    stop()
    update({ phase: 'error', error: message })
  }
  function speak(text, token, resume) {
    if (token !== epoch) return
    if (
      !text ||
      !platform.speechSynthesis ||
      !platform.SpeechSynthesisUtterance
    ) {
      if (resume && active) listen(token)
      else update({ phase: 'idle' })
      return
    }
    const utterance = new platform.SpeechSynthesisUtterance(text)
    utterance.lang = 'ko-KR'
    utterance.rate = 1.03
    const voice = platform.speechSynthesis
      .getVoices()
      .find((item) => item.lang.startsWith('ko'))
    if (voice) utterance.voice = voice
    const done = () => {
      if (token !== epoch) return
      if (resume && active) listen(token)
      else update({ phase: 'idle' })
    }
    utterance.onend = done
    utterance.onerror = () => {
      if (token === epoch)
        fail('답변 음성을 재생하지 못했어요. 화면에서 답변을 확인해 주세요.')
    }
    update({ phase: 'speaking', transcript: '' })
    platform.speechSynthesis.speak(utterance)
  }
  function listen(token) {
    if (!active || token !== epoch) return
    const current = new Recognition()
    recognition = current
    current.lang = 'ko-KR'
    current.interimResults = true
    current.continuous = false
    let handled = false
    update({ phase: 'connecting', transcript: '', error: '' })
    current.onstart = () => {
      if (token === epoch && !handled) update({ phase: 'listening' })
    }
    current.onresult = async (event) => {
      if (token !== epoch || handled) return
      let transcript = ''
      let final = ''
      for (let i = 0; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript
        if (event.results[i].isFinal) final += event.results[i][0].transcript
      }
      update({ transcript })
      if (!final.trim()) return
      handled = true
      recognition = null
      current.abort()
      update({ phase: 'thinking', transcript: final.trim() })
      try {
        const answer = await onQuestion(final.trim())
        if (token !== epoch || !active) return
        speak(answer, token, true)
      } catch {
        if (token === epoch) fail('답변을 가져오지 못했어요. 다시 말해 주세요.')
      }
    }
    current.onerror = (event) => {
      if (token !== epoch || handled) return
      handled = true
      const errors = {
        'not-allowed':
          '마이크 권한이 꺼져 있어요. 브라우저에서 허용한 뒤 다시 눌러 주세요.',
        'service-not-allowed': '이 브라우저에서 음성 인식을 사용할 수 없어요.',
        'audio-capture': '연결된 마이크를 찾지 못했어요.',
        'no-speech': '말소리를 듣지 못했어요. 다시 눌러 말해 주세요.',
        network: '음성 인식 연결이 끊겼어요. 인터넷 연결을 확인해 주세요.',
      }
      fail(errors[event.error] || '음성 인식이 멈췄어요. 다시 눌러 주세요.')
    }
    current.onend = () => {
      if (token !== epoch || handled || !active) return
      handled = true
      fail('말소리를 듣지 못했어요. 다시 눌러 말해 주세요.')
    }
    try {
      current.start()
    } catch {
      fail('마이크를 시작하지 못했어요. 다시 시도해 주세요.')
    }
  }
  function start() {
    stop()
    if (!Recognition) {
      fail(
        '이 브라우저는 음성 인식을 지원하지 않아요. Chrome에서 열거나 글로 물어보세요.',
      )
      return
    }
    active = true
    update({ active: true })
    listen(epoch)
  }
  function read(text) {
    stop()
    speak(text, epoch, false)
  }
  return { start, stop, read, getState: () => ({ ...state }) }
}
