"""
Tests for reasoning trace persistence and optimizer alternatives logging (Task 5).
"""
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import SessionLocal
from app.models_ext import ReasoningTrace
from app.observability import reasoning_logger as rl

client = TestClient(app)


def test_log_step_persists_reasoning_trace():
    """log_step() writes a ReasoningTrace row to the DB."""
    run_id = str(uuid.uuid4())
    rl.log_step(run_id, "TestAgent", "input", {"note": "unit-test"})

    db = SessionLocal()
    try:
        traces = db.query(ReasoningTrace).filter(ReasoningTrace.run_id == run_id).all()
        assert len(traces) >= 1
        assert traces[0].agent == "TestAgent"
        assert traces[0].stage == "input"
        assert traces[0].detail.get("note") == "unit-test"
    finally:
        db.close()


def test_log_step_with_alternatives_rejected():
    """log_step() stores alternatives_rejected in ReasoningTrace."""
    run_id = str(uuid.uuid4())
    rl.log_step(
        run_id, "OptimizerAgent", "reasoning",
        {"recommendation": "increase cooling 12%", "confidence": 0.88},
        alternatives_rejected=["Reduce server clock speed by 5%"],
    )

    db = SessionLocal()
    try:
        traces = (
            db.query(ReasoningTrace)
            .filter(ReasoningTrace.run_id == run_id, ReasoningTrace.stage == "reasoning")
            .all()
        )
        assert len(traces) >= 1
        assert "Reduce server clock speed by 5%" in traces[0].alternatives_rejected
    finally:
        db.close()


def test_log_decision_persists_reasoning_trace():
    """log_decision() also writes a ReasoningTrace row."""
    run_id = str(uuid.uuid4())
    rl.log_decision(
        run_id, "LangGraphOrchestrator",
        recommendation="Increase cooling",
        confidence=0.9,
        rationale="Thermal risk",
        cited_memory_ids=["mem-abc"],
    )

    db = SessionLocal()
    try:
        traces = (
            db.query(ReasoningTrace)
            .filter(ReasoningTrace.run_id == run_id, ReasoningTrace.stage == "decision")
            .all()
        )
        assert len(traces) >= 1
        assert traces[0].detail.get("confidence") == 0.9
    finally:
        db.close()


def test_reasoning_logger_does_not_raise_on_db_failure():
    """DB persistence errors in _persist_to_db must not raise to caller."""
    with patch("app.database.SessionLocal", side_effect=Exception("DB unavailable")):
        # Should not raise — DB sink is defensive
        rl.log_step("no-db-run", "TestAgent", "reasoning", {"x": 1})
