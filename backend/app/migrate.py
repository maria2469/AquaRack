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
import logging
from sqlalchemy import inspect, text


from app.database import engine, Base

# Ensure all model classes (Phase 1 + Phase 2) are registered on Base before create_all().
from app import models  # noqa: F401
from app import models_ext  # noqa: F401

logger = logging.getLogger(__name__)

# Allowed tables and columns for migration security (SQL injection prevention)
ALLOWED_TABLES = {
    "racks", "telemetry", "incidents", "recommendations", 
    "water_model_results", "memory_embeddings", "episodes", "strategy_scores"
}
ALLOWED_COLUMNS = {
    "site_id": "VARCHAR",
    "gpu_temp": "FLOAT", 
    "weather_temp": "FLOAT",
    "humidity": "FLOAT",
    "predicted_water_usage": "FLOAT",
    "root_cause": "VARCHAR",
    "telemetry_id": "VARCHAR",
    "incident_id": "VARCHAR",
    "expected_water_saving": "FLOAT",
}


def _add_column_if_missing(table: str, column: str, coltype: str = "VARCHAR") -> None:
    """Add column to table if it doesn't exist, with SQL injection protection."""
    # Validate table and column names to prevent SQL injection
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table}. Allowed tables: {ALLOWED_TABLES}")
    if column not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid column name: {column}. Allowed columns: {ALLOWED_COLUMNS}")
    if coltype != ALLOWED_COLUMNS[column]:
        raise ValueError(f"Invalid column type for {column}. Expected: {ALLOWED_COLUMNS[column]}, Got: {coltype}")
    
    from app import database
    try:
        inspector = inspect(database.engine)
        if table not in inspector.get_table_names():
            logger.info(f"Table {table} does not exist, skipping migration")
            return
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column in existing:
            logger.info(f"Column {table}.{column} already exists, skipping migration")
            return
        with database.engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
            logger.info(f"Successfully added column {table}.{column} with type {coltype}")
    except Exception as exc:
        logger.warning("Migration failed for %s.%s: %s", table, column, exc)


def run_migrations() -> None:
    from app import database
    database.init_db()
    _add_column_if_missing("racks", "site_id", "VARCHAR")
    _add_column_if_missing("telemetry", "site_id", "VARCHAR")
    _add_column_if_missing("telemetry", "gpu_temp", "FLOAT")
    _add_column_if_missing("telemetry", "weather_temp", "FLOAT")
    _add_column_if_missing("telemetry", "humidity", "FLOAT")
    _add_column_if_missing("telemetry", "predicted_water_usage", "FLOAT")
    _add_column_if_missing("incidents", "root_cause", "VARCHAR")
    _add_column_if_missing("incidents", "telemetry_id", "VARCHAR")
    _add_column_if_missing("recommendations", "incident_id", "VARCHAR")
    _add_column_if_missing("recommendations", "expected_water_saving", "FLOAT")

