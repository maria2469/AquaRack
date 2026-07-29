"""
Agent Service (SDD Phase 2, Section 6/9/22): independently deployable
FastAPI microservice running the multi-agent Orchestrator (FR-2.3).

Run standalone:
    cd aquamind-ai
    SERVICE_PORT=8004 python -m phase2_distributed.services.agent_service.main
"""
import phase2_distributed.common.pathsetup  # noqa: F401

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import recommend as p1_recommend  # GET /recommend/latest

from phase2_distributed.common.migrate import run_migrations
from phase2_distributed.routers import agents_router, health

app = FastAPI(
    title="AquaMind AI — Agent Service (Phase 2)",
    version="2.0.0",
    description="Multi-agent Orchestrator: Telemetry Analyst, Water & Cooling, "
    "Capacity Planning, Memory/RAG, Guardrail/Critic (FR-2.3).",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()


app.include_router(health.router)
app.include_router(agents_router.router)  # POST /recommend (multi-agent), /recommendations, /agents/feedback
app.include_router(p1_recommend.router)  # GET /recommend/latest (harmless overlap on POST is avoided by order)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SERVICE_PORT", 8004)))
