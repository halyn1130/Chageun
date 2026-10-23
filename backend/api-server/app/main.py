from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import places, rag, vehicles, voice

app = FastAPI(title="차근 api-server")

# 프론트(Vue 개발 서버)가 다른 포트에서 호출할 수 있도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehicles.router)
app.include_router(places.router)
app.include_router(voice.router)
app.include_router(rag.router)


@app.get("/health")
def health():
    return {"status": "ok"}
