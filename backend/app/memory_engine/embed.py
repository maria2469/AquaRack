"""
Memory Engine — Stage 2b: embedding (SDD Section 11.2 / 15.2).
Default: local, zero-cost, deterministic hashed bag-of-words embedding
(384-dim) — no model download, no network required. This keeps Phase 1
"fully self-contained... does not require... AWS production infrastructure"
(SDD Section 1).
If BEDROCK_ENABLED=true and boto3/credentials are available, embeddings are
generated via Amazon Bedrock Titan Text Embeddings V2 instead.
"""
import hashlib
import math
import re
import time
import logging
from typing import List, Dict, Optional
from functools import lru_cache

from app.config import settings

LOCAL_EMBED_DIM = 384
LOCAL_MODEL_NAME = "local-hashed-bow-v1"

_token_re = re.compile(r"[a-zA-Z0-9_]+")
logger = logging.getLogger(__name__)

# In-process cache to avoid redundant Bedrock calls
_embedding_cache: Dict[str, List[float]] = {}


def _tokenize(text: str) -> List[str]:
    return _token_re.findall(text.lower())


def _local_embed(text: str, dim: int = LOCAL_EMBED_DIM) -> List[float]:
    """
    Deterministic hashed bag-of-words embedding: each token is hashed into
    a bucket and contributes +1/-1 (sign from a second hash) to that
    dimension, producing a stable, offline, zero-cost vector suitable for
    cosine-similarity retrieval. Not a semantic model, but consistent and
    good enough to demonstrate the RAG loop end-to-end (Phase 1 goal).
    """
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


def _ollama_embed(text: str) -> Optional[List[float]]:
    """Ollama vector embedding via LangChain OllamaEmbeddings wrapper."""
    from app.agents.langchain_ollama import embed_text_ollama

    return embed_text_ollama(text)


def embed_text(text: str):
    """Returns (vector, model_name_used). Falls back to local embedding on any error."""
    if settings.OLLAMA_ENABLED:
        if text in _embedding_cache:
            return _embedding_cache[text], settings.OLLAMA_EMBED_MODEL
        try:
            vector = _ollama_embed(text)
            if vector:
                _embedding_cache[text] = vector
                return vector, settings.OLLAMA_EMBED_MODEL
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}. Falling back to local.")
            pass
    return _local_embed(text), LOCAL_MODEL_NAME


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
