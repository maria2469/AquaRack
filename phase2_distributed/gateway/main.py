"""
Combined Phase 1 + Phase 2 gateway (local demo convenience app).

In AWS, Phase 2 deploys five independent microservices behind an
Application Load Balancer (SDD Section 4 / phase2_distributed/services/*).
For local development this module mounts every Phase 1 + Phase 2 router in
a single FastAPI app/process — same routers, same code, zero duplication —
so the whole system (telemetry, digital twin, water model, multi-agent
recommendations, fleet dashboard, OpenDC/CloudSim jobs) can be exercised
with one command (see repo-root run_phase2.py).

Route precedence note: Phase 2 routers are included *before* the
equivalent Phase 1 routers. FastAPI/Starlette match routes in the order
they were added, so this makes the multi-agent Orchestrator the effective
handler for POST /api/v1/recommend in the combined gateway (Phase 2
supersedes Phase 1's single-agent call here), while Phase 1's other
endpoints (GET /recommend/latest, /telemetry, /simulate, /memory/search,
/dashboard/summary, /reports/daily) remain fully reachable and unchanged —
running `phase1_standalone/run.py` on its own is unaffected either way.
"""
import phase2_distributed.common.pathsetup  # noqa: F401  (must be the first import)

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import dashboard as p1_dashboard
from app.routers import memory as p1_memory
from app.routers import recommend as p1_recommend
from app.routers import reports as p1_reports
from app.routers import simulate as p1_simulate
from app.routers import telemetry as p1_telemetry

from phase2_distributed.common.migrate import run_migrations
from phase2_distributed.routers import (
    agents_router,
    fleet_dashboard,
    fleet_telemetry,
    health as p2_health,
    simulate_opendc,
    water_model_only,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler("aquamind_phase2.log"), logging.StreamHandler()],
)
logger = logging.getLogger("aquamind.phase2.gateway")

app = FastAPI(
    title="AquaMind AI — Phase 1 + Phase 2 Combined",
    version="2.0.0",
    description=(
        "Combined local demo: the Phase 1 standalone laptop digital twin plus the Phase 2 "
        "distributed extensions (fleet ingestion, OpenDC/CloudSim simulation jobs, multi-agent "
        "Orchestrator, fleet-wide dashboard) running in one process."
    ),
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()
    logger.info("AquaMind AI Phase 1+2 gateway started. DB=%s", settings.DATABASE_URL)


# --- Phase 2 routers first: takes precedence on shared paths (multi-agent /recommend) ---
app.include_router(p2_health.router)
app.include_router(fleet_telemetry.router)  # /telemetry/batch, /sites
app.include_router(simulate_opendc.router)  # /simulate/opendc[/{job_id}]
app.include_router(water_model_only.router)  # /watermodel/fleet-summary (adds to /watermodel/latest)
app.include_router(agents_router.router)  # /recommend (multi-agent), /recommendations, /agents/feedback
app.include_router(fleet_dashboard.router)  # /fleet/summary

# --- Phase 1 routers: single-device workflow, still fully functional standalone ---
app.include_router(p1_telemetry.router)  # /telemetry, /telemetry/latest
app.include_router(p1_simulate.router)  # /simulate, /watermodel/latest
app.include_router(p1_recommend.router)  # /recommend/latest (POST /recommend superseded above)
app.include_router(p1_memory.router)  # /memory/search
app.include_router(p1_dashboard.router)  # /dashboard/summary (single-device)
app.include_router(p1_reports.router)  # /reports/daily

# --- Static dashboard (fleet-aware SPA) ---
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DASHBOARD_DIR = os.path.join(_THIS_DIR, "..", "dashboard_web")
if os.path.isdir(_DASHBOARD_DIR):
    app.mount("/static", StaticFiles(directory=_DASHBOARD_DIR), name="static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(_DASHBOARD_DIR, "index.html"))
