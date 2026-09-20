"""Crop report routes — submit → AI analysis → agent decision → result."""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.agents.pipeline import nearby_similar_count, recent_activity, run_full_pipeline
from app.ai import inference_service
from app.auth.dependencies import farmer_required, get_current_user, staff_required
from app.database import SessionLocal, get_db
from app.models import (AgentDecision, AgentActivity, CropReport, Farm,
                        Recommendation, SensorReading, User)
from app.schemas.schemas import (AgentActivityOut, AgentDecisionOut,
                                 RecommendationOut, ReportCreate, ReportDetail,
                                 ReportOut)
from app.services.storage import resolve_url, save_image
from app.utils.audit import audit

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_out(db: Session, r: CropReport) -> dict:
    data = ReportOut.model_validate(r).model_dump()
    data["image_url"] = resolve_url(r.image_url, r.image_path)
    data["risk_factors"] = json.loads(r.risk_factors) if r.risk_factors else []
    data["farmer_name"] = r.farmer.name if r.farmer else None
    data["farm_name"] = r.farm.farm_name if r.farm else None
    return data


def analyze_report_task(report_id: int):
    """Background task: run the agent pipeline in its own session."""
    db = SessionLocal()
    try:
        report = db.get(CropReport, report_id)
        if report and report.status == "PENDING":
            run_full_pipeline(db, report)
            audit(db, report.farmer_id, "AI_ANALYSIS_PERFORMED", "report", report.id,
                  {"model": report.model_version, "demo": report.is_demo_inference})
            audit(db, report.farmer_id, "AGENT_DECISION_GENERATED", "report", report.id,
                  {"risk": report.risk_level})
            db.commit()
    except Exception:
        db.rollback()
        # Mark the failure so the farmer isn't stuck on "analyzing" forever
        try:
            report = db.get(CropReport, report_id)  # type: ignore[name-defined]
            if report:
                report.status = "PENDING"
                db.add(report)
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


@router.post("", response_model=ReportDetail, status_code=201)
async def submit_report(
    background: BackgroundTasks,
    crop: str = Form(...),
    farm_id: int = Form(...),
    image: UploadFile | None = Form(None),
    pest_count: int | None = Form(None),
    soil_moisture: float | None = Form(None),
    leaf_wetness: float | None = Form(None),
    trap_type: str | None = Form(None),
    current: User = Depends(farmer_required),
    db: Session = Depends(get_db),
):
    """Farmer submits a crop report: image + optional sensor numbers."""
    farm = db.get(Farm, farm_id)
    if not farm or farm.farmer_id != current.id:
        raise HTTPException(status_code=404, detail="Farm not found.")

    image_url, image_path = (None, None)
    if image is not None and (image.filename or "").strip():
        image_url, image_path = await save_image(image, current.id)

    report = CropReport(
        farmer_id=current.id,
        farm_id=farm.id,
        crop=crop.strip(),
        image_url=image_url,
        image_path=image_path,
        location=farm.location,
        pest_count=pest_count,
        soil_moisture=soil_moisture,
        leaf_wetness=leaf_wetness,
        status="PENDING",
    )
    db.add(report)
    db.flush()

    # Persist the submitted sensor numbers as a farm reading too (feed history)
    if any(v is not None for v in (pest_count, soil_moisture, leaf_wetness)):
        db.add(SensorReading(farm_id=farm.id, trap_type=trap_type,
                             soil_moisture=soil_moisture,
                             leaf_wetness=leaf_wetness, pest_count=pest_count))

    audit(db, current.id, "REPORT_SUBMITTED", "report", report.id,
          {"crop": report.crop, "farm": farm.farm_name})
    db.commit()
    db.refresh(report)

    background.add_task(analyze_report_task, report.id)
    return get_report(report.id, current, db)


