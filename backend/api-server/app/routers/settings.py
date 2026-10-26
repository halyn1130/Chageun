"""Account-owned voice preference; no caller-supplied user ID."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
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


class PersonalSettings(VoicePreference):
    display_name: str = Field(min_length=1, max_length=50)
    vehicle_id: int | None = Field(default=None, gt=0)

    @field_validator('display_name')
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('이름을 입력해 주세요.')
        return value


@router.get('/profile')
def get_profile(user=Depends(get_current_user), db=Depends(get_db)):
    with db.cursor() as cur:
        cur.execute('SELECT COALESCE(p.display_name,u.username) AS display_name FROM users u LEFT JOIN user_profiles p ON p.user_id=u.id WHERE u.id=%s', (user.id,))
        profile = cur.fetchone()
        cur.execute('SELECT id FROM vehicles WHERE user_id=%s ORDER BY is_primary DESC, id LIMIT 1', (user.id,))
        vehicle = cur.fetchone()
    return {'display_name': profile['display_name'] if profile else user.username,
            'vehicle_id': vehicle['id'] if vehicle else None}


@router.put('/profile')
def save_profile(body: PersonalSettings, user=Depends(get_current_user), db=Depends(get_db)):
    if body.voice_id is not None and body.voice_id not in {v['voice_id'] for v in VOICES}:
        raise HTTPException(422, '선택할 수 없는 목소리예요.')
    with db.cursor() as cur:
        # Serialize preference changes for this account; ownership is verified before any write.
        cur.execute('SELECT id FROM users WHERE id=%s FOR UPDATE', (user.id,))
        cur.fetchone()
        cur.execute('SELECT id FROM vehicles WHERE user_id=%s FOR UPDATE', (user.id,))
        owned = {row['id'] for row in cur.fetchall()}
        if body.vehicle_id not in owned and (body.vehicle_id is not None or owned):
            raise HTTPException(422, '등록한 차량 중에서 선택해 주세요.')
        cur.execute('INSERT INTO user_profiles(user_id,display_name) VALUES(%s,%s) ON DUPLICATE KEY UPDATE display_name=VALUES(display_name)', (user.id, body.display_name))
        if body.vehicle_id is not None:
            cur.execute('UPDATE vehicles SET is_primary=(id=%s) WHERE user_id=%s', (body.vehicle_id, user.id))
        cur.execute('INSERT INTO user_voice_settings(user_id,voice_id) VALUES(%s,%s) ON DUPLICATE KEY UPDATE voice_id=VALUES(voice_id)', (user.id, body.voice_id))
    return body.model_dump()
