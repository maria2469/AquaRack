"""
Fleet-wide dashboard aggregation (SDD Phase 2, Section 11.1 & FR-2.6:
"fleet-wide dashboards with per-site and aggregate views").

Kept as a distinct path (/api/v1/fleet/summary) rather than overriding
Phase 1's /api/v1/dashboard/summary, so a single-device Phase 1 view and
a fleet-wide Phase 2 view can both be shown side by side on the combined
dashboard.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import phase2_distributed.common.pathsetup  # noqa: F401
from app import models
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["fleet-dashboard"])


@router.get("/fleet/summary")
def fleet_summary(db: Session = Depends(get_db)):
    racks = db.query(models.Rack).all()
    sites = []
    total_cooling_kw = 0.0
    total_water_l_per_hr = 0.0
    total_recommendations = 0

    for rack in racks:
        latest_wm = (
            db.query(models.WaterModelResult)
            .join(models.Telemetry, models.Telemetry.telemetry_id == models.WaterModelResult.telemetry_id)
            .filter(models.Telemetry.rack_id == rack.rack_id)
            .order_by(models.WaterModelResult.computed_at.desc())
            .first()
        )
        latest_telemetry = (
            db.query(models.Telemetry)
            .filter(models.Telemetry.rack_id == rack.rack_id)
            .order_by(models.Telemetry.timestamp.desc())
            .first()
        )
        rec_count = (
            db.query(models.Recommendation)
            .join(models.Telemetry, models.Telemetry.telemetry_id == models.Recommendation.telemetry_id)
            .filter(models.Telemetry.rack_id == rack.rack_id)
            .count()
        )
        total_recommendations += rec_count
        if latest_wm:
            total_cooling_kw += latest_wm.cooling_load_kw
            total_water_l_per_hr += latest_wm.water_l_per_hr

        sites.append(
            {
                "rack_id": rack.rack_id,
                "site_id": getattr(rack, "site_id", None),
                "location": rack.location,
                "latest_utilisation_pct": latest_telemetry.cpu_pct if latest_telemetry else None,
                "latest_source": latest_telemetry.source if latest_telemetry else None,
                "latest_cooling_load_kw": latest_wm.cooling_load_kw if latest_wm else None,
                "latest_water_l_per_hr": latest_wm.water_l_per_hr if latest_wm else None,
                "recommendation_count": rec_count,
            }
        )

    open_incidents = db.query(models.Incident).filter(models.Incident.resolved.is_(False)).count()

    return {
        "num_sites_racks": len(racks),
        "fleet_total_cooling_load_kw": round(total_cooling_kw, 3),
        "fleet_total_water_l_per_hr": round(total_water_l_per_hr, 3),
        "fleet_total_recommendations": total_recommendations,
        "fleet_open_incidents": open_incidents,
        "sites": sites,
    }
