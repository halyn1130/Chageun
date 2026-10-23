import os

import pymysql
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db
from app.routers import places, rag, vehicles, voice

app = FastAPI(title="차근 api-server")

# 프론트(Vue)가 다른 포트에서 호출할 수 있도록 허용. 출처 목록은 .env의 FRONTEND_ORIGINS(쉼표 구분)
FRONTEND_ORIGINS = [o.strip() for o in os.environ["FRONTEND_ORIGINS"].split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehicles.router)
app.include_router(places.router)
app.include_router(voice.router)
app.include_router(rag.router)


@app.get("/health")
def health():
    # DB까지 닿는지 확인해서, 연결이 안 되면 503으로 알린다
    try:
        conn = db.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
    except pymysql.MySQLError:
        return JSONResponse({"status": "error", "db": "down"}, status_code=503)
    return {"status": "ok", "db": "ok"}
