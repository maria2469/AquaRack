import csv
import io
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["reports"])


def _daily_rows(db: Session):
    since = datetime.utcnow() - timedelta(days=1)
    telemetry = db.query(models.Telemetry).filter(models.Telemetry.timestamp >= since).all()
    rows = []
    for t in telemetry:
        wm = (
            db.query(models.WaterModelResult)
            .filter(models.WaterModelResult.telemetry_id == t.telemetry_id)
            .first()
        )
        rec = (
            db.query(models.Recommendation)
            .filter(models.Recommendation.telemetry_id == t.telemetry_id)
            .first()
        )
        rows.append(
            {
                "timestamp": t.timestamp.isoformat(),
                "device_id": t.device_id,
                "cpu_pct": t.cpu_pct,
                "gpu_pct": t.gpu_pct,
                "ram_pct": t.ram_pct,
                "cooling_load_kw": wm.cooling_load_kw if wm else "",
                "wue_factor": wm.wue_factor if wm else "",
                "water_l_per_hr": wm.water_l_per_hr if wm else "",
                "recommendation": rec.text if rec else "",
                "confidence": rec.confidence if rec else "",
            }
        )
    return rows


@router.get("/reports/daily")
def daily_report(format: str = Query("csv", pattern="^(csv|pdf)$"), db: Session = Depends(get_db)):
    rows = _daily_rows(db)

    if format == "csv":
        buf = io.StringIO()
        fieldnames = [
            "timestamp", "device_id", "cpu_pct", "gpu_pct", "ram_pct",
            "cooling_load_kw", "wue_factor", "water_l_per_hr", "recommendation", "confidence",
        ]
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        csv_content = buf.getvalue()
        
        # Upload to S3 if configured
        try:
            from app.lib.s3_client import upload_report_to_s3
            upload_report_to_s3("aquamind_daily_report.csv", csv_content, content_type="text/csv")
        except Exception:
            pass

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=aquamind_daily_report.csv"},
        )

    # PDF
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    path = os.path.join(settings.REPORTS_DIR, "aquamind_daily_report.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph("AquaMind AI — Daily Summary Report", styles["Title"]), Spacer(1, 12)]
    data = [["Time", "CPU%", "GPU%", "RAM%", "Cooling kW", "WUE", "Water L/hr", "Confidence"]]
    for r in rows[-40:]:
        data.append(
            [
                r["timestamp"][:19],
                r["cpu_pct"],
                r["gpu_pct"] or "-",
                r["ram_pct"],
                r["cooling_load_kw"],
                r["wue_factor"],
                r["water_l_per_hr"],
                r["confidence"],
            ]
        )
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D91")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)

    try:
        from app.lib.s3_client import upload_report_to_s3
        with open(path, "rb") as pdf_file:
            upload_report_to_s3("aquamind_daily_report.pdf", pdf_file.read(), content_type="application/pdf")
    except Exception:
        pass

    def iterfile():
        with open(path, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=aquamind_daily_report.pdf"},
    )
