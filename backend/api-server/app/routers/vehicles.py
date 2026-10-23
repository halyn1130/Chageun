"""[목업] 내 차 API — 고정 데이터를 돌려준다. DB 연동 시 교체."""
from datetime import date

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/vehicles", tags=["내 차 (목업)"])

ITEM_LABELS = {
    "engine_oil": "엔진오일", "air_filter": "에어필터", "tire": "타이어", "brake_pad": "브레이크패드",
    "coolant": "냉각수", "battery": "배터리", "wiper": "와이퍼", "other": "기타",
}

MOCK_VEHICLE = {
    "id": 3, "nickname": "내 K5", "manufacturer": "기아", "model": "K5",
    "model_year": "2024", "powertrain": "가솔린 1.6T", "mileage_km": 36200, "is_primary": True,
}

MOCK_MAINTENANCE = [
    {"id": 11, "item": "engine_oil", "item_label": "엔진오일", "performed_at": "2024-01-10", "mileage_km": 35000, "memo": None},
    {"id": 10, "item": "air_filter", "item_label": "에어필터", "performed_at": "2023-07-12", "mileage_km": 28400, "memo": None},
    {"id": 9, "item": "tire", "item_label": "타이어", "performed_at": "2023-01-05", "mileage_km": 22100, "memo": None},
]


class VehicleCreate(BaseModel):
    manufacturer: str
    model: str
    model_year: str
    powertrain: str
    nickname: str | None = None
    mileage_km: int | None = None


class MaintenanceCreate(BaseModel):
    item: str
    performed_at: date
    mileage_km: int
    memo: str | None = None


@router.get("/catalog", summary="등록 가능한 차종")
def catalog():
    return [
        {"manufacturer": "기아", "model": "K5", "model_year": "2024", "powertrain": "가솔린 1.6T"},
        {"manufacturer": "현대", "model": "디 올 뉴 아반떼", "model_year": "2024", "powertrain": "가솔린 1.6"},
    ]


@router.get("", summary="내 차량 목록")
def list_vehicles(user: CurrentUser = Depends(get_current_user)):
    return [MOCK_VEHICLE]


@router.post("", status_code=201, summary="차량 등록")
def create_vehicle(body: VehicleCreate, user: CurrentUser = Depends(get_current_user)):
    return {"id": 4, **body.model_dump(), "is_primary": False}


@router.delete("/{vehicle_id}", status_code=204, summary="차량 삭제")
def delete_vehicle(vehicle_id: int, user: CurrentUser = Depends(get_current_user)):
    return Response(status_code=204)


@router.get("/{vehicle_id}/maintenance", summary="정비 이력 (최신순)")
def list_maintenance(vehicle_id: int, item: str | None = None,
                     user: CurrentUser = Depends(get_current_user)):
    return [r for r in MOCK_MAINTENANCE if item is None or r["item"] == item]


@router.post("/{vehicle_id}/maintenance", status_code=201, summary="정비 기록 추가")
def create_maintenance(vehicle_id: int, body: MaintenanceCreate,
                       user: CurrentUser = Depends(get_current_user)):
    return {"id": 12, **body.model_dump(), "item_label": ITEM_LABELS.get(body.item, "기타")}
