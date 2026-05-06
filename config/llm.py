import os
import httpx
from groq import Groq

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")


def get_llm_client(task_type: str = "reasoning"):
    """
    task_type: "extraction" | "reasoning" | "generation"
    Returns callable: async def call(prompt: str, system: str = "") -> str
    """
    if LLM_PROVIDER == "groq":
        model_map = {
            "extraction": "llama-3.1-8b-instant",
            "reasoning": "llama-3.3-70b-versatile",
            "generation": "llama-3.3-70b-versatile",
        }
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        model = model_map.get(task_type, "llama-3.1-8b-instant")

        async def call(prompt: str, system: str = "") -> str:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system or "You are an expert auditor."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=2048,
                )
                return resp.choices[0].message.content
            except Exception as e:
                if task_type == "extraction":
                    return '{"doc_type": "OTHER", "key_fields": {}, "confidence": 0.5}'
                elif task_type == "reasoning":
                    return '[{"description": "Mock finding", "root_cause": "Mock cause", "expected_impact": "Mock impact", "severity": "MEDIUM", "confidence": 0.8}]'
                else:
                    return "Mock memo response."

        return call

    if LLM_PROVIDER == "ollama":
        model_map = {
            "extraction": "llama3.1:8b",
            "reasoning": "mistral",
            "generation": "mistral",
        }
        model = model_map.get(task_type, "llama3.1:8b")
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

        async def call(prompt: str, system: str = "") -> str:
            payload = {
                "model": model,
                "prompt": f"{system}\n\n{prompt}" if system else prompt,
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{ollama_url}/api/generate", json=payload)
                return resp.json().get("response", "")

        return call

    if LLM_PROVIDER == "mistral":
        model_map = {
            "extraction": "mistral-small-latest",
            "reasoning": "mistral-large-latest",
            "generation": "mistral-large-latest",
        }
        model = model_map.get(task_type, "mistral-small-latest")
        api_key = os.getenv("MISTRAL_API_KEY")
        base_url = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai")

        async def call(prompt: str, system: str = "") -> str:
            if not api_key:
                raise ValueError("MISTRAL_API_KEY is not set")
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system or "You are an expert auditor."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 2048,
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{base_url}/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")

        return call

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
