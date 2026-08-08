"""
Legacy single-agent recommend router (SDD Phase 1).
This route is shadowed by agents_router (mounted first), but kept for backward
compatibility and health-check purposes.

Rewired to use the LangGraph orchestrator directly (consistent with
agents_router.py) rather than the old legacy_single_agent_orchestrator which
referenced removed memory_store methods.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.routers.simulate import run_full_pipeline
from app.agents.orchestrator import orchestrator
from app.memory_engine import store as memory_store
from app.memory_engine.summarise import summarise_recommendation

logger = logging.getLogger("aquarack.recommend")

router = APIRouter(prefix="/api/v1", tags=["recommend"])


@router.post("/recommend", response_model=schemas.RecommendationOut)
def recommend(body: schemas.RecommendationRequest, db: Session = Depends(get_db)):
    """
    Legacy single-agent recommend endpoint. In practice the agents_router
    (multi-agent LangGraph) is mounted first so this route is only hit if the
    multi-agent router isn't registered. Kept for backward compat & tests.
    """
    try:
        pipeline = run_full_pipeline(db, body.telemetry_id)
        reading = pipeline["reading"]
        twin_state = pipeline["twin_state"]  # This is now a dict with device_id
        water_out = pipeline["water_out"]

        open_incidents = db.query(models.Incident).filter(models.Incident.resolved.is_(False)).count()
        
        try:
            result = orchestrator.route_task(db, twin_state, water_out, open_incidents)
        except Exception as e:
            logger.error(f"Recommendation reasoning failed: {e}")
            result = {
                "run_id": "recommend-failed",
                "recommendation": "Recommendation reasoning failed",
                "confidence": 0.5,
                "agent_name": "recommend_failed",
                "rationale": f"Reasoning error: {str(e)}"
            }

        # Persist recommendation summary into agentic memory
        summary = summarise_recommendation(twin_state, water_out, result["recommendation"])
        try:
            memory_store.store_memory_embedding(
                db,
                memory_type="recommendation",
                source_id=result.get("run_id", reading.telemetry_id),
                summary=summary,
                device_id=reading.device_id,  # Add device_id
            )
        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
            # Continue with recommendation even if memory storage fails

        rec_row = models.Recommendation(
            device_id=reading.device_id,  # Add device_id to satisfy database constraint
            telemetry_id=reading.telemetry_id,
            text=result["recommendation"],
            confidence=result["confidence"],
            agent_name=result["agent_name"],
            cited_memory_ids=result.get("cited_memory_ids", []),
            rationale=result.get("rationale"),
        )
        db.add(rec_row)
        db.add(
            models.AuditLog(
                actor=result["agent_name"], action="recommendation.create", entity_ref=rec_row.recommendation_id
            )
        )
        db.commit()
        db.refresh(rec_row)
        return rec_row
    except Exception as e:
        logger.error(f"Recommend endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@router.get("/recommend/latest", response_model=schemas.RecommendationOut)
def latest_recommendation(db: Session = Depends(get_db)):
    row = db.query(models.Recommendation).order_by(models.Recommendation.created_at.desc()).first()
    if not row:
        raise HTTPException(status_code=404, detail="No recommendations generated yet")
    return row
