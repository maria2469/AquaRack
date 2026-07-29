# Database schema

The full table/column definitions live in `phase1_standalone/app/models.py`
(SQLAlchemy ORM), implementing the ER diagram in SDD Section 9 exactly —
`racks`, `racks_config`, `telemetry`, `weather`, `water_model`, `incidents`,
`maintenance`, `audit_log`, `conversations`, `memories`, `embeddings`,
`recommendations`.

Phase 1 applies this schema via `Base.metadata.create_all()` at startup
(`app/database.py::init_db`), which works against both local SQLite and a
single-node CockroachDB free-tier cluster.

Phase 2 promotes this to versioned migrations (e.g. Alembic) once the schema
needs to evolve across a distributed deployment — no columns need to be
added, removed, or renamed to make that transition (SDD Section 9, closing
note).
