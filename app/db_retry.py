"""
CockroachDB transaction retry helper (SDD Section 9 / CockroachDB Best Practices).

CockroachDB uses optimistic concurrency control: when two transactions touch the
same data within the uncertainty interval it raises a SerializationFailure /
ReadWithinUncertaintyIntervalError and asks the client to restart the transaction.

This module provides:
  - `crdb_retry(fn, db, *args, **kwargs)` — retries a callable up to MAX_RETRIES
    times whenever a serialization failure is detected, with exponential back-off.
  - `with_retry(fn)` — function decorator version of the above.

References:
  https://www.cockroachlabs.com/docs/stable/transaction-retry-error-reference.html
  https://www.cockroachlabs.com/docs/stable/query-behavior.html#transaction-retries
"""

import logging
import time
from functools import wraps
from typing import Callable, TypeVar

import psycopg
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

MAX_RETRIES = 5
BACKOFF_BASE_MS = 50   # initial sleep: 50 ms → 100 → 200 → 400 → 800

T = TypeVar("T")


def _is_serialization_failure(exc: Exception) -> bool:
    """Return True if *exc* is a CockroachDB serialization / uncertainty error."""
    if isinstance(exc, OperationalError):
        cause = exc.__cause__
        if isinstance(cause, psycopg.errors.SerializationFailure):
            return True
    # Also catch the raw psycopg error when it escapes SQLAlchemy wrapping.
    if isinstance(exc, psycopg.errors.SerializationFailure):
        return True
    return False


def crdb_retry(fn: Callable[..., T], db: Session, *args, **kwargs) -> T:
    """
    Execute *fn(db, *args, **kwargs)* inside a retry loop.

    On SerializationFailure the session is rolled back and the call is retried
    up to MAX_RETRIES times with exponential back-off.
    """
    delay_ms = BACKOFF_BASE_MS
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            result = fn(db, *args, **kwargs)
            return result
        except Exception as exc:
            if _is_serialization_failure(exc) and attempt <= MAX_RETRIES:
                log.warning(
                    "CockroachDB SerializationFailure on attempt %d/%d — retrying in %dms",
                    attempt, MAX_RETRIES, delay_ms,
                )
                try:
                    db.rollback()
                except Exception:
                    pass
                time.sleep(delay_ms / 1000.0)
                delay_ms = min(delay_ms * 2, 2000)  # cap at 2 s
                continue
            raise


def with_retry(fn: Callable) -> Callable:
    """
    Decorator for SQLAlchemy route handlers that accept *db: Session* as their
    **first positional argument**.

    Usage::

        @with_retry
        def _query(db: Session) -> list[Telemetry]:
            return db.query(Telemetry).order_by(...).all()

        result = _query(db)
    """
    @wraps(fn)
    def wrapper(db: Session, *args, **kwargs):
        return crdb_retry(fn, db, *args, **kwargs)
    return wrapper
