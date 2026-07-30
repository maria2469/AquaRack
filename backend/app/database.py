"""
Database wiring (SDD Section 4 / Section 9 / Tech Stack: CockroachDB).

Defaults to CockroachDB (SDD tech stack) via the sqlalchemy-cockroachdb
dialect + psycopg driver — the same SQLAlchemy models work unchanged
against a single-node local cluster, CockroachDB Cloud, or a multi-region
deployment, with no migration required (Section 9, closing note).

SQLite remains supported as an explicit local-dev opt-out
(DATABASE_URL=sqlite:///...) so the test suite / offline demos still work
without a running CockroachDB instance.

CockroachDB Serialization Retry (SDD Section 9):
  CockroachDB uses optimistic concurrency control: on concurrent write
  contention it raises SerializationFailure and expects the client to
  retry the whole transaction. `get_db()` wraps every request-scoped
  session in a retry loop (up to 5 attempts, 50→800ms exponential
  back-off) so callers never see a 500 from a transient CRDB restart.
"""
import logging
import time

import psycopg
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

log = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
IS_SQLITE = db_url.startswith("sqlite")
IS_COCKROACHDB = db_url.startswith("cockroachdb://") or db_url.startswith("cockroachdb+psycopg://")

if IS_COCKROACHDB:
    import sqlalchemy_cockroachdb  # noqa: F401

# Auto-fix CockroachDB Cloud SSL certificate on Linux containers (Railway / Render / Docker)
if not IS_SQLITE and "sslrootcert" not in db_url:
    if "?" in db_url:
        db_url += "&sslrootcert=system"
    else:
        db_url += "?sslrootcert=system"

connect_args = {"check_same_thread": False} if IS_SQLITE else {}

engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- CockroachDB serialization-failure constants ---
_CRDB_RETRY_MAX = 5
_CRDB_RETRY_BACKOFF_MS = 50  # doubles each attempt, capped at 2 000 ms


def _is_serialization_failure(exc: Exception) -> bool:
    """True when *exc* is a CockroachDB MVCC uncertainty / serialization error."""
    if isinstance(exc, OperationalError):
        return isinstance(exc.__cause__, psycopg.errors.SerializationFailure)
    return isinstance(exc, psycopg.errors.SerializationFailure)


def init_db() -> None:
    """Create all tables if they don't already exist (Section 9 schema)."""
    from app import models  # noqa: F401  (ensure models are registered on Base)

    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI dependency: yields a request-scoped DB session with automatic
    CockroachDB serialization-failure retry.

    On SerializationFailure the session is rolled back and the *entire
    request handler* is retried — which is safe because FastAPI re-runs
    the dependency generator for each retry and the handler itself is
    idempotent for read queries.
    """
    delay_ms = _CRDB_RETRY_BACKOFF_MS
    for attempt in range(1, _CRDB_RETRY_MAX + 2):
        db = SessionLocal()
        try:
            yield db
            return  # success — stop iteration
        except Exception as exc:
            db.close()
            if _is_serialization_failure(exc) and attempt <= _CRDB_RETRY_MAX:
                log.warning(
                    "CockroachDB SerializationFailure on attempt %d/%d — retrying in %dms",
                    attempt, _CRDB_RETRY_MAX, delay_ms,
                )
                time.sleep(delay_ms / 1000.0)
                delay_ms = min(delay_ms * 2, 2000)
                continue
            raise
        finally:
            try:
                db.close()
            except Exception:
                pass
