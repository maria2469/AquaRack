"""
AI Decision Agent orchestration (SDD Section 5).
Phase 1 uses a single agent (one Bedrock call via LangChain, or the
deterministic rules-based fallback). All calls go through this shared
tool layer rather than routers touching data stores directly, so the
same tool implementations can be reused unchanged when Phase 2 promotes
this logic into a multi-agent system.

Every step of the reasoning process is pushed to the real-time reasoning
log (shared/observability/reasoning_logger.py) as it happens, so agent
"thinking" is visible live in logs (and, later, in a UI via the SSE
/api/v1/agent/trace/stream endpoint).
"""
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.agents import rules_fallback, langchain_bedrock
from app.memory_engine import store as memory_store
from app.observability import reasoning_logger as rl


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
    Orchestrates: retrieve top-K similar memories -> reason (Bedrock via
    LangChain, or rules fallback) -> return structured recommendation dict.
    Every step is pushed to the real-time reasoning log as it happens.
    """
    run_id = rl.new_run_id()
    agent_name = "water_cooling_single_agent"

    rl.log_step(
        run_id, agent_name, "input",
        {
            "utilisation_pct": twin_state.utilisation_pct,
            "thermal_load_kw": twin_state.thermal_load_kw,
            "cooling_load_kw": water_out.get("cooling_load_kw"),
            "open_incidents": open_incidents,
        },
    )

    query_text = (
        f"utilisation {twin_state.utilisation_pct}% thermal load "
        f"{twin_state.thermal_load_kw}kW cooling load {water_out['cooling_load_kw']}kW"
    )
    rl.log_step(run_id, "memory_rag", "tool_call", {"note": "Retrieving top-K similar memories", "query": query_text})
    memories = query_memory(db, query_text, k=5)
    rl.log_step(run_id, "memory_rag", "decision", {"retrieved_count": len(memories)})

    if settings.BEDROCK_ENABLED:
        try:
            result = langchain_bedrock.invoke_langchain(
                run_id, twin_state.model_dump(), water_out, memories, open_incidents, agent_name
            )
            rl.log_decision(
                run_id, agent_name, result["recommendation"], result["confidence"],
                result["rationale"], result.get("cited_memory_ids", []),
            )
            result["run_id"] = run_id
            return result
        except Exception as exc:
            rl.log_error(run_id, agent_name, f"Bedrock/LangChain call failed, falling back to rules: {exc}")
            # fall through to rules-based fallback (FR-1.11)

    rl.log_step(run_id, agent_name, "reasoning", {"note": "Using deterministic rules_fallback agent"})
    result = rules_fallback.generate_recommendation(twin_state, water_out, memories)
    rl.log_decision(
        run_id, agent_name, result["recommendation"], result["confidence"],
        result["rationale"], result.get("cited_memory_ids", []),
    )
    result["run_id"] = run_id
    return result
