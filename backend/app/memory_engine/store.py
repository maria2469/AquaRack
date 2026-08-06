"""
Vector memory storage/search for RackPulse.
"""
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
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
        db.query(models.MemoryEmbedding)
        .filter(models.MemoryEmbedding.memory_type == memory_type)
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
    query_vector, model_name = embed_text(query_text)

    try:
        matches = native_search_memory_embeddings(db, query_vector, memory_type, k)
        if matches is None:
            raise RuntimeError("native search unavailable")
        retrieval_method = "cockroach_vector"
    except Exception as exc:
        logger.warning("Native VECTOR search failed (%s); falling back to Python cosine.", exc)
        matches = _python_cosine_fallback(db, query_vector, memory_type, k)
        retrieval_method = "python_cosine_fallback"

    total = db.query(models.MemoryEmbedding).filter(models.MemoryEmbedding.memory_type == memory_type).count()

    return {
        "matches": matches,
        "retrieval_method": retrieval_method,
        "embedding_model": model_name,
        "searched_records": total,
    }


def search_memory_embeddings_hybrid(
    db: Session,
    query_text: str,
    memory_type: str = "incident",
    rack_id: Optional[str] = None,
    min_severity: Optional[str] = None,
    time_range_hours: Optional[int] = None,
    k: int = 5,
) -> Dict[str, Any]:
    """Hybrid Vector + Structured Search with fallback to standard vector/cosine search."""
    query_vector, model_name = embed_text(query_text)

    from app.memory_engine.vector_index import native_hybrid_search_memory_embeddings
    try:
        matches = native_hybrid_search_memory_embeddings(
            db,
            query_vector=query_vector,
            memory_type=memory_type,
            rack_id=rack_id,
            min_severity=min_severity,
            time_range_hours=time_range_hours,
            k=k,
        )
        if matches is not None:
            return {
                "matches": matches,
                "retrieval_method": "cockroach_hybrid_vector",
                "embedding_model": model_name,
                "searched_records": len(matches),
            }
    except Exception as exc:
        logger.warning("Native hybrid search failed: %s; falling back.", exc)

    # Fallback to standard vector search
    return search_memory_embeddings(db, query_text=query_text, memory_type=memory_type, k=k)



def store_memory_embedding(
    db: Session, memory_type: str, source_id: str, summary: str
) -> "models.MemoryEmbedding":
    vector, model_name = embed_text(summary)
    row = models.MemoryEmbedding(
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


def search_memories(db: Session, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
    """Backward compatibility helper for /api/v1/memory/search."""
    res = search_memory_embeddings(db, query_text=query_text, memory_type="recommendation", k=k)
    matches = res.get("matches", [])
    if not matches:
        res_inc = search_memory_embeddings(db, query_text=query_text, memory_type="incident", k=k)
        matches = res_inc.get("matches", [])
    results = []
    for m in matches:
        created = m.get("created_at")
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except Exception:
                created = datetime.utcnow()
        elif not created:
            created = datetime.utcnow()

        results.append({
            "memory_id": m.get("id", m.get("source_id", "")),
            "type": m.get("memory_type", "recommendation"),
            "summary_text": m.get("summary", ""),
            "tier": "hot",
            "similarity": m.get("similarity") or 0.9,
            "created_at": created,
        })
    return results