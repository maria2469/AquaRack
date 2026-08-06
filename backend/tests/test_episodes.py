"""
Tests for Episode table, outcome_watcher, and GET /api/v1/episodes/replay (Task 4).
"""
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models_ext import Episode, StrategyScore


client = TestClient(app)


def _make_episode(db, *, rack_id="rack-01", action="increase_cooling_flow_12pct",
                  confidence=0.88, created_at=None, outcome_recorded_at=None,
                  success=None, water_delta_pct=None, temp_delta_c=None, reward=None):
    ep = Episode(
        episode_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        rack_id=rack_id,
        telemetry_snapshot={"cpu_pct": 72.0, "gpu_temp": 68.0, "utilisation_pct": 84.0},
        water_snapshot={"water_l_per_hr": 12.0, "cooling_load_kw": 3.1},
        action_taken=action,
        action_params={"expected_water_saving": 15.5},
        confidence_at_decision=confidence,
        created_at=created_at or datetime.utcnow(),
        outcome_recorded_at=outcome_recorded_at,
        success=success,
        water_delta_pct=water_delta_pct,
        temp_delta_c=temp_delta_c,
        reward=reward,
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


def test_episode_table_creation():
    """Episode rows can be created and queried."""
    db = SessionLocal()
    try:
        ep = _make_episode(db)
        found = db.get(Episode, ep.episode_id)
        assert found is not None
        assert found.action_taken == "increase_cooling_flow_12pct"
        assert found.outcome_recorded_at is None
    finally:
        db.close()


def test_resolve_pending_episodes_happy_path():
    """resolve_pending_episodes resolves an episode older than 15 minutes."""
    from app.memory_engine.outcome_watcher import resolve_pending_episodes
    from app import models

    db = SessionLocal()
    try:
        # Create episode with created_at 20 minutes ago (eligible)
        past = datetime.utcnow() - timedelta(minutes=20)
        ep = _make_episode(db, created_at=past)

        # Ensure there is at least one telemetry row (simulate improved temp)
        t = models.Telemetry(
            telemetry_id=str(uuid.uuid4()),
            rack_id="rack-01",
            device_id="device-test",
            cpu_pct=45.0,          # lower than snapshot's implicit 50.0 baseline
            ram_pct=60.0,          # required NOT NULL
            timestamp=datetime.utcnow(),
        )
        db.add(t)
        db.commit()

        result = resolve_pending_episodes(db=db, now=datetime.utcnow())
        assert result["resolved_episodes"] >= 1

        db.refresh(ep)
        assert ep.outcome_recorded_at is not None
        assert ep.temp_delta_c is not None
        assert ep.success is not None
        assert ep.reward is not None
    finally:
        db.close()


def test_resolve_pending_episodes_skips_recent():
    """Episodes younger than 15 minutes are NOT resolved."""
    from app.memory_engine.outcome_watcher import resolve_pending_episodes

    db = SessionLocal()
    try:
        ep = _make_episode(db, created_at=datetime.utcnow())  # too recent
        result = resolve_pending_episodes(db=db, now=datetime.utcnow())
        db.refresh(ep)
        assert ep.outcome_recorded_at is None
    finally:
        db.close()


def test_strategy_score_upserted():
    """StrategyScore is created/incremented when an episode is resolved."""
    from app.memory_engine.outcome_watcher import resolve_pending_episodes

    db = SessionLocal()
    try:
        action = f"test_action_{uuid.uuid4().hex[:6]}"
        past = datetime.utcnow() - timedelta(minutes=20)
        _make_episode(db, created_at=past, action=action)

        resolve_pending_episodes(db=db, now=datetime.utcnow())

        score = db.get(StrategyScore, action)
        assert score is not None
        assert score.success_count + score.failure_count == 1
        assert 0.0 < score.confidence <= 1.0
    finally:
        db.close()


def test_episodes_replay_endpoint_empty():
    """GET /api/v1/episodes/replay returns 200 with a list."""
    resp = client.get("/api/v1/episodes/replay?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_episodes_replay_endpoint_filtered():
    """Resolved episodes appear in /replay and honour filters."""
    db = SessionLocal()
    try:
        past = datetime.utcnow() - timedelta(minutes=25)
        ep = _make_episode(
            db,
            created_at=past,
            outcome_recorded_at=datetime.utcnow(),
            success=True,
            water_delta_pct=-5.0,
            temp_delta_c=-1.5,
            reward=3.2,
        )
        episode_id = ep.episode_id
    finally:
        db.close()

    resp = client.get("/api/v1/episodes/replay?success=true&limit=50")
    assert resp.status_code == 200
    ids = [r["episode_id"] for r in resp.json()]
    assert episode_id in ids
