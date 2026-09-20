"""Referral system — farmer requests, officer accept/assign/resolve."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import farmer_required, get_current_user, staff_required
from app.database import get_db
from app.models.crop_report import CropReport
from app.models.referral import Referral
from app.models.user import User
from app.schemas.schemas import ReferralCreate, ReferralOut, ReferralStatusUpdate
from app.services.notification_service import notify
from app.utils.audit import audit

router = APIRouter(tags=["referrals"])


def _out(db: Session, r: Referral) -> dict:
    data = ReferralOut.model_validate(r).model_dump()
    report = db.get(CropReport, r.report_id)
    farmer = db.get(User, r.farmer_id)
    data["farmer_name"] = farmer.name if farmer else None
    data["crop"] = report.crop if report else None
    data["disease"] = report.disease if report else None
    data["location"] = report.location if report else None
    return data


@router.post("/referrals", response_model=ReferralOut, status_code=201)
def create_referral(payload: ReferralCreate, current: User = Depends(farmer_required),
                    db: Session = Depends(get_db)):
    report = db.get(CropReport, payload.report_id)
    if not report or report.farmer_id != current.id:
        raise HTTPException(status_code=404, detail="Report not found.")

    referral = Referral(report_id=report.id, farmer_id=current.id, reason=payload.reason)
    db.add(referral)
    db.flush()

    # Notify all officers
    officers = db.query(User).filter(User.role == "OFFICER", User.is_active.is_(True)).all()
    for officer in officers:
        notify(db, officer.id, "REFERRAL", "New referral request",
               f"{current.name} requested: {payload.reason} "
               f"({report.crop}, {report.disease or 'healthy'}).", report_id=report.id)

    audit(db, current.id, "REFERRAL_CREATED", "referral", referral.id,
          {"reason": payload.reason})
    db.commit()
    db.refresh(referral)
    return _out(db, referral)


@router.get("/referrals/mine", response_model=list[ReferralOut])
def my_referrals(current: User = Depends(farmer_required), db: Session = Depends(get_db)):
    referrals = (db.query(Referral)
                   .filter(Referral.farmer_id == current.id)
                   .order_by(Referral.created_at.desc()).all())
    return [_out(db, r) for r in referrals]


@router.get("/referrals", response_model=list[ReferralOut])
def all_referrals(status: str | None = None, current: User = Depends(staff_required),
                  db: Session = Depends(get_db)):
    q = db.query(Referral)
    if status:
        q = q.filter(Referral.status == status)
    return [_out(db, r) for r in q.order_by(Referral.created_at.desc()).limit(200).all()]


@router.patch("/referrals/{referral_id}/status", response_model=ReferralOut)
def update_referral_status(referral_id: int, payload: ReferralStatusUpdate,
                           current: User = Depends(staff_required),
                           db: Session = Depends(get_db)):
    referral = db.get(Referral, referral_id)
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found.")

    referral.status = payload.status
    if payload.officer_id:
        officer = db.get(User, payload.officer_id)
        if officer and officer.role == "OFFICER":
            referral.officer_id = officer.id
    elif current.role == "OFFICER" and not referral.officer_id:
        referral.officer_id = current.id  # self-assign

    if payload.status == "RESOLVED":
        from datetime import datetime, timezone

        referral.resolved_at = datetime.now(timezone.utc)

    notify(db, referral.farmer_id, "REFERRAL", f"Referral {payload.status.lower()}",
           f"Your referral was marked {payload.status}.", report_id=referral.report_id)

    audit(db, current.id,
          "REFERRAL_RESOLVED" if payload.status == "RESOLVED" else "REFERRAL_UPDATED",
          "referral", referral.id, {"status": payload.status})
    db.commit()
    db.refresh(referral)
    return _out(db, referral)
