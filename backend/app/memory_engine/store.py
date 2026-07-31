"""
Vector memory storage/search for RackPulse.
"""
import logging
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app import models
from app.memory_engine.embed import embed_text  # FIX: use the real embed_text
                                                   # from embed.py -- do not
                                                   # redefine/placeholder it here

logger = logging.getLogger("aquamind.memory_store")


def native_search_memory_embeddings(
    db: Session, query_vector: List[float], memory_type: str, k: int
) -> List[Dict[str, Any]]:
    """Delegates to the real implementation in vector_index.py -- that file
    already has the correct SQL, NULL-handling, and count_unsynced_vectors
    diagnostics. Keeping two versions of this function is exactly the kind
    of drift that caused the original bug."""
    from app.memory_engine.vector_index import native_search_memory_embeddings as _native
    return _native(db, query_vector, memory_type, k)


def _python_cosine_fallback(
    db: Session, query_vector: List[float], memory_type: str, k: int
) -> List[Dict[str, Any]]:
    logger.warning("Using Python cosine fallback")
    from app.memory_engine.embed import cosine_similarity

    rows = (
        db.query(models.AgentMemory)
        .filter(models.AgentMemory.memory_type == memory_type)
        .all()
    )
    if not rows:
        return []

    scored = [
        {
            "id": r.id,
            "source_id": r.source_id,
            "summary": r.summary,
            "created_at": r.created_at,
            "similarity": cosine_similarity(query_vector, r.embedding),
        }
        for r in rows
    ]
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:k]


def search_memory_embeddings(
    db: Session, query_text: str, memory_type: str, k: int = 5
) -> Dict[str, Any]:
    query_vector, model_name = embed_text(query_text)  # FIX: real embed_text now
                                                          # returns (vector, model_name)

    try:
        matches = native_search_memory_embeddings(db, query_vector, memory_type, k)
        retrieval_method = "cockroach_vector" if matches else None
        if matches is None:
            raise RuntimeError("native search unavailable")
    except Exception as exc:
        logger.warning("Native VECTOR search failed (%s); falling back to Python cosine.", exc)
        matches = _python_cosine_fallback(db, query_vector, memory_type, k)
        retrieval_method = "python_cosine_fallback"

    total = db.query(models.AgentMemory).filter(models.AgentMemory.memory_type == memory_type).count()

    return {
        "matches": matches,
        "retrieval_method": retrieval_method,
        "embedding_model": model_name,  # FIX: report the *actual* model used
                                          # this request, not a hardcoded constant
        "searched_records": total,
    }


def store_memory_embedding(
    db: Session, memory_type: str, source_id: str, summary: str
) -> "models.AgentMemory":
    vector, model_name = embed_text(summary)
    row = models.AgentMemory(
        memory_type=memory_type,
        source_id=source_id,
        summary=summary,
        embedding=vector,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    from app.memory_engine.vector_index import sync_native_vector
    try:
        sync_native_vector(db, row_id=row.id, vector=vector)
    except Exception:
        # already logged with full context inside sync_native_vector;
        # row still exists with a valid embedding column, just not yet
        # mirrored into vector_native for native search
        pass

    return row