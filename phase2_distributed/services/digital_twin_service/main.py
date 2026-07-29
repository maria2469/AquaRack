"""
Digital Twin Service (SDD Phase 2, Section 9/22): independently deployable
FastAPI microservice running the Digital Twin Engine — both Phase 1's
laptop-mode /simulate pipeline and Phase 2's async OpenDC/CloudSim jobs
(FR-2.2).

Run standalone:
    cd aquamind-ai
    SERVICE_PORT=8002 python -m phase2_distributed.services.digital_twin_service.main
"""
import phase2_distributed.common.pathsetup  # noqa: F401

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import simulate as p1_simulate

from phase2_distributed.common.migrate import run_migrations
from phase2_distributed.routers import health, simulate_opendc

app = FastAPI(
    title="AquaMind AI — Digital Twin Service (Phase 2)",
    version="2.0.0",
    description="Laptop-mode simulate pipeline + async OpenDC/CloudSim simulation jobs (FR-2.2).",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()


app.include_router(health.router)
app.include_router(p1_simulate.router)  # POST /simulate, GET /watermodel/latest (laptop-mode pipeline)
app.include_router(simulate_opendc.router)  # POST/GET /simulate/opendc/*

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SERVICE_PORT", 8002)))
