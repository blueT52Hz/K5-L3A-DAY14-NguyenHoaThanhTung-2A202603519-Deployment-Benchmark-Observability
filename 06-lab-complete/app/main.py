import json
import logging
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from utils.mock_llm import ask as llm_ask

from .auth import verify_api_key
from .config import settings
from .cost_guard import check_budget, record_cost
from .rate_limiter import check_rate_limit
from .redis_client import r, redis_healthy


logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(logging.StreamHandler())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(json.dumps({"event": "startup", "environment": settings.environment}))
    try:
        yield
    finally:
        r.close()
        logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.middleware("http")
async def log_request(request: Request, call_next):
    start = monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        logger.info(json.dumps({"event": "request", "path": request.url.path,
                                "status": status, "ms": round((monotonic() - start) * 1000, 1)}))


@app.exception_handler(RedisError)
async def redis_unavailable(request: Request, exc: RedisError):
    return JSONResponse({"detail": "Redis unavailable"}, status_code=503)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(503, "Redis unavailable")
    return {"ready": True}


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    check_rate_limit(key)
    input_tokens = len(body.question.split()) * 2
    reservation = check_budget(input_tokens)
    try:
        answer = llm_ask(body.question)
    except Exception:
        record_cost(reservation, 0, 0)
        raise
    cost = record_cost(reservation, input_tokens, len(answer.split()) * 2)
    return {"question": body.question, "answer": answer, "cost_usd": cost}
