#orchestration ingestion pipeline
from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Literal, Optional, Tuple
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import text as sql_text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.utils.text_extraction import extract_text_from_file
from app.utils.chunking import chunk_fixed_tokens, chunk_semantic
from app.utils.embeddings import EmbeddingClient
from app.repositories.vector_store import VectorStore
from app.schemas.ingest import IngestResponse

_SETTINGS = get_settings()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class IngestionService:
    def __init__(
        self,
        vector_store: VectorStore,
        embedder: EmbeddingClient,
        session: AsyncSession,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.session = session

    async def ingest(
        self,
        file: UploadFile,
        chunk_strategy: Literal["fixed", "semantic"] = "semantic",
        chunk_size: int = 500,
        overlap: int = 50,
        use_ocr: bool = True,
        extra_metadata: Optional[Dict] = None,
    ) -> IngestResponse:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty file")

        checksum = _sha256(data)

        # Idempotency: check if document already exists
        doc_row = await self.session.execute(
            sql_text("SELECT id FROM documents WHERE checksum = :ck LIMIT 1"),
            {"ck": checksum},
        )
        row = doc_row.first()
        if row:
            doc_id = row[0]
            cnt_row = await self.session.execute(
                sql_text("SELECT COUNT(*) FROM chunks WHERE doc_id = :doc"),
                {"doc": doc_id},
            )
            chunks_count = int(cnt_row.scalar() or 0)
            return IngestResponse(
                document_id=doc_id,
                chunks=chunks_count,
                chunk_strategy=chunk_strategy,
                embedding_model=_SETTINGS.EMBEDDING_MODEL,
                vector_collection=_SETTINGS.QDRANT_COLLECTION,
                used_ocr=False,
                skipped_duplicate=True,
            )

        # Extract text
        try:
            text, used_ocr = extract_text_from_file(
                filename=file.filename or "",
                content_type=file.content_type,
                data=data,
                use_ocr=use_ocr,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=422, detail=str(e))
        if not text or len(text) < 10:
            raise HTTPException(status_code=422, detail="Failed to extract text")

        # Chunk
        if chunk_strategy == "fixed":
            chunks = chunk_fixed_tokens(text, chunk_size=chunk_size, overlap=overlap)
        else:
            chunks = chunk_semantic(text, max_tokens=chunk_size, overlap_sentences=max(0, overlap // 50))
        # chunks: List[Tuple[text, token_count]]

        if not chunks:
            raise HTTPException(status_code=422, detail="No chunks produced")

        doc_id = str(uuid4())
        chunk_ids: List[str] = []
        payloads: List[Dict] = []
        texts: List[str] = []

        for idx, (chunk_text, tok_count) in enumerate(chunks):
            cid = str(uuid4())
            chunk_ids.append(cid)
            texts.append(chunk_text)
            payload = {
                "doc_id": doc_id,
                "chunk_index": idx,
                "filename": file.filename,
                "token_count": tok_count,
                "mime_type": file.content_type,
                "source": file.filename,
                "text": chunk_text,
               
            }
            if extra_metadata:
                payload.update(extra_metadata)
            payloads.append(payload)

        # Embed
        try:
            vectors = await self.embedder.embed_texts(texts)
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"Embedding provider error: {e}"
            )

        # Sanity check on vector dim
        if not vectors or len(vectors[0]) != _SETTINGS.EMBEDDING_DIM:
            raise HTTPException(
                status_code=500,
                detail=f"Embedding dimension mismatch. Expected {_SETTINGS.EMBEDDING_DIM}, got {len(vectors[0]) if vectors else 'None'}",
            )

        # Upsert to Qdrant first
        try:
            await self.vector_store.upsert(ids=chunk_ids, vectors=vectors, payloads=payloads)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Vector store error: {e}")

        # Write to MySQL in a transaction; if it fails, attempt to delete vectors
        try:
            await self.session.execute(
                sql_text(
                    "INSERT INTO documents (id, title, source_uri, mime_type, checksum) "
                    "VALUES (:id, :title, :src, :mime, :ck)"
                ),
                {
                    "id": doc_id,
                    "title": file.filename or None,
                    "src": None,
                    "mime": file.content_type or None,
                    "ck": checksum,
                },
            )

            # Bulk insert chunks
            values_sql = (
                "INSERT INTO chunks (id, doc_id, chunk_index, page_start, page_end, heading, token_count, vector_id) "
                "VALUES (:id, :doc_id, :chunk_index, NULL, NULL, NULL, :token_count, :vector_id)"
            )
            for idx, (cid, (_txt, tok)) in enumerate(zip(chunk_ids, chunks)):
                await self.session.execute(
                    sql_text(values_sql),
                    {
                        "id": cid,
                        "doc_id": doc_id,
                        "chunk_index": idx,
                        "token_count": tok,
                        "vector_id": cid,
                    },
                )

            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            try:
                await self.vector_store.delete_points(ids=chunk_ids)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"DB error: {e}")

        return IngestResponse(
            document_id=doc_id,
            chunks=len(chunks),
            chunk_strategy=chunk_strategy,
            embedding_model=_SETTINGS.EMBEDDING_MODEL,
            vector_collection=_SETTINGS.QDRANT_COLLECTION,
            used_ocr=used_ocr,
            skipped_duplicate=False,
        )