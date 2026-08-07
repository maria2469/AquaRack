from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


def _get_or_create_rack(db: Session) -> models.Rack:
    rack = db.query(models.Rack).first()
    if rack:
        return rack
    rack = models.Rack(
        capacity_kw=settings.RACK_CAPACITY_KW,
        node_count=settings.RACK_NODE_COUNT,
        location="laptop-local",
    )
    db.add(rack)
    db.commit()
    db.refresh(rack)
    db.add(models.RackConfig(rack_id=rack.rack_id, mode="laptop", sim_params={}))
    db.commit()
    return rack


@router.post("/telemetry", status_code=202)
def ingest_telemetry(reading: schemas.TelemetryReadingIn, db: Session = Depends(get_db)):
    try:
        rack = _get_or_create_rack(db)
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
            weather_temp=reading.weather_temp,
            humidity=reading.humidity,
            source=reading.source,
        )
        db.add(row)
        db.add(
            models.AuditLog(
                actor=reading.device_id, action="telemetry.ingest", entity_ref=row.telemetry_id
            )
        )
        db.commit()
        db.refresh(row)
        return {"telemetry_id": row.telemetry_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to ingest telemetry: {str(e)}")


@router.get("/telemetry/latest", response_model=schemas.TelemetryReadingOut)
def latest_telemetry(db: Session = Depends(get_db)):
    row = db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).first()
    if not row:
        raise HTTPException(status_code=404, detail="No telemetry recorded yet")
    return row