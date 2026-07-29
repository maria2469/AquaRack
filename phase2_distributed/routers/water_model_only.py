"""
Water Model Service endpoints — a read-focused split of Phase 1's water
model output so it can scale independently of the Digital Twin service
that computes it (SDD Phase 2, Section 9: "each Application-tier component
becomes an independently deployable component with its own scaling
policy").
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import phase2_distributed.common.pathsetup  # noqa: F401
from app import models
from app import schemas as p1_schemas
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["water-model"])


@router.get("/watermodel/latest", response_model=p1_schemas.WaterModelOut)
def latest_water_model(db: Session = Depends(get_db)):
    row = db.query(models.WaterModelResult).order_by(models.WaterModelResult.computed_at.desc()).first()
    if not row:
        raise HTTPException(status_code=404, detail="No water model results yet")
    return row


@router.get("/watermodel/fleet-summary")
def fleet_water_summary(db: Session = Depends(get_db)):
    """Aggregate cooling load / water draw across every rack's latest reading."""
    racks = db.query(models.Rack).all()
    total_cooling_kw = 0.0
    total_water_l_per_hr = 0.0
    wue_values = []
    per_rack = []

    for rack in racks:
        latest = (
            db.query(models.WaterModelResult)
            .join(models.Telemetry, models.Telemetry.telemetry_id == models.WaterModelResult.telemetry_id)
            .filter(models.Telemetry.rack_id == rack.rack_id)
            .order_by(models.WaterModelResult.computed_at.desc())
            .first()
        )
        if latest:
            total_cooling_kw += latest.cooling_load_kw
            total_water_l_per_hr += latest.water_l_per_hr
            wue_values.append(latest.wue_factor)
            per_rack.append(
                {
                    "rack_id": rack.rack_id,
                    "cooling_load_kw": latest.cooling_load_kw,
                    "water_l_per_hr": latest.water_l_per_hr,
                    "wue_factor": latest.wue_factor,
                }
            )

    return {
        "num_racks_reporting": len(per_rack),
        "fleet_total_cooling_load_kw": round(total_cooling_kw, 3),
        "fleet_total_water_l_per_hr": round(total_water_l_per_hr, 3),
        "fleet_avg_wue_factor": round(sum(wue_values) / len(wue_values), 4) if wue_values else None,
        "per_rack": per_rack,
    }
