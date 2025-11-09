import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv

load_dotenv()

collection = os.getenv("QDRANT_COLLECTION", "docs")
dim = int(os.getenv("EMBEDDING_DIM", "1536"))
url = os.getenv("QDRANT_URL", "http://localhost:6333")

client = QdrantClient(url=url)

existing = [c.name for c in client.get_collections().collections]
if collection in existing:
    print(f"Collection '{collection}' already exists with dim you created earlier.")
else:
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    print(f"Created collection '{collection}' with dim={dim}, metric=cosine")