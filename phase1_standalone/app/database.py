"""
Database wiring (SDD Section 4 / Section 9).

Phase 1 runs against SQLite by default (fully offline, zero cost, per
Section 1) but the same SQLAlchemy models work unchanged against
CockroachDB (single-node, free tier) by pointing DATABASE_URL at it —
the schema is designed to carry forward into Phase 2 without migration
(Section 9, closing note).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
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
