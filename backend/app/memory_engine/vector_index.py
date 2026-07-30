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
        logger.warning(e)


def sync_native_vector(
    db: Session,
    row_id,
    vector: List[float],
):
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
        logger.warning(e)


def native_search_memory_embeddings(
    db: Session,
    query_vector: List[float],
    memory_type: Optional[str] = None,
    k: int = 5,
):
    """
    Native CockroachDB VECTOR search.

    Returns None if unavailable.
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