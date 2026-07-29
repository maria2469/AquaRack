"""
End-to-end smoke tests for the Phase 2 combined gateway: fleet batch
ingest -> sites -> OpenDC simulation job (submit + poll to completion) ->
multi-agent recommend -> recommendations list -> feedback -> fleet
summary -> memory tiering job. Uses an isolated on-disk SQLite DB.
"""
import os
import sys
import time

os.environ["DATABASE_URL"] = "sqlite:///./test_aquamind_phase2.db"
os.environ["BEDROCK_ENABLED"] = "false"

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
_PHASE1_DIR = os.path.join(_REPO_ROOT, "phase1_standalone")
for _p in (_REPO_ROOT, _PHASE1_DIR):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest
from fastapi.testclient import TestClient

from phase2_distributed.gateway.main import app

client = TestClient(app)
client.__enter__()


@pytest.fixture(autouse=True, scope="module")
def _cleanup():
    yield
    for f in ("test_aquamind_phase2.db",):
        if os.path.exists(f):
            os.remove(f)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["phase"] == 2
    assert body["dependencies"]["database"] == "ok"


def test_fleet_batch_ingest_and_sites():
    payload = [
        {"device_id": "edge-01", "cpu_pct": 40.0, "ram_pct": 35.0, "source": "laptop"},
        {"device_id": "edge-02", "cpu_pct": 55.0, "ram_pct": 50.0, "source": "iot"},
    ]
    resp = client.post("/api/v1/telemetry/batch", json=payload)
    assert resp.status_code == 202
    body = resp.json()
    assert body["accepted"] == 2
    assert body["rejected"] == 0

    resp = client.get("/api/v1/sites")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_opendc_simulation_job_lifecycle():
    spec = {
        "mode": "opendc",
        "num_racks": 2,
        "workload_profile": "bursty",
        "duration_ticks": 3,
        "site_name": "test-site-alpha",
    }
    resp = client.post("/api/v1/simulate/opendc", json=spec)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert resp.json()["status"] in ("queued", "running")

    # Poll until the background thread finishes (small job -> fast).
    deadline = time.time() + 15
    status = None
    while time.time() < deadline:
        resp = client.get(f"/api/v1/simulate/opendc/{job_id}")
        assert resp.status_code == 200
        job = resp.json()
        status = job["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.5)

    assert status == "completed", f"job did not complete in time (last status={status})"
    assert job["result"]["num_racks"] == 2
    assert job["result"]["fleet_thermal_load_kw"] >= 0


def test_multi_agent_recommend_and_feedback():
    # Ingest a high-utilisation reading so the recommendation is non-trivial.
    resp = client.post(
        "/api/v1/telemetry",
        json={"device_id": "test-laptop", "cpu_pct": 93.0, "ram_pct": 88.0, "source": "laptop"},
    )
    assert resp.status_code == 202
    telemetry_id = resp.json()["telemetry_id"]

    resp = client.post("/api/v1/recommend", json={"telemetry_id": telemetry_id})
    assert resp.status_code == 200
    rec = resp.json()
    assert rec["agent_name"] == "multi_agent_orchestrator"
    assert 0 <= rec["confidence"] <= 1
    assert len(rec["agent_trace"]) >= 4  # memory_rag, telemetry_analyst, water_cooling, capacity_planning, guardrail_critic

    agent_names = {step["agent"] for step in rec["agent_trace"]}
    assert {"memory_rag", "telemetry_analyst", "water_cooling", "capacity_planning", "guardrail_critic"} <= agent_names

    resp = client.post(
        "/api/v1/agents/feedback",
        json={"recommendation_id": rec["recommendation_id"], "rating": 1, "notes": "looks right"},
    )
    assert resp.status_code == 204

    resp = client.get("/api/v1/recommendations", params={"limit": 10})
    assert resp.status_code == 200
    assert any(r["recommendation_id"] == rec["recommendation_id"] for r in resp.json())


def test_fleet_summary():
    resp = client.get("/api/v1/fleet/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["num_sites_racks"] >= 1
    assert "sites" in body


def test_watermodel_fleet_aggregate():
    resp = client.get("/api/v1/watermodel/fleet-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "fleet_total_cooling_load_kw" in body


def test_memory_retier_job_runs():
    from phase2_distributed.memory_tiering.retier_job import retier_memories

    counts = retier_memories()
    assert counts["hot"] + counts["warm"] + counts["cold"] >= 1
