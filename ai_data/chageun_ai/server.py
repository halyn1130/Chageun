"""RAG server on :8001, called only by the api-server inside the compose network.

Run from ai_data/: RAG_INDEX=data/indexes/<version> uvicorn chageun_ai.server:app --port 8001
"""
from __future__ import annotations
import asyncio
import contextlib
import contextvars
import json
import logging
import os
import time
from pathlib import Path
from typing import Literal
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .agent import rag_query
from .core import read_json, rerank_hits, search, VERIFY_SYSTEM

log = logging.getLogger('chageun.rag')

# USD per 1M tokens (input, output): the list prices we assumed in 2026-10, not checked against a bill.
# Override with RAG_PRICES='{"gpt-4o": [2.5, 10]}'. A model with no price is logged with cost null.
PRICES = {'gpt-4o-mini': (0.15, 0.60), 'gpt-4o': (2.50, 10.00)}
# The LLM calls of the request being answered (Engine.ask runs each request in its own thread).
_calls = contextvars.ContextVar('rag_calls', default=None)


def price_of(model, prices):
    """The longest price key the model name starts with: gpt-4o-mini-2024-07-18 is gpt-4o-mini, not gpt-4o."""
    key = max((k for k in prices if (model or '').startswith(k)), key=len, default=None)
    return prices[key] if key else None


def usage_summary(request_id, status, calls, total_ms, prices=PRICES):
    """One log record per request: the unit cost and latency of each step (scripts/usage_report.py sums them).

    Embedding calls are not counted: their responses carry no usage and they cost about 1/100 of the rest.
    """
    cost = 0.0
    for call in calls:
        price = price_of(call['model'], prices)
        call['cost_usd'] = None if price is None else round((call['in'] * price[0] + call['out'] * price[1]) / 1e6, 6)
        cost = None if cost is None or call['cost_usd'] is None else cost + call['cost_usd']
    return {'request_id': request_id, 'status': status, 'total_ms': round(total_ms),
            'tokens_in': sum(c['in'] for c in calls), 'tokens_out': sum(c['out'] for c in calls),
            'cost_usd': None if cost is None else round(cost, 6), 'calls': calls}


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
    """Loads the models once; the index path and its embedding model come from the index manifest.

    llm_model routes questions and verifies answers; answer_model (default: the same) writes the answers;
    verify_model (default: llm_model) checks them. gpt-4o-mini as verifier rejected answers copied almost
    word for word from the manual (2026-10-25: engine/brake lights 0/3), gpt-4o passed them 3/3.
    (An earlier note found the opposite - "a stronger verifier rejected correct answers" - so the verifier
    must also be checked on wrong answers; see evaluation/experiments/README section 6.)
    A stronger writer keeps a rule's exceptions straight.
    """

    def __init__(self, index, llm_model, answer_model=None, verify_model=None, retry_model=None):
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        self.index = Path(index)
        manifest = read_json(self.index / 'manifest.json')
        self.embedding = OpenAIEmbeddings(model=manifest['embedding_model'])
        make = lambda model, **kw: ChatOpenAI(model=model, temperature=0, timeout=20, max_retries=1, **kw)
        self.llm = make(llm_model)
        self.json_llm = self.llm.bind(response_format={'type': 'json_object'})
        # Output length is most of the latency (about 75 tokens a second); a short answer also suits driving.
        # The cap stops a runaway answer; a cut-off JSON fails closed like any invalid answer.
        self.answer_llm = make(answer_model or llm_model, max_tokens=500).bind(response_format={'type': 'json_object'})
        self.verify_llm = (make(verify_model).bind(response_format={'type': 'json_object'})
                           if verify_model and verify_model != llm_model else self.json_llm)
        # retry_model writes only the retry after a rejected answer, so a stronger model costs extra only there.
        self.retry_llm = (make(retry_model, max_tokens=500).bind(response_format={'type': 'json_object'})
                          if retry_model else None)
        # Reranking is optional: a short timeout and no retry, so a slow call falls back to the search order
        # well inside the 30 s request budget instead of spending it.
        self.rerank_llm = ChatOpenAI(model=llm_model, temperature=0, timeout=8, max_retries=0).bind(
            response_format={'type': 'json_object'})
        self.prices = {**PRICES, **{k: tuple(v) for k, v in json.loads(os.getenv('RAG_PRICES') or '{}').items()}}

    @staticmethod
    def invoke(step, llm, messages):
        """llm.invoke that records the step's model, tokens and time for this request's usage log."""
        started = time.perf_counter()
        message = llm.invoke(messages)
        calls = _calls.get()
        if calls is not None:
            usage = message.usage_metadata or {}
            calls.append({'step': step, 'model': message.response_metadata.get('model_name'),
                          'in': usage.get('input_tokens', 0), 'out': usage.get('output_tokens', 0),
                          'ms': round((time.perf_counter() - started) * 1000)})
        return message

    def choose(self, system, question, tools):
        calls = self.invoke('route', self.llm.bind_tools(tools, tool_choice='required'),
                            [('system', system), ('human', question)]).tool_calls
        return (calls[0]['name'], calls[0]['args']) if calls else None

    TOP_K, RERANK_POOL = 8, 15

    def retrieve(self, query, filters):
        # RAG_RERANK=1: take 15 candidates and let the LLM put the passage that answers first
        # (evaluation/experiments/exp03: MRR 0.52 -> 0.80~0.86, about +1 s). Off: the original top 8.
        rerank = os.getenv('RAG_RERANK', '0') == '1'
        hits = search(self.index, self.embedding.embed_query(query), filters,
                      self.RERANK_POOL if rerank else self.TOP_K, query=query)
        if not rerank:
            return hits
        started = time.perf_counter()
        ranked = rerank_hits(query, hits, lambda system, user: self.invoke(
            'rerank', self.rerank_llm, [('system', system), ('human', user)]).content, keep=self.TOP_K)
        log.info('rerank candidates=%d kept=%d ms=%d', len(hits), len(ranked),
                 (time.perf_counter() - started) * 1000)
        return ranked

    def generate(self, system, user):
        step, llm = ('verify', self.verify_llm) if system == VERIFY_SYSTEM else ('answer', self.answer_llm)
        return self.invoke(step, llm, [('system', system), ('human', user)]).content

    def retry_generate(self, system, user):
        return self.invoke('retry', self.retry_llm, [('system', system), ('human', user)]).content

    def ask(self, request):
        calls, started, status = [], time.perf_counter(), 'error'
        token = _calls.set(calls)
        try:
            result = rag_query(request, self.choose, self.retrieve, self.generate,
                               self.retry_generate if self.retry_llm else None)
            status = result['status']
            return result
        finally:
            _calls.reset(token)
            # Logged even after the api-server stopped waiting (timeout): the tokens were spent either way.
            log.info('usage %s', json.dumps(usage_summary(request.get('request_id'), status, calls,
                                                           (time.perf_counter() - started) * 1000, self.prices)))


def create_app(engine_factory=None, secret=None, timeout_s=None):
    secret = secret if secret is not None else os.getenv('JWT_SECRET', '')
    timeout_s = timeout_s or float(os.getenv('RAG_TIMEOUT_S', '30'))

    @contextlib.asynccontextmanager
    async def lifespan(app):
        try:
            factory = engine_factory or (lambda: Engine(os.environ['RAG_INDEX'], os.getenv('RAG_LLM_MODEL', 'gpt-4o-mini'),
                                                        os.getenv('RAG_ANSWER_MODEL') or None,
                                                        os.getenv('RAG_VERIFY_MODEL') or None,
                                                        os.getenv('RAG_RETRY_MODEL') or None))
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
