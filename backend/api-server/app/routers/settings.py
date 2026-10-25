"""Account-owned voice preference; no caller-supplied user ID."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth import get_current_user
from app.db import get_db

router = APIRouter(prefix='/settings', tags=['개인 설정'])
VOICES = [{'name': '정민', 'voice_id': 'tc_658d1bc867f8ac8fa3cbbeec'}, {'name': '철훈', 'voice_id': 'tc_685cdfad4027aeec7d097a28'}, {'name': '은경', 'voice_id': 'tc_6a7446c19f2d7dfed990a900'}, {'name': '찬구', 'voice_id': 'tc_5c547544fcfee90007fed455'}, {'name': '스모크', 'voice_id': 'tc_60126fbf8e097503c73ed8d6'}]
class VoicePreference(BaseModel):
    voice_id: str | None = Field(default=None, max_length=64)

@router.get('/voices')
def voices(user=Depends(get_current_user)):
    return VOICES

@router.get('/voice')
def get_voice(user=Depends(get_current_user), db=Depends(get_db)):
    with db.cursor() as cur:
        cur.execute('SELECT voice_id FROM user_voice_settings WHERE user_id=%s', (user.id,))
        row = cur.fetchone()
    return {'voice_id': row['voice_id'] if row else None}

@router.put('/voice')
def save_voice(body: VoicePreference, user=Depends(get_current_user), db=Depends(get_db)):
    if body.voice_id is not None and body.voice_id not in {v['voice_id'] for v in VOICES}:
        raise HTTPException(422, '선택할 수 없는 목소리예요.')
    with db.cursor() as cur:
        cur.execute('INSERT INTO user_voice_settings(user_id,voice_id) VALUES(%s,%s) ON DUPLICATE KEY UPDATE voice_id=VALUES(voice_id)', (user.id,body.voice_id))
    return {'voice_id':body.voice_id}
