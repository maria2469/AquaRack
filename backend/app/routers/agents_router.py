"""
Multi-agent AI Decision endpoints (SDD Phase 2, Section 6, 11.1):
  POST /api/v1/recommend          — full multi-agent Orchestrator flow (supersedes
                                     Phase 1's single-agent /recommend when this
                                     router is mounted ahead of it, e.g. in the
                                     combined gateway)
  GET  /api/v1/recommendations    — list/filter historical recommendations
  POST /api/v1/agents/feedback    — human feedback on a recommendation
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

  # noqa: F401
from app import models
from app import schemas as p1_schemas
from app.database import get_db
from app.memory_engine import store as memory_store
from app.memory_engine.summarise import summarise_recommendation
from app.routers.simulate import run_full_pipeline

from app.agents.orchestrator import orchestrator
from app.models_ext import Feedback
from app.schemas_ext import FeedbackIn, MultiAgentRecommendationOut

router = APIRouter(prefix="/api/v1", tags=["agents"])


@router.post("/recommend", response_model=MultiAgentRecommendationOut)
def recommend_multi_agent(body: p1_schemas.RecommendationRequest, db: Session = Depends(get_db)):
    pipeline = run_full_pipeline(db, body.telemetry_id)
    reading = pipeline["reading"]
    twin_state = pipeline["twin_state"]
    water_out = pipeline["water_out"]

    open_incidents = db.query(models.Incident).filter(models.Incident.resolved.is_(False)).count()
    result = orchestrator.route_task(db, twin_state, water_out, open_incidents)

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

    return MultiAgentRecommendationOut(
        recommendation_id=rec_row.recommendation_id,
        telemetry_id=rec_row.telemetry_id,
        memory_id=rec_row.memory_id,
        text=rec_row.text,
        confidence=rec_row.confidence,
        agent_name=rec_row.agent_name,
        cited_memory_ids=rec_row.cited_memory_ids or [],
        rationale=rec_row.rationale,
        created_at=rec_row.created_at,
        agent_trace=result.get("agent_trace", []),
        run_id=result.get("run_id"),
    )


@router.get("/recommendations", response_model=List[p1_schemas.RecommendationOut])
def list_recommendations(
    site_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None, alias="from"),
    date_to: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(models.Recommendation)
    if date_from:
        q = q.filter(models.Recommendation.created_at >= date_from)
    if date_to:
        q = q.filter(models.Recommendation.created_at <= date_to)
    if site_id:
        q = q.join(
            models.Telemetry, models.Telemetry.telemetry_id == models.Recommendation.telemetry_id
        ).filter(models.Telemetry.site_id == site_id)
    return q.order_by(models.Recommendation.created_at.desc()).limit(limit).all()


@router.post("/agents/feedback", status_code=204)
def submit_feedback(body: FeedbackIn, db: Session = Depends(get_db)):
    rec = db.get(models.Recommendation, body.recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    db.add(Feedback(recommendation_id=body.recommendation_id, rating=body.rating, notes=body.notes))
    db.add(
        models.AuditLog(
            actor="human_feedback", action="recommendation.feedback", entity_ref=body.recommendation_id
        )
    )
    db.commit()
    return
