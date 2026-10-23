"""지도 API — 카카오 로컬(장소 검색) · 오피넷(주유소 가격) · 카카오모빌리티(길찾기)를 대신 호출해 정리된 결과만 준다."""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pyproj import Transformer

from app.auth import get_current_user

router = APIRouter(tags=["지도"], dependencies=[Depends(get_current_user)])
log = logging.getLogger("uvicorn.error")

KAKAO_REST_KEY = os.environ["KAKAO_MAP_REST"]
OPINET_KEY = os.environ["OPINET"]
KAKAO_HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
TIMEOUT = httpx.Timeout(10.0)
KST = ZoneInfo("Asia/Seoul")

# 카카오 카테고리 그룹 코드
KAKAO_CATEGORY = {"parking": "PK6", "gas_station": "OL7", "cafe": "CE7"}
OPINET_MAX_RADIUS_M = 5000      # 오피넷 반경 검색 최대값
OPINET_DETAIL_LIMIT = 10        # 주소를 얻으려고 상세 조회할 주유소 수 (호출 수 제한)

# 오피넷은 KATEC 좌표를 쓴다 — 위도·경도(WGS84)와 서로 변환
KATEC = ("+proj=tmerc +lat_0=38 +lon_0=128 +k=0.9999 +x_0=400000 +y_0=600000 +ellps=bessel +units=m +no_defs "
         "+towgs84=-115.80,474.99,674.11,1.16,-2.31,-1.63,6.43")
TO_KATEC = Transformer.from_crs("EPSG:4326", KATEC, always_xy=True)
FROM_KATEC = Transformer.from_crs(KATEC, "EPSG:4326", always_xy=True)

UPSTREAM_ERROR = "지도 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요."


