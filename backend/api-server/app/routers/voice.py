"""[목업] 음성 API — 고정 데이터를 돌려준다. Whisper·OpenAI TTS 연동 시 교체."""
import io
import wave

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(tags=["음성 (목업)"])


class TTSRequest(BaseModel):
    text: str


@router.post("/voice/stt", summary="녹음 → 텍스트")
async def stt(file: UploadFile = File(...)):
    return {"text": "가는 길에 주차장 찾아줘"}


@router.post("/voice/tts", summary="텍스트 → 음성")
def tts(body: TTSRequest):
    return {"audio_url": "/audio/mock.wav"}


@router.get("/audio/{file}", summary="음성 파일 재생")
def audio(file: str):
    # 목업: 1초짜리 무음 wav. 실제 구현에서는 TTS로 만든 mp3를 돌려준다
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000)
    return Response(buf.getvalue(), media_type="audio/wav")
