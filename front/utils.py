import httpx
from config import FASTAPI_BASE_URL

def get_fastapi_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=FASTAPI_BASE_URL, timeout=30.0) 