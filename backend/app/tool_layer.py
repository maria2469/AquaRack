"""
Shared, versioned function-calling tool layer (SDD Section 6.2):
get_telemetry(), run_simulation(), query_memory(), compute_water_model(),
write_memory(). Every agent calls into these rather than touching the DB
directly, so agent logic stays declarative/testable and the exact same
tool implementations back both Phase 1's single agent and Phase 2's
multi-agent system (no drift between phases).

These are thin, fleet-aware wrappers around the Phase 1 implementations
already proven out in app/agent/orchestrator.py, app/routers/simulate.py,
and app/memory_engine/store.py.
"""
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

  # noqa: F401
from app import models
from app.routers.simulate import run_full_pipeline
from app.memory_engine import store as memory_store

TOOL_VERSION = "v1"  # bump when the tool contract changes


def get_telemetry(db: Session, telemetry_id: Optional[str] = None, site_id: Optional[str] = None):
    """Returns a single Telemetry row: by id, latest for a site, or latest overall."""
    if telemetry_id:
        return db.get(models.Telemetry, telemetry_id)
    q = db.query(models.Telemetry)
    if site_id:
        q = q.filter(models.Telemetry.site_id == site_id)
    return q.order_by(models.Telemetry.timestamp.desc()).first()


def run_simulation(db: Session, telemetry_id: Optional[str] = None) -> Dict:
    """Digital Twin -> Water Model pipeline (same helper Phase 1's /simulate and /recommend use)."""
    return run_full_pipeline(db, telemetry_id)


def query_memory(db: Session, query_text: str, k: int = 5, tier: Optional[str] = None) -> List[Dict]:
    """Top-K cosine-similarity memory retrieval (RAG), optionally filtered by tier (hot/warm/cold)."""
    results = memory_store.search_memories(db, query_text, k=k)
    if tier:
        results = [r for r in results if r["tier"] == tier]
    return results


def compute_water_model(db: Session, telemetry_id: str):
    """Latest persisted WaterModelResult for a given telemetry reading."""
    return (
        db.query(models.WaterModelResult)
        .filter(models.WaterModelResult.telemetry_id == telemetry_id)
        .order_by(models.WaterModelResult.computed_at.desc())
        .first()
    )


def write_memory(db: Session, conversation_id: str, mem_type: str, summary: str):
    """Persist a new memory (summary + embedding) via the Memory Engine."""
    return memory_store.store_memory(db, conversation_id, mem_type, summary)
