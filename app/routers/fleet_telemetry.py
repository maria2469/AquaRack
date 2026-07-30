"""
Fleet-scale telemetry endpoints (SDD Phase 2, Section 11.1):
  POST /api/v1/telemetry/batch   — bulk ingest from N edge agents (FR-2.1)
  GET  /api/v1/sites             — fleet view of all registered sites/racks (FR-2.6)
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

  # noqa: F401
from app import models
from app import schemas as p1_schemas
from app.database import get_db
from app.routers.telemetry import _get_or_create_rack

from app.models_ext import Site
from app.schemas_ext import SiteOut

router = APIRouter(prefix="/api/v1", tags=["fleet"])


@router.post("/telemetry/batch", status_code=202)
def ingest_batch(readings: List[p1_schemas.TelemetryReadingIn], db: Session = Depends(get_db)):
    """Bulk ingest from N concurrent laptop/edge agents (FR-2.1). The
    collector's HTTP client is unchanged (Section 3.2 migration table) —
    only the endpoint and an added device_id/site_id differ, both already
    present in the shared schema."""
    accepted, rejected = 0, 0
    rack = _get_or_create_rack(db)

    for reading in readings:
        try:
            row = models.Telemetry(
                rack_id=reading.rack_id or rack.rack_id,
                device_id=reading.device_id,
                site_id=reading.site_id,
                timestamp=reading.timestamp or datetime.utcnow(),
                cpu_pct=reading.cpu_pct,
                gpu_pct=reading.gpu_pct,
                ram_pct=reading.ram_pct,
                disk_io=reading.disk_io,
                fan_rpm=reading.fan_rpm,
                battery_pct=reading.battery_pct,
                source=reading.source,
            )
            db.add(row)
            accepted += 1
        except Exception:
            rejected += 1

    db.add(
        models.AuditLog(
            actor="fleet_ingest", action="telemetry.batch_ingest", entity_ref=f"accepted={accepted}"
        )
    )
    db.commit()
    return {"accepted": accepted, "rejected": rejected}


@router.get("/sites", response_model=List[SiteOut])
def list_sites(db: Session = Depends(get_db)):
    """Fleet view of all registered sites/racks (FR-2.6)."""
    racks = db.query(models.Rack).all()
    sites_by_id = {s.site_id: s for s in db.query(Site).all()}

    out = []
    for r in racks:
        cfg = db.query(models.RackConfig).filter(models.RackConfig.rack_id == r.rack_id).first()
        site = sites_by_id.get(getattr(r, "site_id", None))
        out.append(
            SiteOut(
                rack_id=r.rack_id,
                site_id=getattr(r, "site_id", None),
                name=site.name if site else r.location,
                region=site.region if site else None,
                capacity_kw=r.capacity_kw,
                node_count=r.node_count,
                location=r.location,
                mode=cfg.mode if cfg else "laptop",
            )
        )
    return out
