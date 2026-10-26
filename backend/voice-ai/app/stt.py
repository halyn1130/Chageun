"""STT — 로컬 Whisper(faster-whisper)로 녹음을 텍스트로 바꾼다. 음성이 외부 API로 나가지 않는다.

교수님 예제(voice-ai_code/app/services/stt_service.py) 기반. 바뀐 점:
- 한국어로 고정(language="ko") — 언어 감지를 건너뛰어 더 빠르고 정확하다
- ffmpeg 변환 없이 webm을 바로 읽는다 (faster-whisper가 PyAV로 디코딩)
"""
import io
import os

from faster_whisper import WhisperModel

WHISPER_MODEL = os.environ["WHISPER_MODEL"]   # small · base 등. 느리면 base로
MAX_SECONDS = 60

# 앞서 나온 말처럼 넘겨 주는 문장. 도메인 단어(엔진오일·오토홀드·회전교차로)를 맞게 받아쓰도록 돕는다.
# 단어 목록으로 주면 결과에 쉼표가 끼어들어 문장으로 준다. 평가 문장과 겹치지 않게 쓴다.
# TTS로 만든 질문 8개 기준 정확히 받아쓴 수: 없음 5 → 단어 목록 6 → 이 문장 7
INITIAL_PROMPT = ("운전하면서 차근에게 물어봐요. 브레이크패드는 언제 갈아야 해? 편의점에 들렀다 가자. "
                  "엔진오일 경고등이 켜졌어. 오토홀드랑 회전교차로 규칙 알려줘.")

_model: WhisperModel | None = None


class AudioTooLong(Exception):
    pass


def load_model() -> None:
    """서버가 뜰 때 한 번 불러온다. 처음에는 모델을 내려받는다 (small 약 460MB, 볼륨에 저장)."""
    global _model
    _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def is_ready() -> bool:
    return _model is not None


def transcribe(audio: bytes) -> tuple[str, float]:
    """(인식된 문장, 음성 길이 초). 60초를 넘으면 AudioTooLong, 읽을 수 없는 파일이면 디코딩 예외."""
    segments, info = _model.transcribe(io.BytesIO(audio), language="ko", beam_size=5, vad_filter=True,
                                       initial_prompt=INITIAL_PROMPT)
    # segments는 제너레이터라 실제 인식은 아래에서 돈다. 길이는 그 전에 알 수 있어 먼저 거른다
    if info.duration > MAX_SECONDS:
        raise AudioTooLong
    return "".join(s.text for s in segments).strip(), info.duration
