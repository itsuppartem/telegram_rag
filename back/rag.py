import time
from typing import Dict, Any, Tuple

from config import MAX_QDRANT_RESULTS_TO_FETCH
from embeddings import generate_embedding, rerank_results
from llm import classify_question_llm, enrich_query_with_llm, make_llm_request
from utils import filter_duplicate_chunks
from vector_store import search_vectors


async def ask_question_rag(user_id: int, question: str) -> Tuple[str, Dict[str, Any]]:
    start_time = time.time()
    metadata = {"user_id": user_id}
    final_answer = "Ошибка обработки запроса."

    classified_category = await classify_question_llm(question)
    metadata["classified_category"] = classified_category

    enriched_question = await enrich_query_with_llm(question)
    question_embedding = await generate_embedding(enriched_question)
    if not question_embedding:
        return "Ошибка генерации эмбеддинга.", metadata

    search_results = await search_vectors(question_embedding, limit=MAX_QDRANT_RESULTS_TO_FETCH * 2)
    search_results = await rerank_results(question, search_results)
    search_results = search_results[:MAX_QDRANT_RESULTS_TO_FETCH]
    search_results = filter_duplicate_chunks(search_results)

    context_chunks = [hit.payload.get('text', '') for hit in search_results if hit.payload]
    context = "\n---\n".join(context_chunks)
    metadata["context_chunks"] = context_chunks

    prompt = f"Вопрос: {question}\n\nКонтекст:\n{context}\n\nОтвет:"
    answer = await make_llm_request(prompt, max_tokens=512, temperature=0.1)
    if answer:
        final_answer = answer
    else:
        final_answer = "Не удалось получить ответ от LLM."

    metadata["generation_time"] = round(time.time() - start_time, 2)
    return final_answer, metadata
