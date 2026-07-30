"""
Memory Engine — Stage 3 (store & index) and Stage 4 (retrieve)

Uses CockroachDB native VECTOR search when available and automatically
falls back to Python cosine similarity on SQLite or if native VECTOR
search is unavailable.

The fallback is transaction-safe: if a CockroachDB query fails, the
session is rolled back before continuing so subsequent ORM queries do
not fail with:

    current transaction is aborted
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app import models
from app.memory_engine.embed import cosine_similarity, embed_text
from app.memory_engine import vector_index


# ------------------------------------------------------------------
# Store conversational memory
# ------------------------------------------------------------------

def store_memory(
    db: Session,
    conversation_id: str,
    mem_type: str,
    summary_text: str,
) -> models.Memory:

    memory = models.Memory(
        conversation_id=conversation_id,
        type=mem_type,
        summary_text=summary_text,
        tier="hot",
    )

    db.add(memory)
    db.flush()

    vector, model_name = embed_text(summary_text)

    embedding = models.Embedding(
        memory_id=memory.memory_id,
        vector=vector,
        model_name=model_name,
    )

    db.add(embedding)

    db.commit()

    db.refresh(memory)
    db.refresh(embedding)

    # Sync CockroachDB native VECTOR column (optional)
    try:
        vector_index.sync_native_vector(
            db,
            embedding.embedding_id,
            vector,
        )
    except Exception:
        db.rollback()

    return memory


# ------------------------------------------------------------------
# Default conversation
# ------------------------------------------------------------------

def get_or_create_default_conversation(db: Session) -> str:

    convo = db.query(models.Conversation).first()

    if convo:
        return convo.conversation_id

    convo = models.Conversation(
        user_id="system",
        channel="agent",
    )

    db.add(convo)
    db.commit()
    db.refresh(convo)

    return convo.conversation_id


# ------------------------------------------------------------------
# Search conversation memories
# ------------------------------------------------------------------

def search_memories(
    db: Session,
    query_text: str,
    k: int = 5,
) -> List[dict]:

    query_vector, model_name = embed_text(query_text)

    # -------------------------
    # Native VECTOR search
    # -------------------------
    try:

        native = vector_index.native_search(
            db,
            query_vector,
            model_name,
            k=k,
        )

        if native is not None:
            return native

    except Exception as exc:

        print(f"Native memory search failed: {exc}")
        db.rollback()

    db.rollback()

    # -------------------------
    # Python fallback
    # -------------------------

    rows = (
        db.query(models.Memory, models.Embedding)
        .join(
            models.Embedding,
            models.Embedding.memory_id == models.Memory.memory_id,
        )
        .filter(
            models.Embedding.model_name == model_name
        )
        .all()
    )

    scored = []

    for memory, embedding in rows:

        score = cosine_similarity(
            query_vector,
            embedding.vector,
        )

        scored.append((score, memory))

    scored.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    return [
        {
            "memory_id": memory.memory_id,
            "type": memory.type,
            "summary_text": memory.summary_text,
            "tier": memory.tier,
            "created_at": memory.created_at,
            "similarity": round(score, 4),
        }
        for score, memory in scored[:k]
    ]


# ------------------------------------------------------------------
# Store Enterprise Memory
# ------------------------------------------------------------------

def store_memory_embedding(
    db: Session,
    memory_type: str,
    source_id: str,
    summary: str,
) -> models.MemoryEmbedding:

    vector, _ = embed_text(summary)

    mem = models.MemoryEmbedding(
        memory_type=memory_type,
        source_id=source_id,
        embedding=vector,
        summary=summary,
    )

    db.add(mem)
    db.commit()
    db.refresh(mem)

    # Sync native VECTOR column (optional)
    try:

        vector_index.sync_native_vector(
            db=db,
            row_id=mem.id,
            vector=vector,
        )

    except Exception:

        db.rollback()

    return mem


# ------------------------------------------------------------------
# Search Enterprise Memory
# ------------------------------------------------------------------

def search_memory_embeddings(
    db: Session,
    query_text: str,
    memory_type: Optional[str] = None,
    k: int = 5,
) -> List[dict]:
    """
    Search memory_embeddings.

    Order of execution:

        1. CockroachDB native VECTOR search

        2. Python cosine similarity fallback
    """

    query_vector, _ = embed_text(query_text)

    # ---------------------------------------------------
    # Native CockroachDB VECTOR search
    # ---------------------------------------------------

    try:

        native = vector_index.native_search_memory_embeddings(
            db=db,
            query_vector=query_vector,
            memory_type=memory_type,
            k=k,
        )

        if native is not None:
            return native

    except Exception as exc:

        print(f"Native vector search failed: {exc}")

        db.rollback()

    # Important:
    # If CockroachDB produced any SQL error,
    # rollback before running ORM queries.

    db.rollback()

    # ---------------------------------------------------
    # Python cosine similarity fallback
    # ---------------------------------------------------

    query = db.query(models.MemoryEmbedding)

    if memory_type:

        query = query.filter(
            models.MemoryEmbedding.memory_type == memory_type
        )

    rows = query.all()

    scored = []

    for row in rows:

        score = cosine_similarity(
            query_vector,
            row.embedding,
        )

        scored.append((score, row))

    scored.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    return [
        {
            "id": row.id,
            "memory_type": row.memory_type,
            "source_id": row.source_id,
            "summary": row.summary,
            "created_at": row.created_at,
            "similarity": round(score, 4),
        }
        for score, row in scored[:k]
    ]