"""
End-to-end smoke tests for the Phase 1 monolith: ingest telemetry -> run
digital twin/water model -> get an AI recommendation -> search memory.
Uses an isolated on-disk SQLite DB so it never touches a developer's real
aquamind_phase1.db.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_aquamind.db"
os.environ["OLLAMA_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Use as a context manager so FastAPI's startup event (init_db) actually
# fires — TestClient only triggers lifespan/startup handlers this way.
client = TestClient(app)
client.__enter__()


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    for f in ("test_aquamind.db",):
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_full_pipeline():
    # 1. Ingest telemetry
    payload = {
        "device_id": "test-laptop",
        "cpu_pct": 98.0,
        "gpu_pct": 95.0,
        "ram_pct": 90.0,
        "fan_rpm": 4200,
        "battery_pct": 88.0,
        "source": "laptop",
    }
    resp = client.post("/api/v1/telemetry", json=payload)
    assert resp.status_code == 202
    telemetry_id = resp.json()["telemetry_id"]

    # 2. Latest telemetry readable
    resp = client.get("/api/v1/telemetry/latest")
    assert resp.status_code == 200
    assert resp.json()["telemetry_id"] == telemetry_id

    # 3. Simulate (Digital Twin + Water Model)
    resp = client.post("/api/v1/simulate", json={"telemetry_id": telemetry_id})
    assert resp.status_code == 200
    sim = resp.json()
    assert sim["utilisation"] > 0
    assert sim["water_model"]["cooling_load_kw"] > 0

    # High utilisation should trigger the "high" incident. In the unified
    # app, POST /api/v1/recommend is served by the multi-agent Orchestrator
    # (mounted with precedence over the legacy single-agent path).
    resp = client.post("/api/v1/recommend", json={"telemetry_id": telemetry_id})
    assert resp.status_code == 200
    rec = resp.json()
    assert rec["agent_name"] == "multi_agent_orchestrator"
    assert 0 <= rec["confidence"] <= 1
    assert "critical" in rec["text"].lower()

    # 4. Dashboard summary reflects everything
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["latest_recommendation"]["recommendation_id"] == rec["recommendation_id"]
    assert summary["open_incidents"] >= 1

    # 5. Memory search finds the recommendation we just stored
    resp = client.get("/api/v1/memory/search", params={"q": "utilisation critical", "k": 3})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1

    # 6. Daily CSV report
    resp = client.get("/api/v1/reports/daily", params={"format": "csv"})
    assert resp.status_code == 200
    assert "cooling_load_kw" in resp.text
