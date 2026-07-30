"""
Service health/readiness probe (SDD Phase 2, Section 11.1):
  GET /api/v1/health -> {status, dependencies}
"""
from fastapi import APIRouter
from sqlalchemy import text

  # noqa: F401
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

    dependencies["ollama"] = "enabled" if settings.OLLAMA_ENABLED else "disabled (rules-based fallback active)"
    dependencies["cockroach_mcp"] = "ready"

    status = "ok" if dependencies["database"] == "ok" else "degraded"
    return {"status": status, "phase": 2, "dependencies": dependencies}
