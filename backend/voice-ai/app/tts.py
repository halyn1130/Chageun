"""Selectable TTS providers. Secrets stay on the server; generated audio is not saved."""
import os
from dataclasses import dataclass
import httpx

TIMEOUT = httpx.Timeout(20.0)
DEFAULT_TYPECAST_VOICE = "tc_672c5f5ce59fac2a48faeaee"  # official ssfm-v30 SDK example


SELECTABLE_VOICES = {'tc_6a7446c19f2d7dfed990a900', 'tc_658d1bc867f8ac8fa3cbbeec', 'tc_685cdfad4027aeec7d097a28', 'tc_5c547544fcfee90007fed455', 'tc_60126fbf8e097503c73ed8d6'}

class TtsError(Exception):
    pass


@dataclass(frozen=True)
class Audio:
    data: bytes
    media_type: str


def synthesize(text: str, voice_id: str | None = None) -> Audio:
    if voice_id is not None and voice_id not in SELECTABLE_VOICES:
        raise TtsError("Unsupported voice_id")
    provider = os.getenv("TTS_PROVIDER", "openai").strip().lower()
    if provider == "typecast":
        key = os.getenv("TYPECAST_API_KEY", "").strip()
        if not key:
            raise TtsError("TYPECAST_API_KEY is not configured")
        url = "https://api.typecast.ai/v1/text-to-speech"
        headers = {"X-API-KEY": key}
        body = {
            "text": text,
            "model": "ssfm-v30",
            "voice_id": voice_id or os.getenv("TYPECAST_VOICE_ID", "").strip() or DEFAULT_TYPECAST_VOICE,
            "language": "kor",
            "prompt": {"emotion_type": "smart"},
            "output": {"audio_format": "wav"},
        }
        mime = "audio/wav"
    elif provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise TtsError("OPENAI_API_KEY is not configured")
        url = "https://api.openai.com/v1/audio/speech"
        headers = {"Authorization": f"Bearer {key}"}
        body = {"model": "tts-1", "voice": "nova", "input": text, "response_format": "mp3"}
        mime = "audio/mpeg"
    else:
        raise TtsError("Unsupported TTS_PROVIDER")
    try:
        res = httpx.post(url, headers=headers, json=body, timeout=TIMEOUT)
        res.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Do not log upstream response bodies: they may echo input text or credentials.
        raise TtsError(f"{provider}: HTTP {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise TtsError(f"{provider}: {type(e).__name__}") from e
    if not res.content or not res.headers.get("content-type", "").lower().startswith("audio/"):
        raise TtsError(f"{provider}: invalid audio response")
    return Audio(res.content, mime)
