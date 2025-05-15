from typing import List

from qdrant_client.http.models import ScoredPoint


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    return max(words, chars // 4)


def filter_duplicate_chunks(hits: List[ScoredPoint]) -> List[ScoredPoint]:
    seen_texts = set()
    unique_hits = []

    for hit in hits:
        payload = hit.payload or {}
        chunk_text = payload.get('text', '')
        if chunk_text not in seen_texts:
            seen_texts.add(chunk_text)
            unique_hits.append(hit)

    return unique_hits


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'txt', 'pdf', 'docx'}
