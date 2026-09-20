"""Analytics — officer dashboard aggregates and regional hotspot detection."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import staff_required
from app.database import get_db
from app.models import AgentActivity, CropReport, Referral
from app.models.user import User
from app.schemas.schemas import DashboardStats, HotspotOut, ReportOut
from app.utils.audit import audit

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/hotspots", response_model=list[HotspotOut])
def hotspots(days: int = 30, current: User = Depends(staff_required),
             db: Session = Depends(get_db)):
    """Group recent reports by location: counts, high-risk counts, dominant disease.

    Locations are labelled "potential hotspots" (never 'confirmed outbreaks').
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    reports = (db.query(CropReport)
                 .filter(CropReport.created_at >= since)
                 .all())

    grouped: dict[str, list[CropReport]] = {}
    for r in reports:
        grouped.setdefault(r.location or "Unknown", []).append(r)

    hotspots: list[HotspotOut] = []
    for location, items in grouped.items():
        high = sum(1 for r in items if r.risk_level == "High")
        diseases = [r.disease for r in items if r.disease]
        dominant = Counter(diseases).most_common(1)
        risks = [r.risk_level for r in items]
        dominant_risk = Counter(risks).most_common(1)[0][0] if risks else None
        count = len(items)
        # Potential hotspot heuristic (prototype): >=3 reports with a high-risk share
        is_hotspot = count >= 3 and (high >= max(1, count // 3))
        hotspots.append(HotspotOut(
            location=location, report_count=count, high_risk_count=high,
            dominant_disease=dominant[0][0] if dominant else None,
            dominant_risk=dominant_risk,
            is_potential_hotspot=is_hotspot,
        ))

    hotspots.sort(key=lambda h: h.report_count, reverse=True)
    return hotspots


@router.get("/dashboard", response_model=DashboardStats)
def officer_dashboard(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    reports = db.query(CropReport).all()
    recent = (db.query(CropReport)
                .options(joinedload(CropReport.farmer), joinedload(CropReport.farm))
                .order_by(CropReport.created_at.desc()).limit(15).all())

    def _out(r):
        data = ReportOut.model_validate(r).model_dump()
        data["farmer_name"] = r.farmer.name if r.farmer else None
        data["farm_name"] = r.farm.farm_name if r.farm else None
        return data

    audit(db, current.id, "DASHBOARD_VIEWED", "report", None)
    db.commit()
    return DashboardStats(
        total_reports=len(reports),
        high_risk=sum(1 for r in reports if r.risk_level == "High"),
        moderate_risk=sum(1 for r in reports if r.risk_level == "Moderate"),
        low_risk=sum(1 for r in reports if r.risk_level == "Low"),
        pending_verification=sum(1 for r in reports if not r.officer_verified
                                 and r.status in ("ANALYZED",)),
        open_referrals=db.query(Referral)
                         .filter(Referral.status != "RESOLVED").count(),
        recent_reports=[_out(r) for r in recent],
    )


@router.get("/agent-activity", response_model=list[dict])
def agent_activity_feed(limit: int = 60, current: User = Depends(staff_required),
                        db: Session = Depends(get_db)):
    """Latest agent activity across all reports (officer view of the agent loop)."""
    rows = (db.query(AgentActivity, CropReport)
              .join(CropReport, AgentActivity.report_id == CropReport.id)
              .order_by(AgentActivity.created_at.desc())
              .limit(min(limit, 200)).all())
    return [
        {
            "id": act.id,
            "report_id": report.id,
            "crop": report.crop,
            "disease": report.disease,
            "stage": act.stage,
            "message": act.message,
            "created_at": act.created_at,
        }
        for act, report in rows
    ]


@router.get("/disease-distribution")
def disease_distribution(days: int = 90, current: User = Depends(staff_required),
                         db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    reports = db.query(CropReport).filter(CropReport.created_at >= since).all()
    counter = Counter(r.disease or "Healthy" for r in reports)
    return [{"label": label, "count": count} for label, count in counter.most_common()]
