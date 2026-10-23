"""RAG server on :8001, called only by the api-server inside the compose network.

Run from ai_data/: RAG_INDEX=data/indexes/<version> uvicorn chageun_ai.server:app --port 8001
"""
from __future__ import annotations
import asyncio
import contextlib
import logging
import os
from pathlib import Path
from typing import Literal
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .agent import rag_query
from .core import read_json, search

log = logging.getLogger('chageun.rag')


class Vehicle(BaseModel):
    id: int | None = None
    manufacturer: str
    model: str
    model_year: str
    powertrain: str
    mileage_km: int | None = None


class MaintenanceRecord(BaseModel):
    item: str
    performed_at: str | None = None
    mileage_km: int | None = None


class Maintenance(BaseModel):
    # The api-server draft and the confirmed spec name the states differently; nothing here depends on them yet.
    lookup_status: str
    items: list[str] = []
    records: list[MaintenanceRecord] = []


class Message(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class LatLng(BaseModel):
    lat: float
    lng: float


class Destination(LatLng):
    name: str


class RagRequest(BaseModel):
    request_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    question: str = Field(min_length=2, max_length=500)
    vehicle: Vehicle | None = None
    maintenance: Maintenance
    history: list[Message] = Field(default=[], max_length=20)
    location: LatLng | None = None
    destination: Destination | None = None


class Engine:
    """Loads the models once; the index path and its embedding model come from the index manifest."""

    def __init__(self, index, llm_model):
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        self.index = Path(index)
        manifest = read_json(self.index / 'manifest.json')
        self.embedding = OpenAIEmbeddings(model=manifest['embedding_model'])
        llm = ChatOpenAI(model=llm_model, temperature=0, timeout=20, max_retries=1)
        self.llm, self.json_llm = llm, llm.bind(response_format={'type': 'json_object'})

    def choose(self, system, question, tools):
        calls = self.llm.bind_tools(tools, tool_choice='required').invoke([('system', system), ('human', question)]).tool_calls
        return (calls[0]['name'], calls[0]['args']) if calls else None

    def retrieve(self, query, filters):
        return search(self.index, self.embedding.embed_query(query), filters, 5, query=query)

    def generate(self, system, user):
        return self.json_llm.invoke([('system', system), ('human', user)]).content

    def ask(self, request):
        return rag_query(request, self.choose, self.retrieve, self.generate)


def create_app(engine_factory=None, secret=None, timeout_s=None):
    secret = secret if secret is not None else os.getenv('JWT_SECRET', '')
    timeout_s = timeout_s or float(os.getenv('RAG_TIMEOUT_S', '30'))

    @contextlib.asynccontextmanager
    async def lifespan(app):
        try:
            factory = engine_factory or (lambda: Engine(os.environ['RAG_INDEX'], os.getenv('RAG_LLM_MODEL', 'gpt-4o-mini')))
            app.state.engine = factory()
        except Exception:  # the server still starts so /health can report that it is not ready
            log.exception('index not ready')
        yield

    app = FastAPI(title='차근 RAG 서버', lifespan=lifespan)
    app.state.engine = None

    @app.exception_handler(RequestValidationError)
    def invalid(request: Request, error: RequestValidationError):
        fields = ', '.join('.'.join(map(str, e['loc'][1:])) for e in error.errors())
        return JSONResponse(status_code=422, content={'detail': f'요청 형식이 올바르지 않아요: {fields}'})

    def user(authorization: str | None = Header(default=None)):
        # The api-server forwards the user's token; verify it with the auth server's secret and issuer.
        if not secret:
            raise HTTPException(503, 'RAG 서버 인증 설정이 준비되지 않았어요.')
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, '로그인이 필요해요.')
        try:
            return jwt.decode(authorization[7:], secret, algorithms=['HS256'], issuer='simple-auth-server',
                              options={'require': ['exp', 'iss', 'sub']})
        except jwt.PyJWTError:
            raise HTTPException(401, '로그인 정보가 만료되었거나 올바르지 않아요.')

    @app.get('/health')
    def health():
        if app.state.engine is None:
            return JSONResponse(status_code=503, content={'status': 'unavailable', 'detail': '인덱스가 준비되지 않았어요.'})
        return {'status': 'ok'}

    @app.post('/rag-query')
    async def query(body: RagRequest, claims: dict = Depends(user)):
        if app.state.engine is None:
            raise HTTPException(503, '답변 준비가 아직 끝나지 않았어요. 잠시 후 다시 시도해 주세요.')
        try:
            result = await asyncio.wait_for(asyncio.to_thread(app.state.engine.ask, body.model_dump()), timeout_s)
        except asyncio.TimeoutError:
            log.warning('timeout request_id=%s', body.request_id)
            raise HTTPException(503, '답변이 늦어지고 있어요. 다시 시도해 주세요.')
        except Exception:
            log.exception('failed request_id=%s', body.request_id)
            raise HTTPException(503, '지금은 답변을 만들 수 없어요. 잠시 후 다시 시도해 주세요.')
        log.info('request_id=%s user=%s status=%s', body.request_id, claims.get('sub'), result['status'])
        return result

    return app


def _app():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    logging.basicConfig(level=logging.INFO)
    return create_app()


app = _app()
