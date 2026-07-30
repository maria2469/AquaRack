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


def ensure_native_vector_column(db: Session, dim: int) -> None:
    """Idempotently add a native VECTOR(dim) column + index on CockroachDB."""
    if not IS_COCKROACHDB or dim in _ensured_dims:
        return
    try:
        db.execute(text(f"ALTER TABLE embeddings ADD COLUMN IF NOT EXISTS vector_native VECTOR({dim})"))
        # CockroachDB vector indexing (C-SPANN, v25.2+); safe to attempt and
        # ignore if the running cluster version doesn't support indexed
        # vector columns yet — <=> search still works as an unindexed scan.
        try:
            db.execute(
                text(
                    "CREATE VECTOR INDEX IF NOT EXISTS embeddings_vector_native_idx "
                    "ON embeddings (vector_native)"
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("Vector index not created (cluster may not support it yet): %s", exc)
        db.commit()
        _ensured_dims.add(dim)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("Could not ensure native vector column: %s", exc)


def sync_native_vector(db: Session, embedding_id: str, vector: List[float]) -> None:
    """Mirror a JSON vector into the native VECTOR column for CockroachDB search."""
    if not IS_COCKROACHDB:
        return
    ensure_native_vector_column(db, len(vector))
    try:
        db.execute(
            text("UPDATE embeddings SET vector_native = :vec WHERE embedding_id = :id"),
            {"vec": str(vector), "id": embedding_id},
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("Could not sync native vector for embedding %s: %s", embedding_id, exc)


def native_search(db: Session, query_vector: List[float], model_name: str, k: int = 5) -> Optional[List[dict]]:
    """
    Real in-database cosine similarity search via CockroachDB's `<=>`
    operator. Returns None (caller falls back to Python-side scan) if not
    running on CockroachDB or if the native column isn't populated yet.
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
