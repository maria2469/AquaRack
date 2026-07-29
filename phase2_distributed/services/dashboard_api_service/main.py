"""
Dashboard API Service (SDD Phase 2, Section 9/22): independently deployable
FastAPI microservice serving both the Phase 1 single-device dashboard
summary and the Phase 2 fleet-wide summary/reporting, plus the static
dashboard SPA.

Run standalone:
    cd aquamind-ai
    SERVICE_PORT=8000 python -m phase2_distributed.services.dashboard_api_service.main
"""
import phase2_distributed.common.pathsetup  # noqa: F401

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import dashboard as p1_dashboard
from app.routers import reports as p1_reports

from phase2_distributed.common.migrate import run_migrations
from phase2_distributed.routers import fleet_dashboard, health

app = FastAPI(
    title="AquaMind AI — Dashboard API Service (Phase 2)",
    version="2.0.0",
    description="Single-device + fleet-wide dashboard summaries, reporting, and static SPA.",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()


app.include_router(health.router)
app.include_router(fleet_dashboard.router)  # GET /fleet/summary
app.include_router(p1_dashboard.router)  # GET /dashboard/summary (single-device)
app.include_router(p1_reports.router)  # GET /reports/daily

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DASHBOARD_DIR = os.path.join(_THIS_DIR, "..", "..", "dashboard_web")
if os.path.isdir(_DASHBOARD_DIR):
    app.mount("/static", StaticFiles(directory=_DASHBOARD_DIR), name="static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(_DASHBOARD_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SERVICE_PORT", 8000)))
