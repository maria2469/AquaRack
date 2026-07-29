"""
Service health/readiness probe (SDD Phase 2, Section 11.1):
  GET /api/v1/health -> {status, dependencies}
"""
from fastapi import APIRouter
from sqlalchemy import text

import phase2_distributed.common.pathsetup  # noqa: F401
from app.config import settings
from app.database import engine

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health():
    dependencies = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        dependencies["database"] = "ok"
    except Exception as exc:
        dependencies["database"] = f"error: {exc}"

    dependencies["bedrock"] = "enabled" if settings.BEDROCK_ENABLED else "disabled (rules-based fallback active)"

    status = "ok" if dependencies["database"] == "ok" else "degraded"
    return {"status": status, "phase": 2, "dependencies": dependencies}
