"""내 차 API — 차량(vehicles)과 정비 이력(maintenance_records)."""
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.db import get_db

router = APIRouter(prefix="/vehicles", tags=["내 차"])

# 등록 가능한 차종 = 설명서가 등록된 차종. ai_data/data/registry.json의 설명서 값과 글자까지 같아야
# RAG가 이 값으로 설명서를 걸러 검색한다 (다르면 "설명서가 아직 등록되지 않았어요")
CATALOG = [
    {"manufacturer": "기아", "model": "K5", "model_year": "2026", "powertrain": "G2.0"},
    {"manufacturer": "현대", "model": "디 올 뉴 아반떼", "model_year": "2026", "powertrain": "G1.6"},
]

VEHICLE_COLUMNS = "id, nickname, manufacturer, model, model_year, powertrain, mileage_km, is_primary"

# 정비 항목. 화면용 이름(item_label)은 DB에 저장하지 않고 응답할 때 붙인다
ITEM_LABELS = {
    "engine_oil": "엔진오일", "air_filter": "에어필터", "tire": "타이어", "brake_pad": "브레이크패드",
    "coolant": "냉각수", "battery": "배터리", "wiper": "와이퍼", "other": "기타",
}
MaintenanceItem = Literal["engine_oil", "air_filter", "tire", "brake_pad", "coolant", "battery", "wiper", "other"]

MAINTENANCE_COLUMNS = "id, item, performed_at, mileage_km, memo"
KST = ZoneInfo("Asia/Seoul")


class VehicleCreate(BaseModel):
    manufacturer: str
    model: str
    model_year: str
    powertrain: str
    nickname: str | None = Field(None, max_length=50)
    mileage_km: int | None = Field(None, ge=0)

    # Swagger "Try it out"에 미리 채워지는 예시
    model_config = {"json_schema_extra": {"examples": [{
        "manufacturer": "기아", "model": "K5", "model_year": "2026", "powertrain": "G2.0",
        "nickname": "내 K5", "mileage_km": 36200,
    }]}}


class Vehicle(BaseModel):
    id: int
    nickname: str | None
    manufacturer: str
    model: str
    model_year: str
    powertrain: str
    mileage_km: int | None
    is_primary: bool   # DB에는 0/1로 저장돼 있어 응답할 때 true/false로 바꾼다


def get_owned_vehicle(db, user: CurrentUser, vehicle_id: int) -> dict:
    """내 차량이면 돌려주고, 없거나 남의 차량이면 404."""
    with db.cursor() as cur:
        cur.execute(f"SELECT {VEHICLE_COLUMNS} FROM vehicles WHERE id = %s AND user_id = %s",
                    (vehicle_id, user.id))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "차량을 찾을 수 없어요.")
    return row


class MaintenanceCreate(BaseModel):
    item: MaintenanceItem
    performed_at: date
    mileage_km: int = Field(ge=0)
    memo: str | None = Field(None, max_length=255)

    model_config = {"json_schema_extra": {"examples": [{
        "item": "engine_oil", "performed_at": "2024-01-10", "mileage_km": 35000, "memo": "합성유",
    }]}}


class Maintenance(BaseModel):
    id: int
    item: str
    item_label: str
    performed_at: date
    mileage_km: int | None
    memo: str | None


def with_label(row: dict) -> dict:
    return {**row, "item_label": ITEM_LABELS[row["item"]]}


def latest_maintenance(db, vehicle_id: int | None) -> dict:
    """RAG에 보낼 정비 기록: 항목별 가장 최근 기록 1건씩 (내부 API의 maintenance 형식)."""
    if vehicle_id is None:
        return {"lookup_status": "no_vehicle", "items": [], "records": []}
    with db.cursor() as cur:
        cur.execute("SELECT item, performed_at, mileage_km FROM maintenance_records"
                    " WHERE vehicle_id = %s ORDER BY performed_at DESC, id DESC", (vehicle_id,))
        rows = cur.fetchall()
    latest = {}
    for r in rows:   # 최신순이라 항목별로 처음 나온 것이 가장 최근 기록
        latest.setdefault(r["item"], {**r, "performed_at": r["performed_at"].isoformat()})
    return {"lookup_status": "ok" if latest else "empty", "items": list(latest), "records": list(latest.values())}


@router.get("/catalog", summary="등록 가능한 차종")
def catalog():
    return CATALOG


