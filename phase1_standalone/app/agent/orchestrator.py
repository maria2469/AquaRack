"""
AI Decision Agent orchestration (SDD Section 5).
Phase 1 uses a single agent (one Bedrock call, or the deterministic
rules-based fallback). All calls go through this shared tool layer rather
than routers touching data stores directly, so the same tool
implementations can be reused unchanged when Phase 2 promotes this logic
into a multi-agent system.
"""
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.agent import rules_fallback, bedrock_client
from app.memory_engine import store as memory_store


def get_telemetry(db: Session, telemetry_id: str = None):
    if telemetry_id:
        return db.get(models.Telemetry, telemetry_id)
    return db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).first()


def query_memory(db: Session, query_text: str, k: int = 5):
    return memory_store.search_memories(db, query_text, k=k)


def compute_water_model(db: Session, telemetry_id: str):
    return (
        db.query(models.WaterModelResult)
        .filter(models.WaterModelResult.telemetry_id == telemetry_id)
        .order_by(models.WaterModelResult.computed_at.desc())
        .first()
    )


def write_memory(db: Session, conversation_id: str, mem_type: str, summary: str):
    return memory_store.store_memory(db, conversation_id, mem_type, summary)


def run_recommendation(db: Session, twin_state, water_out: dict, open_incidents: int) -> dict:
    """
    Orchestrates: retrieve top-K similar memories -> reason (Bedrock or
    rules fallback) -> return structured recommendation dict.
    """
    query_text = (
        f"utilisation {twin_state.utilisation_pct}% thermal load "
        f"{twin_state.thermal_load_kw}kW cooling load {water_out['cooling_load_kw']}kW"
    )
    memories = query_memory(db, query_text, k=5)

    if settings.BEDROCK_ENABLED:
        try:
            return bedrock_client.invoke(
                twin_state.model_dump(), water_out, memories, open_incidents
            )
        except Exception:
            pass  # fall through to rules-based fallback (FR-1.11)

    return rules_fallback.generate_recommendation(twin_state, water_out, memories)
