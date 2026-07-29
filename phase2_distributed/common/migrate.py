"""
Phase 2 startup migration helper.

Phase 2's new tables (sites, simulation_jobs, recommendation_feedback,
cdc_export_log) are created via the normal `Base.metadata.create_all()`
call, same as Phase 1 (SDD Section 9 closing note: schema carries forward
without migration).

The one safety-net this module adds: if a developer already has an
*existing* aquamind_phase1.db created before `site_id` was added to the
`racks` / `telemetry` tables, `create_all()` alone won't retrofit that
column onto an existing table. This runs a lightweight ALTER TABLE ADD
COLUMN for exactly that case (no-op if the column already exists, e.g. on
a fresh database or one already using the Phase 2 models).

In production (Section 21.2), Phase 2 promotes this to versioned Alembic
migrations; this lightweight approach is sufficient for local/dev use.
"""
from sqlalchemy import inspect, text

import phase2_distributed.common.pathsetup  # noqa: F401
from app.database import engine, Base

# Ensure all model classes (Phase 1 + Phase 2) are registered on Base before create_all().
from app import models  # noqa: F401
from phase2_distributed.common import models_ext  # noqa: F401


def _add_column_if_missing(table: str, column: str, coltype: str = "VARCHAR") -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return  # table doesn't exist yet — create_all() will create it with the column already present
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


def run_migrations() -> None:
    Base.metadata.create_all(bind=engine)
    _add_column_if_missing("racks", "site_id", "VARCHAR")
    _add_column_if_missing("telemetry", "site_id", "VARCHAR")
