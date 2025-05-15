import os
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Path
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from database import list_knowledge_base_documents, clear_user_history, get_chat_history_with_metrics
from document_processing import process_document
from rag import ask_question_rag

app = FastAPI(title="RAG API", description="API для RAG системы", version="1.0.0")


class QuestionRequest(BaseModel):
    user_id: int = Field(..., description="ID пользователя")
    question: str = Field(..., description="Вопрос пользователя")


class QuestionResponse(BaseModel):
    answer: str = Field(...)
    metrics: Dict[str, Any] = Field(...)


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    answer, metrics = await ask_question_rag(request.user_id, request.question)
    return QuestionResponse(answer=answer, metrics=metrics)


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    file_path = f"uploads_telegram/{file.filename}"
    os.makedirs("uploads_telegram", exist_ok=True)
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    chunks = await process_document(file_path, file.filename)
    os.remove(file_path)
    if not chunks:
        raise HTTPException(status_code=400, detail="Ошибка обработки файла")
    return {"success": True, "chunks": len(chunks)}


@app.get("/documents")
async def get_documents():
    documents = await list_knowledge_base_documents()
    return {"documents": documents}


@app.delete("/history/{user_id}")
async def clear_history(user_id: int = Path(...)):
    success, message = await clear_user_history(user_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@app.get("/history")
async def view_chat_history():
    chats = await get_chat_history_with_metrics()
    html = "<html><body><h1>История чатов</h1>"
    for chat in chats:
        html += f"<h2>Пользователь {chat['user_id']}</h2>"
        for msg in chat['messages']:
            html += f"<div><b>{msg['role']}:</b> {msg['content']}</div>"
    html += "</body></html>"
    return HTMLResponse(content=html)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
