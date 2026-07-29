"""
Telemetry Service (SDD Phase 2, Section 9/22): independently deployable
FastAPI microservice handling single-device and fleet-scale telemetry
ingestion (FR-2.1).

Run standalone:
    cd aquamind-ai
    SERVICE_PORT=8001 python -m phase2_distributed.services.telemetry_service.main
"""
import phase2_distributed.common.pathsetup  # noqa: F401  (must be the first import)

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import telemetry as p1_telemetry

from phase2_distributed.common.migrate import run_migrations
from phase2_distributed.routers import fleet_telemetry, health

app = FastAPI(
    title="AquaMind AI — Telemetry Service (Phase 2)",
    version="2.0.0",
    description="Single-device + fleet-scale telemetry ingestion (FR-2.1).",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()


app.include_router(health.router)
app.include_router(fleet_telemetry.router)
app.include_router(p1_telemetry.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SERVICE_PORT", 8001)))
