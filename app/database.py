"""
Database wiring (SDD Section 4 / Section 9 / Tech Stack: CockroachDB).

Defaults to CockroachDB (SDD tech stack) via the sqlalchemy-cockroachdb
dialect + psycopg2 driver — the same SQLAlchemy models work unchanged
against a single-node local cluster, CockroachDB Cloud, or a multi-region
Phase 2 deployment, with no migration required (Section 9, closing note).

SQLite remains supported as an explicit local-dev opt-out
(DATABASE_URL=sqlite:///...) so the test suite / offline demos still work
without a running CockroachDB instance.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")
IS_COCKROACHDB = settings.DATABASE_URL.startswith("cockroachdb://")

if IS_COCKROACHDB:
    # Registers the `cockroachdb://` SQLAlchemy dialect (sqlalchemy-cockroachdb
    # package, backed by psycopg2) as a side effect of import; connections
    # are still made via create_engine() below.
    import sqlalchemy_cockroachdb  # noqa: F401

connect_args = {"check_same_thread": False} if IS_SQLITE else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create all tables if they don't already exist (Section 9 schema)."""
    from app import models  # noqa: F401  (ensure models are registered on Base)

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
