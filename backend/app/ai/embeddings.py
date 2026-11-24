import hashlib
import math
import re

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.ai import EMBEDDING_DIM


def _fit(vector: list[float]) -> list[float]:
    if len(vector) > EMBEDDING_DIM:
        vector = vector[:EMBEDDING_DIM]
    elif len(vector) < EMBEDDING_DIM:
        vector = vector + [0.0] * (EMBEDDING_DIM - len(vector))
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def local_embed(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "little") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    for left, right in zip(tokens, tokens[1:]):
        digest = hashlib.sha256(f"{left}_{right}".encode()).digest()
        index = int.from_bytes(digest[:4], "little") % EMBEDDING_DIM
        vector[index] += 0.5
    return _fit(vector)


def _gemini_embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if not settings.gemini_api_key.strip():
        raise AppError("GEMINI_API_KEY is empty, so Gemini embeddings are unavailable.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_embedding_model}:batchEmbedContents"
    body = {
        "requests": [
            {
                "model": f"models/{settings.gemini_embedding_model}",
                "content": {"parts": [{"text": text[:8000]}]},
                "outputDimensionality": EMBEDDING_DIM,
            }
            for text in texts
        ]
    }
    response = httpx.post(url, json=body, headers={"x-goog-api-key": settings.gemini_api_key.strip()}, timeout=60)
    if response.status_code >= 400:
        raise AppError("The embedding provider rejected the request.", 502)
    data = response.json()
    vectors = [item.get("values") for item in data.get("embeddings", [])]
    if len(vectors) != len(texts) or any(not vector for vector in vectors):
        raise AppError("The embedding provider returned an unexpected response.", 502)
    return [_fit([float(value) for value in vector]) for vector in vectors]


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    model = settings.ollama_model.strip()
    if not model:
        raise AppError("OLLAMA_MODEL is empty, so Ollama embeddings are unavailable.")
    url = settings.ollama_base_url.rstrip("/") + "/api/embed"
    response = httpx.post(url, json={"model": model, "input": texts}, timeout=60)
    if response.status_code >= 400:
        raise AppError("Ollama embeddings are unavailable.", 502)
    vectors = response.json().get("embeddings") or []
    if len(vectors) != len(texts):
        raise AppError("Ollama returned an unexpected embedding response.", 502)
    return [_fit([float(value) for value in vector]) for vector in vectors]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    provider = get_settings().embedding_provider.strip().lower() or "local"
    if provider == "gemini":
        return _gemini_embed(texts)
    if provider == "ollama":
        return _ollama_embed(texts)
    return [local_embed(text) for text in texts]
