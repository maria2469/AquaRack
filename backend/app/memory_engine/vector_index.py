"""
CockroachDB Vector Index (SDD Tech Stack: "CockroachDB Vector Index").

CockroachDB (v24.2+) has a native VECTOR(n) column type and a `<=>`
cosine-distance SQL operator, so similarity search can run as real SQL
inside the database rather than pulling every embedding row back into
Python for a manual cosine-similarity scan.

This module:
  1. Ensures a native `vector_native VECTOR(dim)` column exists on
     `embeddings` (idempotent DDL, CockroachDB-only).
  2. Mirrors the JSON `vector` column into `vector_native` on every write
     via `sync_native_vector`.
  3. Runs the actual top-K search with `ORDER BY vector_native <=> :q_vec`
     directly in CockroachDB.

On SQLite (local dev opt-out), all of this is a no-op and the caller
(app.memory_engine.store) transparently falls back to the existing
Python-side cosine-similarity scan — so the same codebase runs on both,
matching the SDD's "same schema, zero code changes" principle.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import IS_COCKROACHDB

logger = logging.getLogger("aquamind.vector_index")

_ensured_dims: set[int] = set()


def ensure_native_vector_column(db: Session, dim: int, table_name: str = "embeddings") -> None:
    """Idempotently add a native VECTOR(dim) column + index on CockroachDB."""
    if not IS_COCKROACHDB or (dim, table_name) in _ensured_dims:
        return
    try:
        db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS vector_native VECTOR({dim})"))
        try:
            db.execute(
                text(
                    f"CREATE VECTOR INDEX IF NOT EXISTS {table_name}_vector_native_idx "
                    f"ON {table_name} (vector_native)"
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("Vector index on %s not created: %s", table_name, exc)
        db.commit()
        _ensured_dims.add((dim, table_name))
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("Could not ensure native vector column on %s: %s", table_name, exc)


def sync_native_vector(db: Session, embedding_id: str, vector: List[float], table_name: str = "embeddings", id_column: str = "embedding_id") -> None:
    """Mirror a JSON vector into the native VECTOR column for CockroachDB search."""
    if not IS_COCKROACHDB:
        return
    ensure_native_vector_column(db, len(vector), table_name=table_name)
    try:
        db.execute(
            text(f"UPDATE {table_name} SET vector_native = :vec WHERE {id_column} = :id"),
            {"vec": str(vector), "id": embedding_id},
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("Could not sync native vector for %s id %s: %s", table_name, embedding_id, exc)


def native_search(db: Session, query_vector: List[float], model_name: str, k: int = 5) -> Optional[List[dict]]:
    """
    Real in-database cosine similarity search via CockroachDB's `<=>`
    operator for memories table.
    """
    if not IS_COCKROACHDB:
        return None
    try:
        rows = db.execute(
            text(
                """
                SELECT m.memory_id, m.type, m.summary_text, m.tier, m.created_at,
                       1 - (e.vector_native <=> :qvec::VECTOR) AS similarity
                FROM embeddings e
                JOIN memories m ON m.memory_id = e.memory_id
                WHERE e.model_name = :model_name AND e.vector_native IS NOT NULL
                ORDER BY e.vector_native <=> :qvec::VECTOR
                LIMIT :k
                """
            ),
            {"qvec": str(query_vector), "model_name": model_name, "k": k},
        ).mappings().all()
        return [
            {
                "memory_id": r["memory_id"],
                "type": r["type"],
                "summary_text": r["summary_text"],
                "tier": r["tier"],
                "created_at": r["created_at"],
                "similarity": round(float(r["similarity"]), 4),
            }
            for r in rows
        ]
    except Exception as exc:  # noqa: BLE001
        logger.info("Native CockroachDB vector search unavailable, falling back to Python scan: %s", exc)
        return None


def native_search_memory_embeddings(db: Session, query_vector: List[float], memory_type: Optional[str] = None, k: int = 5) -> Optional[List[dict]]:
    """
    Native vector search over memory_embeddings table using CockroachDB `<=>` cosine distance.
    """
    if not IS_COCKROACHDB:
        return None
    try:
        type_clause = "AND memory_type = :mtype" if memory_type else ""
        query_sql = f"""
            SELECT id, memory_type, source_id, summary, created_at,
                   1 - (vector_native <=> :qvec::VECTOR) AS similarity
            FROM memory_embeddings
            WHERE vector_native IS NOT NULL {type_clause}
            ORDER BY vector_native <=> :qvec::VECTOR
            LIMIT :k
        """
        params = {"qvec": str(query_vector), "k": k}
        if memory_type:
            params["mtype"] = memory_type
        rows = db.execute(text(query_sql), params).mappings().all()
        return [
            {
                "id": r["id"],
                "memory_type": r["memory_type"],
                "source_id": r["source_id"],
                "summary": r["summary"],
                "created_at": r["created_at"],
                "similarity": round(float(r["similarity"]), 4),
            }
            for r in rows
        ]
    except Exception as exc:  # noqa: BLE001
        logger.info("Native CockroachDB vector search on memory_embeddings unavailable: %s", exc)
        return None

