"""
Episodes Router (Task 4 — GET /api/v1/episodes/replay).

Provides a filtered view of resolved Episode rows for Experience Replay
analysis: front-end and ML pipelines can query historical episodes by rack,
outcome, or temperature window to feed offline reinforcement-learning loops.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_ext import Episode

logger = logging.getLogger("aquamind.router.episodes")
router = APIRouter(prefix="/api/v1/episodes", tags=["episodes"])


@router.get("/replay", summary="List resolved episodes for experience-replay")
def get_episodes_replay(
    rack_id: Optional[str] = Query(None, description="Filter by rack ID"),
    success: Optional[bool] = Query(None, description="Filter by success flag"),
    min_reward: Optional[float] = Query(None, description="Minimum reward threshold"),
    action: Optional[str] = Query(None, description="Filter by action_taken value"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of episodes to return"),
    db: Session = Depends(get_db),
):
    """
    Return resolved Episode rows (outcome_recorded_at IS NOT NULL) optionally
    filtered by rack, success flag, minimum reward, or action taken.
    Results are ordered by created_at DESC (most recent first).
    """
    q = db.query(Episode).filter(Episode.outcome_recorded_at.isnot(None))

    if rack_id is not None:
        q = q.filter(Episode.rack_id == rack_id)
    if success is not None:
        q = q.filter(Episode.success == success)
    if min_reward is not None:
        q = q.filter(Episode.reward >= min_reward)
    if action is not None:
        q = q.filter(Episode.action_taken == action)

    episodes = q.order_by(Episode.created_at.desc()).limit(limit).all()

    return [
        {
            "episode_id": ep.episode_id,
            "run_id": ep.run_id,
            "rack_id": ep.rack_id,
            "recommendation_id": ep.recommendation_id,
            "action_taken": ep.action_taken,
            "confidence_at_decision": ep.confidence_at_decision,
            "water_delta_pct": ep.water_delta_pct,
            "temp_delta_c": ep.temp_delta_c,
            "incident_occurred": ep.incident_occurred,
            "success": ep.success,
            "reward": ep.reward,
            "outcome_recorded_at": ep.outcome_recorded_at.isoformat() if ep.outcome_recorded_at else None,
            "created_at": ep.created_at.isoformat() if ep.created_at else None,
        }
        for ep in episodes
    ]
