"""차근 voice-ai — 브라우저가 직접 호출하는 음성 서버 (STT · TTS).

인증은 api-server와 같다: Authorization: Bearer <access_token>.
로그에는 request_id · 처리 시간 · 음성 길이만 남기고, 인식된 문장이나 읽을 문장은 남기지 않는다.
"""
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import av
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app import stt, tts
from app.auth import get_current_user

log = logging.getLogger("uvicorn.error")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 60초 webm은 1MB 안팎이라 넉넉하게

# 프론트(Vue)가 다른 포트에서 호출하므로 허용. 출처 목록은 compose가 넣어 주는 FRONTEND_ORIGINS(쉼표 구분)
FRONTEND_ORIGINS = [o.strip() for o in os.environ["FRONTEND_ORIGINS"].split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 첫 요청이 모델 로딩을 기다리지 않도록 서버가 뜰 때 미리 불러온다
    t0 = time.perf_counter()
    stt.load_model()
    log.info("Whisper 모델(%s) 준비 완료: %.1fs", stt.WHISPER_MODEL, time.perf_counter() - t0)
    yield


app = FastAPI(title="차근 voice-ai", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],   # 프론트가 TTS 응답 헤더의 request_id를 읽을 수 있게
)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    request_id: str | None = None
    voice_id: str | None = Field(default=None, max_length=64)

    model_config = {"json_schema_extra": {"examples": [{"text": "울산대공원까지 13분, 12시 41분 도착 예정이에요."}]}}


@app.get("/health")
def health():
    if not stt.is_ready():
        return JSONResponse({"status": "error", "whisper": "loading"}, status_code=503)
    return {"status": "ok", "whisper": stt.WHISPER_MODEL}


@app.post("/stt", summary="녹음 → 텍스트")
def speech_to_text(file: UploadFile = File(...), request_id: str | None = Form(None),
                   user=Depends(get_current_user)):
    rid = request_id or str(uuid.uuid4())
    audio = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not audio:
        raise HTTPException(422, "녹음 파일이 비어 있어요.")
    if len(audio) > MAX_UPLOAD_BYTES:
        raise HTTPException(422, "녹음 파일이 너무 커요. 60초 이내로 녹음해 주세요.")

    t0 = time.perf_counter()
    try:
        text, seconds = stt.transcribe(audio)
    except stt.AudioTooLong:
        raise HTTPException(422, "녹음은 60초 이내로 해 주세요.")
    except (av.error.FFmpegError, IndexError) as e:   # 손상되었거나 오디오가 아닌 파일 · 오디오 트랙 없음
        log.warning("STT 실패 request_id=%s: %s", rid, type(e).__name__)
        raise HTTPException(422, "녹음 파일을 읽을 수 없어요. 다시 녹음해 주세요.")
    log.info("STT request_id=%s user=%s audio=%.1fs latency=%dms",
             rid, user.id, seconds, (time.perf_counter() - t0) * 1000)
    return {"request_id": rid, "text": text}


@app.post("/tts", summary="텍스트 → 음성(Typecast WAV / OpenAI MP3)",
          responses={200: {"content": {"audio/wav": {}, "audio/mpeg": {}}, "description": "생성된 음성"}})
def text_to_speech(body: TTSRequest, user=Depends(get_current_user)):
    if body.voice_id is not None and body.voice_id not in tts.SELECTABLE_VOICES:
        raise HTTPException(422, "선택할 수 없는 목소리예요.")
    rid = body.request_id or str(uuid.uuid4())
    t0 = time.perf_counter()
    try:
        audio = tts.synthesize(body.text, voice_id=body.voice_id)
    except tts.TtsError as e:
        log.warning("TTS 실패 request_id=%s: %s", rid, e)
        raise HTTPException(503, "음성을 만들지 못했어요. 잠시 후 다시 시도해 주세요.")
    log.info("TTS request_id=%s user=%s chars=%d latency=%dms",
             rid, user.id, len(body.text), (time.perf_counter() - t0) * 1000)
    return Response(audio.data, media_type=audio.media_type, headers={"X-Request-ID": rid, "Cache-Control": "no-store"})
