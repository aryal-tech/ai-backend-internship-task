# Supports: openai | fastembed | local (sentence-transformers)
from __future__ import annotations
from typing import List, Optional
import asyncio
from app.core.config import get_settings

_SETTINGS = get_settings()

class EmbeddingClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, dim: Optional[int] = None):
        self.provider = provider or _SETTINGS.EMBEDDING_PROVIDER
        self.model = model or _SETTINGS.EMBEDDING_MODEL
        self.dim = dim or _SETTINGS.EMBEDDING_DIM

        self._client = None       # OpenAI
        self._fast_model = None   # fastembed
        self._st_model = None     # sentence-transformers
        self._init_clients()

    def _init_clients(self) -> None:
        if self.provider == "openai":
            from openai import AsyncOpenAI  # type: ignore
            if not _SETTINGS.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY not set")
            self._client = AsyncOpenAI(api_key=_SETTINGS.OPENAI_API_KEY)
        elif self.provider in ("fastembed", "local"):
            # lazy init on first use
            pass
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")

    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        batch_size = 64
        out: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            resp = await self._client.embeddings.create(model=self.model, input=batch)  # type: ignore
            out.extend([d.embedding for d in resp.data])
        return out

    async def _embed_fastembed(self, texts: List[str]) -> List[List[float]]:
        def _load_and_encode() -> List[List[float]]:
            from fastembed import TextEmbedding
            if self._fast_model is None:
                self._fast_model = TextEmbedding(model_name=self.model)
            return [v.tolist() for v in self._fast_model.embed(texts, batch_size=32, normalize=True)]
        return await asyncio.to_thread(_load_and_encode)

    async def _embed_local(self, texts: List[str]) -> List[List[float]]:
        def _load_and_encode() -> List[List[float]]:
            from sentence_transformers import SentenceTransformer
            if self._st_model is None:
                self._st_model = SentenceTransformer(self.model)
            vecs = self._st_model.encode(texts, batch_size=32, normalize_embeddings=True)  # type: ignore
            return vecs.tolist()
        return await asyncio.to_thread(_load_and_encode)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self.provider == "openai":
            return await self._embed_openai(texts)
        if self.provider == "fastembed":
            return await self._embed_fastembed(texts)
        # "local" = sentence-transformers
        return await self._embed_local(texts)