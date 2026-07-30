from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.db_retry import crdb_retry

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


def _fetch_dashboard(db: Session) -> schemas.DashboardSummary:
    """All DB reads for the dashboard — wrapped in CRDB retry logic."""
    latest_telemetry = (
        db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).first()
    )
    latest_water_model = (
        db.query(models.WaterModelResult)
        .order_by(models.WaterModelResult.computed_at.desc())
        .first()
    )
    latest_recommendation = (
        db.query(models.Recommendation).order_by(models.Recommendation.created_at.desc()).first()
    )
    history = (
        db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).limit(50).all()
    )
    history.reverse()
    open_incidents = db.query(models.Incident).filter(models.Incident.resolved.is_(False)).count()

    return schemas.DashboardSummary(
        latest_telemetry=latest_telemetry,
        latest_water_model=latest_water_model,
        latest_recommendation=latest_recommendation,
        telemetry_history=history,
        open_incidents=open_incidents,
    )


@router.get("/dashboard/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return crdb_retry(_fetch_dashboard, db)
