"""[목업 · 임시] 대화 API. RAG 서버 구성이 정해지면 이동하거나 삭제한다.
질문에 들어간 단어에 따라 status별 응답 예시를 돌려준다.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import get_current_user

router = APIRouter(tags=["대화 (목업 · 임시)"], dependencies=[Depends(get_current_user)])


class LatLng(BaseModel):
    lat: float
    lng: float


class RagRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    vehicle_id: int | None = None
    conversation_id: str | None = None
    location: LatLng | None = None

    # Swagger "Try it out"에 미리 채워지는 예시 (첫 질문이라 conversation_id 없음)
    model_config = {"json_schema_extra": {"examples": [{
        "question": "주변에 주차장 찾아줘",
        "location": {"lat": 35.5384, "lng": 129.3114},
    }]}}


def reply(req: RagRequest, status: str, answer: str, speech: str, sources=None,
          action=None, needs_review=False, handoff=False):
    return {
        "status": status, "answer": answer, "speech_text": speech, "sources": sources or [],
        "needs_review": needs_review, "handoff": handoff, "action": action,
        "conversation_id": req.conversation_id or "c_mock",
    }


@router.post("/rag-query", summary="질문 → 답변 + 출처")
def rag_query(req: RagRequest):
    q = req.question

    if "차선" in q:
        return reply(req, "out_of_scope", "주행 중 실시간 판단은 도와드릴 수 없어요. 주변 상황을 직접 확인해 주세요.",
                     "실시간 판단은 도와드릴 수 없어요.")
    if any(w in q for w in ("주차장", "주유소", "카페")):
        if req.location is None:
            return reply(req, "need_location", "주변을 찾으려면 현재 위치가 필요해요.", "위치 권한을 허용해 주세요.")
        category = "parking" if "주차장" in q else "gas_station" if "주유소" in q else "cafe"
        return reply(req, "tool_result", "주변 장소를 찾았어요.", "경로 주변 주차장을 찾았어요.",
                     action={"type": "show_places", "category": category})
    if "내 차" in q:
        return reply(req, "tool_result", "정비 이력을 열어 드릴게요.", "마지막 교환 시기를 알려드릴게요.",
                     action={"type": "open_my_car", "vehicle_id": req.vehicle_id or 3, "item": "engine_oil"})
    if any(w in q for w in ("K5", "아반떼", "엔진오일", "경고등")):
        if req.vehicle_id is None:
            return reply(req, "need_vehicle", "어떤 차량 기준으로 알려드릴까요? 차량을 선택하거나 등록해 주세요.",
                         "차량을 먼저 선택해 주세요.")
        return reply(req, "answered", "설명서 기준 엔진오일 교환 주기는 (목업 답변)입니다.",
                     "설명서 기준 교환 주기를 알려드릴게요.",
                     sources=[{"title": "2024 K5 취급설명서", "page": "p.512", "url": "https://example.com/k5"}])
    if any(w in q for w in ("우회전", "주정차", "보호구역", "교차로", "좌회전")):
        return reply(req, "answered", "도로교통법에 따르면 (목업 답변)입니다.", "도로교통법 기준으로 알려드릴게요.",
                     sources=[{"title": "도로교통법", "page": "제25조", "url": "https://www.law.go.kr"}])
    return reply(req, "not_found", "관련 내용을 찾을 수 없어요.", "찾을 수 없어요.", handoff=True)
