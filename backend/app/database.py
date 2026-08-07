"""
Database wiring (CockroachDB only).
"""

import logging
import os
import time

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

log = logging.getLogger(__name__)

db_url = settings.DATABASE_URL.strip()

IS_COCKROACHDB = (
    db_url.startswith("cockroachdb://")
    or db_url.startswith("cockroachdb+psycopg://")
)

if not IS_COCKROACHDB:
    raise ValueError(
        "AquaRack requires CockroachDB. "
        f"DATABASE_URL must start with 'cockroachdb://' or 'cockroachdb+psycopg://'. "
        f"Got: {db_url[:20]}..."
    )

import sqlalchemy_cockroachdb  # noqa: F401


# ---------------------------------------------------------------------
# Automatically configure CockroachDB SSL certificate
# ---------------------------------------------------------------------
if "sslrootcert=" not in db_url:

    # 1. User explicitly provided a certificate path
    cert_path = os.environ.get("COCKROACH_CERT")

    # 2. Windows default location
    if not cert_path:
        win_cert = os.path.join(
            os.environ.get("APPDATA", ""),
            "postgresql",
            "root.crt",
        )
        if os.path.exists(win_cert):
            cert_path = win_cert

    # 3. Linux default location
    if not cert_path:
        linux_cert = os.path.expanduser("~/.postgresql/root.crt")
        if os.path.exists(linux_cert):
            cert_path = linux_cert

    # 4. Railway / Docker custom mount
    if not cert_path:
        docker_cert = "/app/certs/root.crt"
        if os.path.exists(docker_cert):
            cert_path = docker_cert

    # 5. Use discovered certificate
    if cert_path:
        cert_path = cert_path.replace("\\", "/")

        if "?" in db_url:
            db_url += f"&sslrootcert={cert_path}"
        else:
            db_url += f"?sslrootcert={cert_path}"

    else:
        # 6. Modern psycopg can use OS trust store
        if "?" in db_url:
            db_url += "&sslrootcert=system"
        else:
            db_url += "?sslrootcert=system"

log.info("Database URL: %s", db_url)

engine = create_engine(
    db_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

_CRDB_RETRY_MAX = 5
_CRDB_RETRY_BACKOFF_MS = 50


def _is_serialization_failure(exc: Exception) -> bool:
    if isinstance(exc, OperationalError):
        return isinstance(
            exc.__cause__,
            psycopg.errors.SerializationFailure,
        )
    return isinstance(exc, psycopg.errors.SerializationFailure)


def init_db():
    from app import models  # noqa

    Base.metadata.create_all(bind=engine)


def get_db():
    delay = _CRDB_RETRY_BACKOFF_MS

    for attempt in range(1, _CRDB_RETRY_MAX + 2):

        db = SessionLocal()

        try:
            yield db
            db.commit()  # Ensure commit before yield return
            return

        except Exception as exc:

            try:
                db.rollback()  # Ensure rollback on error
            except Exception:
                pass
            db.close()

            if _is_serialization_failure(exc) and attempt <= _CRDB_RETRY_MAX:

                log.warning(
                    "Serialization failure. Retrying (%d/%d)",
                    attempt,
                    _CRDB_RETRY_MAX,
                )

                time.sleep(delay / 1000)

                delay = min(delay * 2, 2000)

                continue

            raise

        finally:
            try:
                db.close()
            except Exception:
                pass
