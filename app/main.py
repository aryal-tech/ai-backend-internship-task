from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient
import redis.asyncio as redis

from app.core.config import get_settings
from app.api.ingest import router as ingest_router
from app.api.chat import router as chat_router # IMPORT

_SETTINGS = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.qdrant = AsyncQdrantClient(url=_SETTINGS.QDRANT_URL)
    app.state.redis = redis.from_url(_SETTINGS.REDIS_URL, decode_responses=True) # REDIS
    yield
    await app.state.qdrant.close()
    await app.state.redis.close() # REDIS

app = FastAPI(title="AI Backend", lifespan=lifespan)
app.include_router(ingest_router)
app.include_router(chat_router) # ROUTER

@app.get("/")
async def root(): return {"message": "Service is up. See /docs for API details."}