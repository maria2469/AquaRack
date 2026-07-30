from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.config import settings
from app.digital_twin.laptop_mode import DigitalTwinEngine, RackProfile
from app.water_model.thermo import WaterModel

router = APIRouter(prefix="/api/v1", tags=["simulate"])


def _get_reading(db: Session, telemetry_id: str = None) -> models.Telemetry:
    if telemetry_id:
        row = db.get(models.Telemetry, telemetry_id)
    else:
        row = db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).first()
    if not row:
        raise HTTPException(status_code=404, detail="No telemetry available to simulate")
    return row


def run_full_pipeline(db: Session, telemetry_id: str = None) -> dict:
    """Shared helper: Digital Twin -> Water Model, used by /simulate and /recommend."""
    reading = _get_reading(db, telemetry_id)
    rack = db.get(models.Rack, reading.rack_id) if reading.rack_id else db.query(models.Rack).first()
    profile = RackProfile.load_config(
        rack_id=rack.rack_id if rack else "default",
        capacity_kw=rack.capacity_kw if rack else settings.RACK_CAPACITY_KW,
        node_count=rack.node_count if rack else settings.RACK_NODE_COUNT,
    )
    twin = DigitalTwinEngine(profile, mode="laptop")
    twin_state = twin.simulate(reading)

    weather = db.query(models.Weather).order_by(models.Weather.timestamp.desc()).first()
    ambient_temp = weather.ambient_temp if weather else settings.DEFAULT_AMBIENT_TEMP_C
    humidity = weather.humidity if weather else settings.DEFAULT_HUMIDITY_PCT

    water_model = WaterModel(
        ambient_temp=ambient_temp,
        humidity=humidity,
        pue_thermal_overhead=settings.PUE_THERMAL_OVERHEAD,
    )
    water_out = water_model.compute_water_usage(twin_state.thermal_load_kw)

    wm_row = models.WaterModelResult(
        telemetry_id=reading.telemetry_id,
        wue_factor=water_out["wue_factor"],
        cooling_load_kw=water_out["cooling_load_kw"],
        water_l_per_hr=water_out["water_l_per_hr"],
        pue=water_out["pue"],
        utilisation_pct=twin_state.utilisation_pct,
        thermal_load_kw=twin_state.thermal_load_kw,
        power_draw_kw=twin_state.power_draw_kw,
    )
    db.add(wm_row)

    # Threshold-based incident flagging (Phase 1, per ER diagram "incidents" notes)
    if twin_state.utilisation_pct >= 85:
        db.add(
            models.Incident(
                telemetry_id=reading.telemetry_id,
                severity="high",
                description=f"Utilisation critical at {twin_state.utilisation_pct}%",
                resolved=False,
            )
        )

    db.commit()
    db.refresh(wm_row)
    return {"reading": reading, "twin_state": twin_state, "water_out": water_out, "wm_row": wm_row}


@router.post("/simulate")
def simulate(body: schemas.RecommendationRequest, db: Session = Depends(get_db)):
    result = run_full_pipeline(db, body.telemetry_id)
    return {
        "utilisation": result["twin_state"].utilisation_pct,
        "thermal_load_kw": result["twin_state"].thermal_load_kw,
        "power_draw_kw": result["twin_state"].power_draw_kw,
        "water_model": result["water_out"],
    }


@router.get("/watermodel/latest", response_model=schemas.WaterModelOut)
def latest_water_model(db: Session = Depends(get_db)):
    row = (
        db.query(models.WaterModelResult)
        .order_by(models.WaterModelResult.computed_at.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No water model results yet")
    return row
