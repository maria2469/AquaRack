"""
Water Model Service (SDD Phase 2, Section 9/22): independently deployable
FastAPI microservice serving Water Model reads and fleet-wide cooling/
water aggregates, scaled separately from the Digital Twin service that
computes the underlying values.

Run standalone:
    cd aquamind-ai
    SERVICE_PORT=8003 python -m phase2_distributed.services.water_model_service.main
"""
import phase2_distributed.common.pathsetup  # noqa: F401

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db

from phase2_distributed.common.migrate import run_migrations
from phase2_distributed.routers import health, water_model_only

app = FastAPI(
    title="AquaMind AI — Water Model Service (Phase 2)",
    version="2.0.0",
    description="Water/cooling reads and fleet-wide aggregates (Section 13).",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()


app.include_router(health.router)
app.include_router(water_model_only.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SERVICE_PORT", 8003)))