@router.post("/{report_id}/analyze", response_model=ReportDetail)
def analyze(report_id: int, current: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    """(Re-)run AI analysis + agent decision for a report."""
    report = db.get(CropReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if current.role == "FARMER" and report.farmer_id != current.id:
        raise HTTPException(status_code=403, detail="Not your report.")

    run_full_pipeline(db, report)
    audit(db, current.id, "AI_ANALYSIS_PERFORMED", "report", report.id,
          {"model": report.model_version, "demo": report.is_demo_inference})
    db.commit()
    db.refresh(report)
    return get_report(report.id, current, db)


def get_report(report_id: int, current: User, db: Session) -> ReportDetail:
    report = (db.query(CropReport)
                .options(joinedload(CropReport.farmer), joinedload(CropReport.farm))
                .filter(CropReport.id == report_id).first())
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if current.role == "FARMER" and report.farmer_id != current.id:
        raise HTTPException(status_code=403, detail="Not your report.")

    data = _report_out(db, report)
    decision = db.query(AgentDecision).filter(
        AgentDecision.report_id == report.id).order_by(AgentDecision.created_at.desc()).first()
    recs = (db.query(Recommendation)
            .filter(Recommendation.report_id == report.id)
            .order_by(Recommendation.id).all())

    if decision is not None:
        decision_data = AgentDecisionOut.model_validate(decision).model_dump()
        try:
            decision_data["factors"] = json.loads(decision.factors) if decision.factors else []
        except (TypeError, ValueError):
            decision_data["factors"] = []
        data["agent_decision"] = decision_data
    else:
        data["agent_decision"] = None
    data["recommendations"] = [RecommendationOut.model_validate(x).model_dump() for x in recs]
    data["activity"] = [
        AgentActivityOut.model_validate(a).model_dump() for a in recent_activity(db, report.id)]
    data["nearby_similar"] = nearby_similar_count(db, report)
    return ReportDetail.model_validate(data)


@router.get("", response_model=list[ReportOut])
def my_history(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Farmer's own reports, newest first."""
    reports = (db.query(CropReport)
                 .options(joinedload(CropReport.farmer), joinedload(CropReport.farm))
                 .filter(CropReport.farmer_id == current.id)
                 .order_by(CropReport.created_at.desc()).limit(50).all())
    return [_report_out(db, r) for r in reports]


@router.get("/all", response_model=list[ReportOut])
def all_reports(status: str | None = None, limit: int = 100,
                current: User = Depends(staff_required), db: Session = Depends(get_db)):
    """Officer/Admin: all reports (newest first) — used by the officer dashboard
    and the admin live data view (farmer attribution + stored image included)."""
    q = (db.query(CropReport)
           .options(joinedload(CropReport.farmer), joinedload(CropReport.farm)))
    if status:
        q = q.filter(CropReport.status == status)
    reports = q.order_by(CropReport.created_at.desc()).limit(min(limit, 500)).all()
    return [_report_out(db, r) for r in reports]


@router.get("/all/grouped")
def all_reports_grouped(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    """All reports grouped per user (admin live view of the sample database)."""
    reports = (db.query(CropReport)
                 .options(joinedload(CropReport.farmer), joinedload(CropReport.farm))
                 .order_by(CropReport.created_at.desc())
                 .limit(500).all())
    grouped: dict[int, dict] = {}
    for r in reports:
        g = grouped.setdefault(
            r.farmer_id,
            {
                "farmer_id": r.farmer_id,
                "farmer_name": r.farmer.name if r.farmer else "Unknown",
                "farmer_email": r.farmer.email if r.farmer else None,
                "sample_count": 0,
                "reports": [],
            },
        )
        g["sample_count"] += 1
        g["reports"].append({
            "id": r.id,
            "crop": r.crop,
            "disease": r.disease,
            "is_healthy": r.is_healthy,
            "confidence": r.confidence,
            "severity": r.severity,
            "risk_level": r.risk_level,
            "risk_score": r.risk_score,
            "status": r.status,
            "location": r.farm.location if r.farm else r.location,
            "farm_name": r.farm.farm_name if r.farm else None,
            "image_url": resolve_url(r.image_url, r.image_path),
            "model_version": r.model_version,
            "is_demo_inference": r.is_demo_inference,
            "officer_verified": r.officer_verified,
            "created_at": r.created_at,
        })
    return list(grouped.values())


@router.get("/{report_id}", response_model=ReportDetail)
def report_detail(report_id: int, current: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return get_report(report_id, current, db)


@router.get("/{report_id}/thumbnail")
def report_thumbnail(report_id: int, current: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Small base64 thumbnail for history lists (demo-friendly)."""
    report = db.get(CropReport, report_id)
    if not report or (current.role == "FARMER" and report.farmer_id != current.id):
        raise HTTPException(status_code=404, detail="Report not found.")
    thumb = inference_service.thumbnail_data_url(report.image_path)
    return {"thumbnail": thumb}
