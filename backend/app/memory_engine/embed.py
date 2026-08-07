"""
Memory Engine — embedding (SDD Section 11.2 / 15.2).
Primary: Cohere embed API (semantic). Fallback: local hashed bag-of-words
(non-semantic, offline, zero-cost).
"""
import hashlib
import math
import re
import logging
from typing import List, Dict, Optional
from functools import lru_cache

import cohere

from app.config import settings

TARGET_EMBED_DIM = getattr(settings, "EMBEDDING_DIM", 1024)
LOCAL_EMBED_DIM = TARGET_EMBED_DIM
LOCAL_MODEL_NAME = f"local-hashed-bow-{TARGET_EMBED_DIM}-v1"

_token_re = re.compile(r"[a-zA-Z0-9_]+")
logger = logging.getLogger(__name__)

# Use LRU cache with size limit to prevent unbounded memory growth
@lru_cache(maxsize=1000)
def _get_cached_embedding(text: str, input_type: str) -> Optional[List[float]]:
    """Cached embedding function with LRU eviction policy."""
    if settings.COHERE_ENABLED and settings.COHERE_API_KEY:
        try:
            vec = _cohere_embed(text, input_type)
            if vec:
                return vec
        except Exception as e:
            logger.warning("Cohere embedding failed: %s", e)
    return _local_embed(text, LOCAL_EMBED_DIM)

_cohere_client: Optional[cohere.Client] = None


def _get_cohere_client() -> Optional[cohere.Client]:
    global _cohere_client
    if _cohere_client is None and settings.COHERE_API_KEY:
        _cohere_client = cohere.Client(settings.COHERE_API_KEY)
    return _cohere_client


def _tokenize(text: str) -> List[str]:
    return _token_re.findall(text.lower())


def _normalize_dimension(vec: List[float], target_dim: int = TARGET_EMBED_DIM) -> List[float]:
    """Ensures vector is exactly target_dim length (pads with 0.0 or truncates if needed)."""
    if len(vec) == target_dim:
        return vec
    if len(vec) < target_dim:
        return vec + [0.0] * (target_dim - len(vec))
    return vec[:target_dim]


def _local_embed(text: str, dim: int = TARGET_EMBED_DIM) -> List[float]:
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for tok in tokens:
        h = hashlib.md5(tok.encode("utf-8")).hexdigest()
        idx = int(h[:8], 16) % dim
        sign = 1.0 if int(h[8:9], 16) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cohere_embed(text: str, input_type: str = "search_document") -> Optional[List[float]]:
    client = _get_cohere_client()
    if not client:
        return None
    response = client.embed(
        texts=[text],
        model=settings.COHERE_EMBED_MODEL,
        input_type=input_type,
    )
    raw_vec = response.embeddings[0]
    return _normalize_dimension(raw_vec, TARGET_EMBED_DIM)


def embed_text(text: str, input_type: str = "search_document"):
    """Returns (vector, model_name_used) with guaranteed 1024 dimensions using LRU cache."""
    # Use the cached function with LRU eviction
    vector = _get_cached_embedding(text, input_type)
    model_name = settings.COHERE_EMBED_MODEL if (settings.COHERE_ENABLED and settings.COHERE_API_KEY) else LOCAL_MODEL_NAME
    return vector, model_name


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)