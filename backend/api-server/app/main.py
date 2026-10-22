from fastapi import FastAPI

app = FastAPI(title="차근 api-server")


@app.get("/health")
def health():
    return {"status": "ok"}
