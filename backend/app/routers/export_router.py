"""CSV exports — Officer/Admin only (no private farmer data for unauthorized users)."""
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import staff_required
from app.database import get_db
from app.models import (CropReport, Farm, ModelFeedback, Referral,
                        SensorReading, User)
from app.utils.audit import audit

router = APIRouter(prefix="/export", tags=["export"])


def _csv_response(filename: str, header: list[str], rows: list[list]) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports")
def export_reports(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    reports = db.query(CropReport).order_by(CropReport.created_at).all()
    rows = []
    for r in reports:
        rows.append([
            r.id, r.created_at, r.farmer.name if r.farmer else "", r.crop,
            r.disease or "Healthy", round(r.confidence, 1), r.severity, r.risk_level,
            r.risk_score, r.location, r.status,
            r.temperature or "", r.humidity or "", r.rainfall or "",
            r.soil_moisture or "", r.leaf_wetness or "", r.pest_count or "",
            r.model_version or "", "DEMO" if r.is_demo_inference else "REAL",
        ])
    audit(db, current.id, "DATA_EXPORTED", "report", None, {"kind": "reports"})
    db.commit()
    return _csv_response(
        "agricure_reports.csv",
        ["id", "created_at", "farmer", "crop", "disease", "confidence", "severity",
         "risk", "risk_score", "location", "status", "temperature", "humidity",
         "rainfall", "soil_moisture", "leaf_wetness", "pest_count", "model_version",
         "inference_mode"],
        rows,
    )


@router.get("/feedback")
def export_feedback(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    rows = db.query(ModelFeedback, User, CropReport) \
             .join(User, ModelFeedback.officer_id == User.id) \
             .join(CropReport, ModelFeedback.report_id == CropReport.id) \
             .order_by(ModelFeedback.created_at).all()
    data = [[
        fb.id, fb.created_at, fb.report_id, report.crop,
        fb.predicted_disease or "Healthy", fb.actual_disease or "Healthy",
        "correct" if fb.was_correct else "corrected", officer.name, fb.model_version or "",
        "queued" if fb.in_retraining_queue else "not_queued",
    ] for fb, officer, report in rows]
    audit(db, current.id, "DATA_EXPORTED", "model_feedback", None, {"kind": "feedback"})
    db.commit()
    return _csv_response(
        "agricure_model_feedback.csv",
        ["id", "created_at", "report_id", "crop", "predicted", "actual", "outcome",
         "officer", "model_version", "retraining_status"],
        data,
    )


@router.get("/referrals")
def export_referrals(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    rows = db.query(Referral, User, CropReport) \
             .join(User, Referral.farmer_id == User.id) \
             .join(CropReport, Referral.report_id == CropReport.id) \
             .order_by(Referral.created_at).all()
    data = [[
        ref.id, ref.created_at, ref.report_id, farmer.name, report.crop,
        report.disease or "Healthy", report.location or "", ref.reason, ref.status,
        ref.resolved_at or "",
    ] for ref, farmer, report in rows]
    audit(db, current.id, "DATA_EXPORTED", "referral", None, {"kind": "referrals"})
    db.commit()
    return _csv_response(
        "agricure_referrals.csv",
        ["id", "created_at", "report_id", "farmer", "crop", "disease", "location",
         "reason", "status", "resolved_at"],
        data,
    )


@router.get("/sensors")
def export_sensors(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    rows = db.query(SensorReading, Farm) \
             .join(Farm, SensorReading.farm_id == Farm.id) \
             .order_by(SensorReading.recorded_at).all()
    data = [[
        reading.id, reading.recorded_at, farm.farm_name, farm.location,
        reading.trap_type or "", reading.temperature or "", reading.humidity or "",
        reading.soil_moisture or "", reading.leaf_wetness or "", reading.pest_count or "",
    ] for reading, farm in rows]
    audit(db, current.id, "DATA_EXPORTED", "sensor_reading", None, {"kind": "sensors"})
    db.commit()
    return _csv_response(
        "agricure_sensor_readings.csv",
        ["id", "recorded_at", "farm", "location", "trap_type", "temperature",
         "humidity", "soil_moisture", "leaf_wetness", "pest_count"],
        data,
    )
