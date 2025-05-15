FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_rag.py .
COPY fastapi_backend.py .
COPY .env .

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8000"] 