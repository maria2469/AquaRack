from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import IS_COCKROACHDB

logger = logging.getLogger("aquamind.vector_index")

_ensured = set()


def ensure_native_vector_column(
    db: Session,
    dim: int,
    table_name: str = "memory_embeddings",
):
    if not IS_COCKROACHDB:
        return

    key = (table_name, dim)

    if key in _ensured:
        return

    try:

        db.execute(
            text(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN IF NOT EXISTS vector_native VECTOR({dim})
                """
            )
        )

        db.execute(
            text(
                f"""
                CREATE VECTOR INDEX IF NOT EXISTS
                {table_name}_vector_idx
                ON {table_name}(vector_native)
                """
            )
        )

        db.commit()

        _ensured.add(key)

    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to ensure native vector column/index on %s (dim=%d): %s. "
            "Native VECTOR search will keep failing until this is fixed.",
            table_name, dim, e,
        )


def sync_native_vector(
    db: Session,
    row_id,
    vector: List[float],
):
    """FIX: this previously swallowed all failures behind a bare warning, so
    vector_native could silently stay NULL for an unbounded number of rows,
    shrinking the native-search candidate pool without any visible signal.
    Now raises after logging, so callers (store_memory / store_memory_embedding)
    can decide whether to surface this to a caller/metrics rather than have it
    disappear into a log line no one is watching."""
    if not IS_COCKROACHDB:
        return

    ensure_native_vector_column(db, len(vector))

    try:

        db.execute(
            text(
                """
                UPDATE memory_embeddings
                SET vector_native = CAST(:vec AS VECTOR)
                WHERE id=:id
                """
            ),
            {
                "vec": str(vector),
                "id": row_id,
            },
        )

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to sync vector_native for memory_embeddings.id=%s: %s. "
            "This row will be invisible to native VECTOR search until re-synced.",
            row_id, e,
        )
        raise


def count_unsynced_vectors(db: Session, memory_type: Optional[str] = None) -> int:
    """NEW: lets you check, on demand, how many rows are missing vector_native
    -- i.e. how degraded your native-search candidate pool currently is.
    Call this from a health-check endpoint or before trusting a demo run."""
    if not IS_COCKROACHDB:
        return 0
    sql = "SELECT count(*) FROM memory_embeddings WHERE vector_native IS NULL"
    params = {}
    if memory_type:
        sql += " AND memory_type = :mtype"
        params["mtype"] = memory_type
    try:
        return db.execute(text(sql), params).scalar_one()
    except Exception as e:
        db.rollback()
        logger.warning("count_unsynced_vectors failed: %s", e)
        return -1


def native_search_memory_embeddings(
    db: Session,
    query_vector: List[float],
    memory_type: Optional[str] = None,
    k: int = 5,
):
    """
    Native CockroachDB VECTOR search.

    Returns None if unavailable (caller falls back to Python cosine).
    """

    if not IS_COCKROACHDB:
        return None

    try:

        sql = """
        SELECT
            id,
            memory_type,
            source_id,
            summary,
            created_at,
            1 - (
                vector_native <=> CAST(:vec AS VECTOR)
            ) AS similarity
        FROM memory_embeddings
        WHERE vector_native IS NOT NULL
        """

        params = {
            "vec": str(query_vector),
            "k": k,
        }

        if memory_type:
            sql += " AND memory_type=:mtype"
            params["mtype"] = memory_type

        sql += """
        ORDER BY vector_native <=> CAST(:vec AS VECTOR)
        LIMIT :k
        """

        rows = (
            db.execute(text(sql), params)
            .mappings()
            .all()
        )

        if not rows:
            unsynced = count_unsynced_vectors(db, memory_type)
            logger.warning(
                "Native VECTOR search returned 0 rows for memory_type=%s "
                "(unsynced rows currently NULL: %s). Caller will fall back "
                "to Python cosine over the same underlying table.",
                memory_type, unsynced,
            )

        return [
            {
                "id": r["id"],
                "memory_type": r["memory_type"],
                "source_id": r["source_id"],
                "summary": r["summary"],
                "created_at": r["created_at"],
                "similarity": float(r["similarity"]),
            }
            for r in rows
        ]

    except Exception as e:

        db.rollback()

        logger.warning(
            "Native vector search failed. Falling back. %s",
            e,
        )

        return None


def native_hybrid_search_memory_embeddings(
    db: Session,
    query_vector: List[float],
    memory_type: Optional[str] = None,
    rack_id: Optional[str] = None,
    min_severity: Optional[str] = None,
    time_range_hours: Optional[int] = None,
    k: int = 5,
):
    """
    Hybrid Vector + Structured Search in CockroachDB.
    Combines vector cosine similarity with structured SQL predicates:
      - memory_type filtering
      - incident severity / metadata joins
      - time range window filtering (NOW() - INTERVAL 'X hours')
    """
    if not IS_COCKROACHDB:
        return None

    try:
        sql = """
        SELECT
            m.id,
            m.memory_type,
            m.source_id,
            m.summary,
            m.created_at,
            1 - (
                m.vector_native <=> CAST(:vec AS VECTOR)
            ) AS similarity
        FROM memory_embeddings m
        """

        joins = []
        where_clauses = ["m.vector_native IS NOT NULL"]
        params = {"vec": str(query_vector), "k": k}

        if memory_type:
            where_clauses.append("m.memory_type = :mtype")
            params["mtype"] = memory_type

        if time_range_hours:
            where_clauses.append(f"m.created_at >= NOW() - INTERVAL '{int(time_range_hours)} hours'")

        if min_severity and (memory_type == "incident" or not memory_type):
            joins.append("LEFT JOIN incidents i ON m.source_id = i.incident_id")
            where_clauses.append("i.severity = :severity")
            params["severity"] = min_severity

        if rack_id:
            # If joined with telemetry or incidents
            if "incidents i" not in " ".join(joins):
                joins.append("LEFT JOIN incidents i ON m.source_id = i.incident_id")
            joins.append("LEFT JOIN telemetry t ON i.telemetry_id = t.telemetry_id")
            where_clauses.append("(t.rack_id = :rack_id OR m.summary LIKE :rack_pattern)")
            params["rack_id"] = rack_id
            params["rack_pattern"] = f"%{rack_id}%"

        full_sql = f"{sql} {' '.join(joins)} WHERE {' AND '.join(where_clauses)} ORDER BY m.vector_native <=> CAST(:vec AS VECTOR) LIMIT :k"

        rows = db.execute(text(full_sql), params).mappings().all()

        return [
            {
                "id": r["id"],
                "memory_type": r["memory_type"],
                "source_id": r["source_id"],
                "summary": r["summary"],
                "created_at": r["created_at"],
                "similarity": float(r["similarity"]),
            }
            for r in rows
        ]
    except Exception as exc:
        db.rollback()
        logger.warning("Native hybrid vector search failed: %s. Falling back.", exc)
        return None