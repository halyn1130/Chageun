// Binary TTS from our authenticated voice server. No provider key reaches the browser.
export function createRemoteSpeech({ platform, getToken, endpoint = '/voice/tts', timeoutMs = 25000, getVoice = null }) {
  let generation = 0
  let controller = null
  let audio = null
  let objectUrl = null
  let timer = null
  function cleanup() {
    if (timer !== null) clearTimeout(timer)
    timer = null
    controller?.abort()
    controller = null
    if (audio) {
      audio.onended = null
      audio.onerror = null
      audio.pause()
      audio.removeAttribute?.('src')
      audio.load?.()
      audio = null
    }
    if (objectUrl) platform.URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
  function stop() {
    generation += 1
    cleanup()
  }
  async function speak(text, { onEnd, onError }) {
    stop()
    const current = generation
    try {
      const token = getToken()
      if (!token) throw new Error('음성 안내를 들으려면 먼저 로그인해 주세요.')
      controller = new AbortController()
      timer = setTimeout(() => {
        if (current !== generation) return
        stop()
        onError('음성 생성이 늦어지고 있어요. 다시 눌러 주세요.')
      }, timeoutMs)
      const voiceId = getVoice ? await getVoice(controller.signal) : undefined
      if (current !== generation) return
      const response = await platform.fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ text, ...(voiceId ? { voice_id: voiceId } : {}) }),
        signal: controller.signal,
      })
      if (current !== generation) return
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}))
        throw new Error(typeof detail.detail === 'string' ? detail.detail : '음성을 만들지 못했어요. 잠시 후 다시 시도해 주세요.')
      }
      if (!response.headers.get('content-type')?.startsWith('audio/')) throw new Error('올바른 음성 응답을 받지 못했어요.')
      const blob = await response.blob()
      if (current !== generation) return
      if (!blob.size) throw new Error('생성된 음성이 비어 있어요.')
      clearTimeout(timer)
      timer = null
      controller = null
      objectUrl = platform.URL.createObjectURL(blob)
      audio = new platform.Audio(objectUrl)
      audio.onended = () => {
        if (current !== generation) return
        cleanup()
        onEnd()
      }
      audio.onerror = () => {
        if (current !== generation) return
        stop()
        onError('답변 음성을 재생하지 못했어요. 다시 눌러 주세요.')
      }
      await audio.play()
    } catch (error) {
      if (current !== generation) return
      stop()
      onError(error.name === 'NotAllowedError'
        ? '브라우저가 재생을 막았어요. 답변 듣기 버튼을 눌러 주세요.'
        : error.message || '음성 서버에 연결할 수 없어요.')
    }
  }
  return { speak, stop }
}
