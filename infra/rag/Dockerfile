# RAG 서버 (ai_data/chageun_ai/server.py) — 빌드 컨텍스트는 ai_data/, 코드는 AI팀 것을 그대로 쓴다
# 인덱스(data/indexes)는 이미지에 넣지 않고 compose에서 볼륨으로 연결한다
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY chageun_ai ./chageun_ai
# 경고등 사전 — agent가 시작할 때 읽는다 (data/indexes는 볼륨이라 이 파일과 함께 /app/data 아래에 놓인다)
COPY data/warning_lights.json ./data/warning_lights.json
EXPOSE 8001
CMD ["uvicorn", "chageun_ai.server:app", "--host", "0.0.0.0", "--port", "8001"]
