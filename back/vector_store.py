import asyncio
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, ScoredPoint, Filter, FilterSelector

from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME, VECTOR_SIZE

qdrant_client = None


async def initialize_vector_store():
    global qdrant_client

    try:
        qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30, prefer_grpc=False)

        try:
            qdrant_client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
        except Exception as e:
            if "not found" in str(e).lower() or "status_code=404" in str(e):
                qdrant_client.create_collection(collection_name=QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                    optimizers_config={"default_segment_number": 2, "max_optimization_threads": 2,
                        "memmap_threshold": 1000000, "indexing_threshold": 50000, "flush_interval_sec": 5,
                        "max_segment_size": 1000000, "deleted_threshold": 0.2, "vacuum_min_vector_number": 1000},
                    on_disk_payload=True)

        return True
    except Exception as e:
        print(f"Error initializing Qdrant: {e}")
        return False


async def search_vectors(query_vector: List[float], limit: int = 20, score_threshold: float = 0.5,
        filter_conditions: Optional[List] = None) -> List[ScoredPoint]:
    if qdrant_client is None:
        return []

    try:
        query_filter = None
        if filter_conditions:
            query_filter = Filter(should=filter_conditions)

        search_results = await asyncio.to_thread(qdrant_client.search, collection_name=QDRANT_COLLECTION_NAME,
            query_vector=query_vector, query_filter=query_filter, limit=limit, score_threshold=score_threshold)

        return search_results
    except Exception as e:
        print(f"Error searching vectors: {e}")
        return []


async def delete_document_vectors(doc_id: str) -> bool:
    if qdrant_client is None:
        return False

    try:
        delete_result = await asyncio.to_thread(qdrant_client.delete, collection_name=QDRANT_COLLECTION_NAME,
            points_selector=FilterSelector(
                filter=Filter(must=[{"key": "document_mongo_id", "match": {"value": str(doc_id)}}])), wait=True)

        return delete_result.status == "completed"
    except Exception as e:
        print(f"Error deleting document vectors: {e}")
        return False


async def upsert_vectors(points: List[dict]) -> bool:
    if qdrant_client is None:
        return False

    try:
        await asyncio.to_thread(qdrant_client.upsert, collection_name=QDRANT_COLLECTION_NAME, points=points, wait=True)
        return True
    except Exception as e:
        print(f"Error upserting vectors: {e}")
        return False