@router.get("", response_model=list[Vehicle], summary="내 차량 목록")
def list_vehicles(user: CurrentUser = Depends(get_current_user), db=Depends(get_db)):
    # 기본 차량을 맨 앞에, 나머지는 등록한 순서대로
    with db.cursor() as cur:
        cur.execute(f"SELECT {VEHICLE_COLUMNS} FROM vehicles WHERE user_id = %s ORDER BY is_primary DESC, id",
                    (user.id,))
        return cur.fetchall()


@router.post("", status_code=201, response_model=Vehicle, summary="차량 등록")
def create_vehicle(body: VehicleCreate, user: CurrentUser = Depends(get_current_user), db=Depends(get_db)):
    spec = {k: body.model_dump()[k] for k in ("manufacturer", "model", "model_year", "powertrain")}
    if spec not in CATALOG:
        raise HTTPException(422, "등록할 수 없는 차종이에요. 차종 목록에서 골라 주세요.")

    with db.cursor() as cur:
        # 처음 등록하는 차량이면 기본 차량으로 지정
        cur.execute("SELECT COUNT(*) AS n FROM vehicles WHERE user_id = %s", (user.id,))
        is_primary = cur.fetchone()["n"] == 0
        cur.execute(
            "INSERT INTO vehicles (user_id, nickname, manufacturer, model, model_year, powertrain, mileage_km, is_primary)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (user.id, body.nickname, body.manufacturer, body.model, body.model_year, body.powertrain,
             body.mileage_km, is_primary),
        )
        vehicle_id = cur.lastrowid
    return get_owned_vehicle(db, user, vehicle_id)


@router.delete("/{vehicle_id}", status_code=204, summary="차량 삭제")
def delete_vehicle(vehicle_id: int, user: CurrentUser = Depends(get_current_user), db=Depends(get_db)):
    vehicle = get_owned_vehicle(db, user, vehicle_id)
    with db.cursor() as cur:
        # 정비 기록은 FK(ON DELETE CASCADE)로 함께 지워진다
        cur.execute("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        # 기본 차량을 지웠으면 남은 차량 중 가장 먼저 등록한 것을 기본으로
        if vehicle["is_primary"]:
            cur.execute("UPDATE vehicles SET is_primary = TRUE WHERE user_id = %s ORDER BY id LIMIT 1", (user.id,))
    return Response(status_code=204)


# ---- 정비 이력 ----

@router.get("/{vehicle_id}/maintenance", response_model=list[Maintenance], summary="정비 이력 (최신순)")
def list_maintenance(vehicle_id: int,
                     item: MaintenanceItem | None = Query(None, openapi_examples={"엔진오일": {"value": "engine_oil"}}),
                     user: CurrentUser = Depends(get_current_user), db=Depends(get_db)):
    get_owned_vehicle(db, user, vehicle_id)
    sql = f"SELECT {MAINTENANCE_COLUMNS} FROM maintenance_records WHERE vehicle_id = %s"
    args = [vehicle_id]
    if item is not None:
        sql += " AND item = %s"
        args.append(item)
    with db.cursor() as cur:
        cur.execute(sql + " ORDER BY performed_at DESC, id DESC", args)
        return [with_label(r) for r in cur.fetchall()]


@router.post("/{vehicle_id}/maintenance", status_code=201, response_model=Maintenance, summary="정비 기록 추가")
def create_maintenance(vehicle_id: int, body: MaintenanceCreate,
                       user: CurrentUser = Depends(get_current_user), db=Depends(get_db)):
    get_owned_vehicle(db, user, vehicle_id)
    if body.performed_at > datetime.now(KST).date():
        raise HTTPException(422, "정비 날짜는 오늘 이후로 입력할 수 없어요.")

    with db.cursor() as cur:
        cur.execute("INSERT INTO maintenance_records (vehicle_id, item, performed_at, mileage_km, memo)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    (vehicle_id, body.item, body.performed_at, body.mileage_km, body.memo))
        record_id = cur.lastrowid
        # 정비 당시 주행거리가 차량의 현재 주행거리보다 크면 차량 주행거리도 올린다
        cur.execute("UPDATE vehicles SET mileage_km = %s WHERE id = %s AND (mileage_km IS NULL OR mileage_km < %s)",
                    (body.mileage_km, vehicle_id, body.mileage_km))
        cur.execute(f"SELECT {MAINTENANCE_COLUMNS} FROM maintenance_records WHERE id = %s", (record_id,))
        return with_label(cur.fetchone())
