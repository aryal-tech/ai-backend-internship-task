from typing import Any, Dict, Sequence
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Batch


class VectorStore:
    def __init__(self, client: AsyncQdrantClient, collection: str):
        self.client = client
        self.collection = collection

    async def upsert(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        payloads: Sequence[Dict[str, Any]],
    ) -> None:
        batch = Batch(ids=list(ids), vectors=list(vectors), payloads=list(payloads))
        await self.client.upsert(collection_name=self.collection, points=batch)

    async def delete_points(self, ids: Sequence[str]) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector={"points": list(ids)}
        )