class LatLng(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: LatLng
    destination: LatLng
    waypoints: list[LatLng] = Field(default=[], max_length=5)

    # Swagger "Try it out"에 미리 채워지는 예시: 울산시청 → 울산대공원, 경유지 없음
    model_config = {"json_schema_extra": {"examples": [{
        "origin": {"lat": 35.5384, "lng": 129.3114},
        "destination": {"lat": 35.5287, "lng": 129.2923},
        "waypoints": [],
    }]}}


async def get_json(url: str, params: dict, headers: dict | None = None) -> dict:
    """외부 API 호출. 실패·시간 초과는 모두 502로 바꿔 사용자에게 보여 줄 문장만 남긴다."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            res = await client.get(url, params=params, headers=headers)
            res.raise_for_status()
            return res.json()
    except (httpx.HTTPError, ValueError) as e:
        # 원인은 서버 로그에만 남긴다 (키 설정 누락·권한 문제 등을 찾기 위해).
        # 오피넷은 키가 쿼리에 들어가므로 요청 주소 전체나 예외 메시지(주소 포함)는 남기지 않는다
        if isinstance(e, httpx.HTTPStatusError):
            log.warning("외부 API 실패 %s: HTTP %s %s", url, e.response.status_code, e.response.text[:200])
        else:
            log.warning("외부 API 실패 %s: %s", url, type(e).__name__)
        raise HTTPException(502, UPSTREAM_ERROR)


def kakao_place(doc: dict) -> dict:
    return {
        "id": f"kakao:{doc['id']}",
        "name": doc["place_name"],
        "address": doc.get("road_address_name") or doc.get("address_name"),
        "lat": float(doc["y"]),
        "lng": float(doc["x"]),
        "distance_m": int(doc["distance"]) if doc.get("distance") else None,   # 기준 좌표를 줬을 때만 있음
        "price_won": None,
    }


@router.get("/places/search", summary="장소 검색")
async def search_places(query: str = Query(min_length=1, max_length=100, openapi_examples={"울산대공원": {"value": "울산대공원"}}),
                        lat: float | None = Query(None, openapi_examples={"울산시청": {"value": 35.5384}}),
                        lng: float | None = Query(None, openapi_examples={"울산시청": {"value": 129.3114}})):
    params = {"query": query, "size": 15}
    if lat is not None and lng is not None:
        params.update(x=lng, y=lat)   # 기준 좌표가 있으면 거리도 받는다
    data = await get_json("https://dapi.kakao.com/v2/local/search/keyword.json", params, KAKAO_HEADERS)
    return {"places": [kakao_place(d) for d in data["documents"]]}


@router.get("/places/nearby", summary="주변 장소 찾기")
async def nearby_places(category: Literal["parking", "gas_station", "cafe"] = Query(openapi_examples={"주차장": {"value": "parking"}}),
                        lat: float = Query(openapi_examples={"울산시청": {"value": 35.5384}}),
                        lng: float = Query(openapi_examples={"울산시청": {"value": 129.3114}}),
                        radius_m: int = Query(1000, ge=1, le=20000),
                        sort: Literal["distance", "price"] = "distance"):
    if category == "gas_station":
        return {"places": await nearby_gas_stations(lat, lng, radius_m, sort)}
    if sort == "price":
        raise HTTPException(422, "가격순 정렬은 주유소에서만 할 수 있어요.")

    data = await get_json("https://dapi.kakao.com/v2/local/search/category.json", {
        "category_group_code": KAKAO_CATEGORY[category], "x": lng, "y": lat,
        "radius": radius_m, "sort": "distance", "size": 15,
    }, KAKAO_HEADERS)
    return {"places": [kakao_place(d) for d in data["documents"]]}


async def nearby_gas_stations(lat: float, lng: float, radius_m: int, sort: str) -> list[dict]:
    """주유소는 휘발유 가격이 있는 오피넷으로 찾는다."""
    x, y = TO_KATEC.transform(lng, lat)
    data = await get_json("https://www.opinet.co.kr/api/aroundAll.do", {
        "code": OPINET_KEY, "x": x, "y": y, "radius": min(radius_m, OPINET_MAX_RADIUS_M),
        "sort": 1 if sort == "price" else 2,   # 1: 가격순, 2: 거리순
        "prodcd": "B027",                       # 휘발유
        "out": "json",
    })
    stations = data["RESULT"]["OIL"][:OPINET_DETAIL_LIMIT]

    # 주변 검색 결과에는 주소가 없어서 상세 조회를 동시에 보낸다 (실패해도 주소만 비운다)
    details = await asyncio.gather(*(get_json("https://www.opinet.co.kr/api/detailById.do", {
        "code": OPINET_KEY, "id": s["UNI_ID"], "out": "json",
    }) for s in stations), return_exceptions=True)

    places = []
    for s, detail in zip(stations, details):
        st_lng, st_lat = FROM_KATEC.transform(s["GIS_X_COOR"], s["GIS_Y_COOR"])
        address = None
        if isinstance(detail, dict) and detail["RESULT"]["OIL"]:
            info = detail["RESULT"]["OIL"][0]
            address = info.get("NEW_ADR") or info.get("VAN_ADR")
        places.append({
            "id": f"opinet:{s['UNI_ID']}",
            "name": s["OS_NM"],
            "address": address,
            "lat": round(st_lat, 7),
            "lng": round(st_lng, 7),
            "distance_m": round(s["DISTANCE"]),
            "price_won": s["PRICE"],
        })
    return places


@router.post("/route", summary="경로")
async def route(body: RouteRequest):
    params = {
        "origin": f"{body.origin.lng},{body.origin.lat}",
        "destination": f"{body.destination.lng},{body.destination.lat}",
        "priority": "RECOMMEND",
    }
    if body.waypoints:
        params["waypoints"] = "|".join(f"{w.lng},{w.lat}" for w in body.waypoints)
    data = await get_json("https://apis-navi.kakaomobility.com/v1/directions", params, KAKAO_HEADERS)

    r = data["routes"][0]
    if r["result_code"] != 0:   # 출발지와 도착지가 너무 가깝거나 길이 없는 경우 등
        raise HTTPException(422, f"경로를 찾을 수 없어요. ({r['result_msg']})")

    # 도로별 좌표 [x1, y1, x2, y2, ...]를 지도에 그릴 [경도, 위도] 목록으로 펼친다
    path = []
    for section in r["sections"]:
        for road in section["roads"]:
            v = road["vertexes"]
            path += [[v[i], v[i + 1]] for i in range(0, len(v), 2)]

    # guides[0]은 출발지 안내라서 그다음이 첫 회전 안내
    guides = [g for sec in r["sections"] for g in sec["guides"]]
    first = guides[1] if len(guides) > 1 else None
    next_guide = f"{first['distance']}m 앞 {first['guidance']}" if first else None

    duration_s = r["summary"]["duration"]
    return {
        "distance_m": r["summary"]["distance"],
        "duration_s": duration_s,
        "eta": (datetime.now(KST) + timedelta(seconds=duration_s)).strftime("%H:%M"),
        "path": path,
        "next_guide": next_guide,
    }
