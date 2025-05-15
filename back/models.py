from typing import List, Dict, Any

from pydantic import BaseModel, Field


class RAGMetrics(BaseModel):
    relevance_scores: List[float]
    context_tokens: int
    used_chunks: int
    generation_time: float
    answer_tokens: int
    average_relevance_score: float
    context_chunks: List[str]
    qdrant_filters: List[str]

    class Config:
        from_attributes = True


class QuestionRequest(BaseModel):
    user_id: int = Field(..., description="Уникальный идентификатор пользователя")
    question: str = Field(..., description="Текст вопроса пользователя")


class QuestionResponse(BaseModel):
    answer: str = Field(..., description="Ответ на вопрос пользователя")
    metrics: Dict[str, Any] = Field(..., description="Метрики обработки запроса")


class DocumentResponse(BaseModel):
    documents: List[Dict[str, Any]] = Field(..., description="Список документов в базе знаний")


class DeleteResponse(BaseModel):
    success: bool = Field(..., description="Статус успешности операции")
    message: str = Field(..., description="Сообщение о результате операции")


class ClearHistoryResponse(BaseModel):
    success: bool = Field(..., description="Статус успешности операции")
    message: str = Field(..., description="Сообщение о результате операции")
