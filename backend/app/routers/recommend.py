from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.routers.simulate import run_full_pipeline
from app.agents import legacy_single_agent_orchestrator as orchestrator
from app.memory_engine import store as memory_store
from app.memory_engine.summarise import summarise_recommendation

router = APIRouter(prefix="/api/v1", tags=["recommend"])


@router.post("/recommend", response_model=schemas.RecommendationOut)
def recommend(body: schemas.RecommendationRequest, db: Session = Depends(get_db)):
    pipeline = run_full_pipeline(db, body.telemetry_id)
    reading = pipeline["reading"]
    twin_state = pipeline["twin_state"]
    water_out = pipeline["water_out"]

    open_incidents = db.query(models.Incident).filter(models.Incident.resolved.is_(False)).count()
    result = orchestrator.run_recommendation(db, twin_state, water_out, open_incidents)

    # Persist the memory (Stage 1-3 of Memory Lifecycle, SDD Section 11)
    conversation_id = memory_store.get_or_create_default_conversation(db)
    summary = summarise_recommendation(twin_state, water_out, result["recommendation"])
    memory = memory_store.store_memory(db, conversation_id, "recommendation", summary)

    rec_row = models.Recommendation(
        telemetry_id=reading.telemetry_id,
        memory_id=memory.memory_id,
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


@router.get("/recommend/latest", response_model=schemas.RecommendationOut)
def latest_recommendation(db: Session = Depends(get_db)):
    row = db.query(models.Recommendation).order_by(models.Recommendation.created_at.desc()).first()
    if not row:
        raise HTTPException(status_code=404, detail="No recommendations generated yet")
    return row
