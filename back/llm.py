from typing import List, Optional, Dict, Any

import httpx

from config import OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL_NAME, VALID_CATEGORIES


async def make_llm_request(prompt: str, max_tokens: int, temperature: float, stop: Optional[List[str]] = None) -> \
        Optional[str]:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    messages_payload = [{"role": "user", "content": prompt}]
    payload: Dict[str, Any] = {"model": OPENAI_MODEL_NAME, "messages": messages_payload, "max_tokens": max_tokens,
                               "temperature": temperature, "stream": False}
    if stop:
        payload["stop"] = stop

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{OPENAI_API_BASE}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            llm_response_data = response.json()
        if llm_response_data and 'choices' in llm_response_data and llm_response_data['choices']:
            choice = llm_response_data['choices'][0]
            if 'message' in choice and isinstance(choice['message'], dict) and 'content' in choice['message']:
                return choice['message']['content'].strip()
            elif 'text' in choice:
                return choice['text'].strip()
        return None
    except Exception as e:
        print(f"LLM request error: {e}")
        return None


async def classify_question_llm(question: str) -> str:
    prompt = f"""You are an expert in question classification. Determine the most appropriate category for the following employee question. Choose ONLY ONE category from the list below and write ONLY ITS NAME in your response. DO NOT ADD any other words or explanations.\n\nCategories and their descriptions:\n1. Lookup: Searching for specific information.\n2. Calculation: Performing calculations.\n\nEmployee question: \"{question}\"\nCategory:"""
    default_category = "Lookup"
    try:
        result = await make_llm_request(prompt, max_tokens=20, temperature=0.0, stop=["\n", "."])
        if result:
            cleaned = result.strip().replace('"', '').replace("'", "").replace('*', '').replace('.', '').split('\n')[
                0].strip()
            if cleaned in VALID_CATEGORIES:
                return cleaned
        return default_category
    except Exception:
        return default_category


async def enrich_query_with_llm(question: str) -> str:
    prompt = f"You are an expert in information search. Transform the user's question into an effective search query. Please provide the response in Russian.\nUser question: \"{question}\"\nEffective search query:"
    try:
        enriched = await make_llm_request(prompt, max_tokens=60, temperature=0.0, stop=["\n"])
        if enriched and len(enriched) > 3:
            cleaned = enriched.strip().replace('"', '').replace("'", "").replace("Improved query:", "").strip()
            if cleaned.lower() != question.lower():
                return cleaned
        return question
    except Exception:
        return question
