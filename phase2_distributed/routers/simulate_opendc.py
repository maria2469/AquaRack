"""
OpenDC/CloudSim simulation job endpoints (SDD Phase 2, Section 11.1, 15):
  POST /api/v1/simulate/opendc         — submit an async simulation job (FR-2.2)
  GET  /api/v1/simulate/opendc/{job_id} — poll job status/result (Section 15.3)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import phase2_distributed.common.pathsetup  # noqa: F401
from app.database import get_db

from phase2_distributed.common.models_ext import SimulationJob
from phase2_distributed.common.schemas_ext import SimulationJobResult, SimulationJobSpec
from phase2_distributed.digital_twin import cloudsim_adapter, opendc_adapter

router = APIRouter(prefix="/api/v1", tags=["simulate-opendc"])


@router.post("/simulate/opendc", status_code=202)
def submit_opendc_job(spec: SimulationJobSpec, db: Session = Depends(get_db)):
    submit_fn = opendc_adapter.submit_job if spec.mode == "opendc" else cloudsim_adapter.submit_job
    job = submit_fn(db, spec.model_dump())
    return {"job_id": job.job_id, "status": job.status, "mode": job.mode}


@router.get("/simulate/opendc/{job_id}", response_model=SimulationJobResult)
def get_opendc_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(SimulationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Simulation job not found")
    return job
