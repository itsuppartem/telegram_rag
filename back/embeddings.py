import asyncio
from typing import List, Optional

from sentence_transformers import SentenceTransformer, CrossEncoder

from config import EMBEDDING_MODEL_NAME, RERANKER_MODEL_NAME

embedding_model = None
reranker_model = None


async def initialize_models():
    global embedding_model, reranker_model

    try:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device='cpu')
        reranker_model = CrossEncoder(RERANKER_MODEL_NAME, device='cpu')
        return True
    except Exception as e:
        print(f"Error initializing embedding models: {e}")
        return False


async def generate_embedding(text: str) -> Optional[List[float]]:
    if embedding_model is None:
        return None

    try:
        vector = await asyncio.to_thread(embedding_model.encode, text)
        return vector.tolist()
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


async def rerank_results(question: str, search_results: List[dict]) -> List[dict]:
    if not search_results or reranker_model is None:
        return search_results

    try:
        pairs = []
        valid_results = []

        for result in search_results:
            payload = result.payload if result.payload else {}
            chunk_text = payload.get('text', '')
            if chunk_text:
                pairs.append([question, chunk_text])
                valid_results.append(result)

        if not pairs:
            return search_results

        scores = await asyncio.to_thread(reranker_model.predict, pairs)

        reranked_results = []
        for i, result in enumerate(valid_results):
            if i < len(scores):
                new_score = float(scores[i])
                result.score = new_score
                reranked_results.append(result)

        reranked_results.sort(key=lambda x: x.score, reverse=True)
        return reranked_results

    except Exception as e:
        print(f"Error during reranking: {e}")
        search_results.sort(key=lambda x: x.score, reverse=True)
        return search_results
