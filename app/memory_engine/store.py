"""
Memory Engine — Stage 3 (store & index) and Stage 4 (retrieve), SDD Section
11.3/11.4 / Tech Stack ("CockroachDB Vector Index").

Runs against CockroachDB in production (or SQLite for local/offline dev,
via DATABASE_URL). On CockroachDB, similarity search uses a real native
VECTOR column + the `<=>` cosine-distance SQL operator (see
app.memory_engine.vector_index) so search happens in the database, not in
a Python-side loop. On SQLite, the same call transparently falls back to
an in-Python cosine-similarity scan — same schema, same call sites, per
SDD Section 4.4/9.
"""
from typing import List

from sqlalchemy.orm import Session

from app import models
from app.memory_engine.embed import embed_text, cosine_similarity
from app.memory_engine import vector_index


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
    db.flush()  # get memory_id without committing yet
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

    # Mirror into CockroachDB's native VECTOR column for real in-DB search
    # (no-op on SQLite).
    vector_index.sync_native_vector(db, embedding.embedding_id, vector)

    return memory


def get_or_create_default_conversation(db: Session) -> str:
    convo = db.query(models.Conversation).first()
    if convo:
        return convo.conversation_id
    convo = models.Conversation(user_id="system", channel="agent")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo.conversation_id


def search_memories(db: Session, query_text: str, k: int = 5) -> List[dict]:
    query_vec, model_name = embed_text(query_text)

    # Prefer a real in-database vector search (CockroachDB `<=>` operator).
    native_results = vector_index.native_search(db, query_vec, model_name, k=k)
    if native_results is not None:
        return native_results

    # Fallback: Python-side cosine-similarity scan (SQLite / no native
    # vector column yet / cluster doesn't support VECTOR).
    rows = (
        db.query(models.Memory, models.Embedding)
        .join(models.Embedding, models.Embedding.memory_id == models.Memory.memory_id)
        .filter(models.Embedding.model_name == model_name)
        .all()
    )
    scored = []
    for memory, embedding in rows:
        sim = cosine_similarity(query_vec, embedding.vector)
        scored.append((sim, memory))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:k]
    return [
        {
            "memory_id": m.memory_id,
            "type": m.type,
            "summary_text": m.summary_text,
            "tier": m.tier,
            "created_at": m.created_at,
            "similarity": round(sim, 4),
        }
        for sim, m in top
    ]


def store_memory_embedding(
    db: Session,
    memory_type: str,
    source_id: str,
    summary: str,
) -> models.MemoryEmbedding:
    """Store an enterprise vector embedding in memory_embeddings table."""
    vector, _ = embed_text(summary)
    mem_emb = models.MemoryEmbedding(
        memory_type=memory_type,
        source_id=source_id,
        embedding=vector,
        summary=summary,
    )
    db.add(mem_emb)
    db.commit()
    db.refresh(mem_emb)
    vector_index.sync_native_vector(db, mem_emb.id, vector, table_name="memory_embeddings", id_column="id")
    return mem_emb


def search_memory_embeddings(
    db: Session,
    query_text: str,
    memory_type: str = None,
    k: int = 5,
) -> List[dict]:
    """Search memory_embeddings table semantically using CockroachDB vector index or fallback cosine similarity."""
    query_vec, _ = embed_text(query_text)
    native_res = vector_index.native_search_memory_embeddings(db, query_vec, memory_type=memory_type, k=k)
    if native_res is not None:
        return native_res

    # Python fallback scan
    q = db.query(models.MemoryEmbedding)
    if memory_type:
        q = q.filter(models.MemoryEmbedding.memory_type == memory_type)
    rows = q.all()
    scored = []
    for r in rows:
        sim = cosine_similarity(query_vec, r.embedding)
        scored.append((sim, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:k]
    return [
        {
            "id": r.id,
            "memory_type": r.memory_type,
            "source_id": r.source_id,
            "summary": r.summary,
            "created_at": r.created_at,
            "similarity": round(sim, 4),
        }
        for sim, r in top
    ]

