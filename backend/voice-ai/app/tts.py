"""TTS — OpenAI TTS(nova)로 문장을 mp3로 만든다.

교수님 예제(voice-ai_code/app/services/tts_service.py) 기반. 바뀐 점:
- 파일로 저장하지 않고 mp3 바이트를 그대로 돌려준다 (고정 파일명이라 동시 요청이 서로 덮어쓰던 문제 제거)
- 시간 제한 15초, 실패는 TtsError 하나로 모아 503으로 응답하게 한다
"""
import os

import httpx

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TIMEOUT = httpx.Timeout(15.0)


class TtsError(Exception):
    pass


def synthesize(text: str) -> bytes:
    try:
        res = httpx.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": "tts-1", "voice": "nova", "input": text, "response_format": "mp3"},
            timeout=TIMEOUT,
        )
        res.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise TtsError(f"HTTP {e.response.status_code} {e.response.text[:200]}") from e
    except httpx.HTTPError as e:
        raise TtsError(type(e).__name__) from e
    return res.content
