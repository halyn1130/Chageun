"""대화 API — 프론트의 질문에 차량 · 정비 기록 · 이전 대화를 채워 rag 서버로 보내고, 답을 저장해 돌려준다.

rag 서버는 상태가 없고 회원 DB를 보지 않는다. 사용자에게 딸린 정보는 모두 여기서 확인해 넘긴다 (내부 API).
로그에는 request_id · 결과 상태 · 처리 시간만 남기고 질문 원문은 남기지 않는다.
"""
import logging
import os
import time
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.auth import CurrentUser, bearer, get_current_user
from app.conversations import load_history, new_conversation_id, save_turn
from app.db import get_db
from app.routers.vehicles import VEHICLE_COLUMNS, get_owned_vehicle, latest_maintenance

router = APIRouter(tags=["대화"])
log = logging.getLogger("uvicorn.error")

RAG_URL = os.environ["RAG_URL"]
TIMEOUT = httpx.Timeout(35.0)   # rag 서버가 30초에 스스로 끊으므로 그보다 조금 길게
UNAVAILABLE = "지금은 답변을 만들 수 없어요. 잠시 후 다시 시도해 주세요."
RAG_VEHICLE_FIELDS = ("id", "manufacturer", "model", "model_year", "powertrain", "mileage_km")


class LatLng(BaseModel):
    lat: float
    lng: float


class VehicleContext(BaseModel):
    manufacturer: str
    model: str
    model_year: str
    powertrain: str
    mileage_km: int | None = Field(default=None, ge=0)


class MaintenanceContext(BaseModel):
    item: str
    performed_at: str
    mileage_km: int = Field(ge=0)


class FollowupContext(BaseModel):
    question: str
    answer: str = Field(max_length=500)


class GuidanceContext(BaseModel):
    """UI context; persisted vehicle ownership and records remain server-owned."""
    entry_point: str = "conversation"
    topic: str | None = None
    maintenance_item: str | None = None
    original_question: str = Field(max_length=500)
    vehicle: VehicleContext | None = None
    maintenance_status: str = "unavailable"
    maintenance_records: list[MaintenanceContext] = Field(default_factory=list)
    collected_answers: dict[str, str] = Field(default_factory=dict)
    followups: list[FollowupContext] = Field(default_factory=list)


class Destination(LatLng):
    name: str


class RagRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    vehicle_id: int | None = None          # 생략하면 기본 차량
    conversation_id: str | None = Field(None, max_length=40)   # 이어지는 질문이면 이전 응답의 값
    location: LatLng | None = None
    context: GuidanceContext | None = None
    destination: Destination | None = None

    model_config = {"json_schema_extra": {"examples": [{"question": "엔진오일 교환 주기는?"}]}}


def pick_vehicle(db, user: CurrentUser, vehicle_id: int | None) -> dict | None:
    """요청한 내 차량(남의 차면 404). 생략하면 기본 차량, 차가 없으면 None."""
    if vehicle_id is not None:
        return get_owned_vehicle(db, user, vehicle_id)
    with db.cursor() as cur:
        cur.execute(f"SELECT {VEHICLE_COLUMNS} FROM vehicles WHERE user_id = %s ORDER BY is_primary DESC, id LIMIT 1",
                    (user.id,))
        return cur.fetchone()


@router.post("/rag-query", summary="질문 → 답변 + 출처")
def rag_query(req: RagRequest, user: CurrentUser = Depends(get_current_user),
              cred: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)):
    # Explicitly choosing no car in the UI must not fall back to a stored primary.
    no_vehicle = req.context is not None and req.context.vehicle is None and req.vehicle_id is None
    vehicle = None if no_vehicle else pick_vehicle(db, user, req.vehicle_id)
    conversation_id = req.conversation_id or new_conversation_id()
    request_id = str(uuid.uuid4())
    body = {
        "request_id": request_id,
        "conversation_id": conversation_id,
        "question": req.question,
        "vehicle": {k: vehicle[k] for k in RAG_VEHICLE_FIELDS} if vehicle else None,
        "maintenance": latest_maintenance(db, vehicle["id"] if vehicle else None),
        "history": load_history(db, user, conversation_id) if req.conversation_id else [],
        "location": req.location.model_dump() if req.location else None,
        "destination": req.destination.model_dump() if req.destination else None,
    }

    t0 = time.perf_counter()
    try:
        res = httpx.post(f"{RAG_URL}/rag-query", json=body, timeout=TIMEOUT,
                         headers={"Authorization": f"Bearer {cred.credentials}"})
    except httpx.HTTPError as e:   # rag 서버가 꺼져 있거나 응답이 없음
        log.warning("RAG 연결 실패 request_id=%s: %s", request_id, type(e).__name__)
        raise HTTPException(503, UNAVAILABLE)
    latency = (time.perf_counter() - t0) * 1000

    if res.status_code != 200:
        # rag의 401(토큰 만료)과 503(준비 안 됨·시간 초과)은 사용자에게 그대로 안내한다.
        # 그 밖의 오류(422 등)는 api-server가 보낸 형식 문제라 사용자 잘못이 아니므로 503으로 감춘다
        is_json = res.headers.get("content-type", "").startswith("application/json")
        detail = res.json().get("detail", UNAVAILABLE) if is_json else UNAVAILABLE
        log.warning("RAG 오류 request_id=%s: HTTP %s %s", request_id, res.status_code, detail)
        if res.status_code == 401:
            raise HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})
        raise HTTPException(503, detail if res.status_code == 503 else UNAVAILABLE)

    result = res.json()
    save_turn(db, user, conversation_id, req.question, result["answer"])
    log.info("RAG request_id=%s user=%s status=%s latency=%dms", request_id, user.id, result["status"], latency)
    return result
