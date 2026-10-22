"""[목업] 지도 API — 고정 데이터를 돌려준다. 카카오·오피넷 연동 시 교체."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["지도 (목업)"])

MOCK_PLACES = {
    "parking": [
        {"id": "kakao:1001", "name": "주차장 A", "address": "울산 남구 삼산로 100", "lat": 35.5395, "lng": 129.3120, "distance_m": 400, "price_won": None},
        {"id": "kakao:1002", "name": "주차장 B", "address": "울산 남구 삼산로 200", "lat": 35.5410, "lng": 129.3150, "distance_m": 1200, "price_won": None},
    ],
    "gas_station": [
        {"id": "kakao:2001", "name": "OO주유소", "address": "울산 남구 번영로 50", "lat": 35.5370, "lng": 129.3090, "distance_m": 600, "price_won": 1659},
        {"id": "kakao:2002", "name": "XX주유소", "address": "울산 남구 번영로 150", "lat": 35.5350, "lng": 129.3060, "distance_m": 900, "price_won": 1689},
    ],
    "cafe": [
        {"id": "kakao:3001", "name": "카페 차근", "address": "울산 남구 달동 10", "lat": 35.5380, "lng": 129.3130, "distance_m": 300, "price_won": None},
    ],
}


class LatLng(BaseModel):
    lat: float
    lng: float


class RouteRequest(BaseModel):
    origin: LatLng
    destination: LatLng
    waypoints: list[LatLng] = []


@router.get("/places/search", summary="장소 검색")
def search_places(query: str, lat: float | None = None, lng: float | None = None):
    return {"places": [
        {"id": "kakao:8123", "name": query, "address": "울산 남구 대공원로 94", "lat": 35.5300, "lng": 129.3000, "distance_m": 2300, "price_won": None},
    ]}


@router.get("/places/nearby", summary="주변 장소 찾기")
def nearby_places(category: str, lat: float, lng: float, radius_m: int = 1000, sort: str = "distance"):
    places = MOCK_PLACES.get(category, [])
    key = "price_won" if sort == "price" and category == "gas_station" else "distance_m"
    return {"places": sorted(places, key=lambda p: p[key])}


@router.post("/route", summary="경로")
def route(body: RouteRequest):
    path = [[body.origin.lng, body.origin.lat]]
    path += [[w.lng, w.lat] for w in body.waypoints]
    path += [[body.destination.lng, body.destination.lat]]
    extra = len(body.waypoints) * 300   # 경유지 1곳당 5분 추가 (목업)
    return {"distance_m": 5400, "duration_s": 720 + extra, "eta": "09:20",
            "path": path, "next_guide": "300m 앞 우회전"}
