"""
Memory Engine — Stage 2b: embedding (SDD Section 11.2 / 15.2).
Default: local, zero-cost, deterministic hashed bag-of-words embedding
(768-dim) — no model download, no network required.
If OLLAMA_ENABLED=true and the Ollama call succeeds, embeddings are
generated via a real semantic model instead.

FIX: embed_text() now logs explicitly which path produced the vector
(semantic Ollama vs. non-semantic local hash), and no longer returns
LOCAL_MODEL_NAME "silently" — a caller reading model_name in logs can
now tell whether retrieval quality can be trusted as semantic.
Root cause note: hashed bag-of-words has near-zero semantic generalization
-- "evaporative cooling" and "water flow" share no tokens, so it can only
match on literal vocabulary overlap. Combined with near-identical templated
summaries (see summarize.py fix), this is what produces flat, near-equal
similarity scores across unrelated memories.
"""
import hashlib
import math
import re
import logging
from typing import List, Dict, Optional

from app.config import settings

LOCAL_EMBED_DIM = 768
LOCAL_MODEL_NAME = "local-hashed-bow-768-v1"

_token_re = re.compile(r"[a-zA-Z0-9_]+")
logger = logging.getLogger(__name__)

_embedding_cache: Dict[str, List[float]] = {}


def _tokenize(text: str) -> List[str]:
    return _token_re.findall(text.lower())


def _local_embed(text: str, dim: int = LOCAL_EMBED_DIM) -> List[float]:
    """Deterministic hashed bag-of-words embedding. NOT semantic -- see module
    docstring. Kept as the offline zero-cost fallback, but every call site
    that ends up here now logs it (see embed_text)."""
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
    from app.agents.langchain_groq import embed_text_ollama

    return embed_text_ollama(text)


def embed_text(text: str):
    """Returns (vector, model_name_used).

    FIX: every fallback path is now logged so degraded (non-semantic)
    retrieval is visible in logs instead of silent.
    """
    if settings.OLLAMA_ENABLED:
        if text in _embedding_cache:
            return _embedding_cache[text], settings.OLLAMA_EMBED_MODEL
        try:
            vector = _ollama_embed(text)
            if vector:
                _embedding_cache[text] = vector
                return vector, settings.OLLAMA_EMBED_MODEL
            logger.warning(
                "Ollama embedding returned empty result for text (len=%d); "
                "falling back to non-semantic local hash embedding.",
                len(text),
            )
        except Exception as e:
            logger.error(
                "Ollama embedding failed (%s); falling back to non-semantic "
                "local hash embedding. Retrieval quality will be degraded "
                "until this is resolved.",
                e,
            )
    else:
        logger.warning(
            "OLLAMA_ENABLED is False -- using non-semantic local hash embedding "
            "(%s). Similarity scores will reflect literal token overlap only, "
            "not meaning.",
            LOCAL_MODEL_NAME,
        )
    return _local_embed(text), LOCAL_MODEL_NAME


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)