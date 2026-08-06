from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models_ext import JobPlacement
from app.models import Rack

logger = logging.getLogger("aquamind.actuation")
router = APIRouter(prefix="/api/v1/actuation", tags=["Actuation"])

class ThrottleRequest(BaseModel):
    rack_id: str
    target_fan_speed_rpm: float
    target_chiller_setpoint_c: float

class MigrateRequest(BaseModel):
    source_rack_id: str
    target_rack_id: str
    workload_type: str

@router.post("/hvac/throttle")
def hvac_throttle(req: ThrottleRequest, db: Session = Depends(get_db)):
    """Simulates throttling the HVAC system (Digital Twin Action)."""
    rack = db.query(Rack).filter(Rack.rack_id == req.rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")
    
    # In a real system, this would call an IoT controller or BMS webhook.
    logger.info(f"Actuating HVAC for rack {req.rack_id}: Fan -> {req.target_fan_speed_rpm} RPM, Setpoint -> {req.target_chiller_setpoint_c}°C")
    
    return {"status": "success", "message": f"HVAC parameters updated for {req.rack_id}", "applied_changes": req.model_dump()}

@router.post("/workload/migrate")
def workload_migrate(req: MigrateRequest, db: Session = Depends(get_db)):
    """Migrates a workload from one rack to another to balance thermal load."""
    job = db.query(JobPlacement).filter(
        JobPlacement.rack_id == req.source_rack_id,
        JobPlacement.workload_type == req.workload_type
    ).first()

    if not job:
        # If no specific job exists yet in our dummy DB, we'll just create one on the target.
        # In a real environment, we'd fail if the source workload didn't exist.
        job = JobPlacement(rack_id=req.target_rack_id, workload_type=req.workload_type)
        db.add(job)
        logger.warning(f"No existing {req.workload_type} found on {req.source_rack_id}. Created directly on {req.target_rack_id}.")
    else:
        # Migrate the job
        job.rack_id = req.target_rack_id
        logger.info(f"Migrating {req.workload_type} (Job {job.job_id}) from {req.source_rack_id} -> {req.target_rack_id}")

    db.commit()
    
    return {"status": "success", "message": f"Migrated {req.workload_type} to {req.target_rack_id}"}
