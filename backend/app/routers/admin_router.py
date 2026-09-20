"""Admin dashboard — users, system statistics, model overview, audit log."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import admin_required
from app.database import get_db
from app.models import (AuditLog, CropReport, ModelFeedback, ModelVersion,
                        Notification, Referral, User)
from app.schemas.schemas import AdminStats, ModelVersionOut, UserOut
from app.utils.audit import audit

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
def admin_stats(current: User = Depends(admin_required), db: Session = Depends(get_db)):
    model = (db.query(ModelVersion)
               .order_by(ModelVersion.created_at.desc()).first())
    return AdminStats(
        total_farmers=db.query(User).filter(User.role == "FARMER").count(),
        total_officers=db.query(User).filter(User.role == "OFFICER").count(),
        total_reports=db.query(CropReport).count(),
        high_risk_reports=db.query(CropReport).filter(CropReport.risk_level == "High").count(),
        pending_referrals=db.query(Referral).filter(Referral.status != "RESOLVED").count(),
        feedback_count=db.query(ModelFeedback).count(),
        retraining_queue=db.query(ModelFeedback)
                           .filter(ModelFeedback.in_retraining_queue.is_(True)).count(),
        model=ModelVersionOut.model_validate(model).model_dump() if model else None,
    )


@router.get("/users", response_model=list[UserOut])
def list_users(role: str | None = None, current: User = Depends(admin_required),
               db: Session = Depends(get_db)):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return q.order_by(User.created_at.desc()).limit(500).all()


@router.patch("/users/{user_id}/active", response_model=UserOut)
def set_user_active(user_id: int, is_active: bool,
                    current: User = Depends(admin_required), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user.is_active = is_active
    audit(db, current.id, "USER_STATUS_CHANGED", "user", user_id, {"is_active": is_active})
    db.commit()
    db.refresh(user)
    return user


@router.get("/audit-logs", response_model=list[dict])
def audit_logs(limit: int = 100, current: User = Depends(admin_required),
               db: Session = Depends(get_db)):
    rows = (db.query(AuditLog, User)
              .outerjoin(User, AuditLog.user_id == User.id)
              .order_by(AuditLog.created_at.desc())
              .limit(min(limit, 500)).all())
    return [
        {
            "id": log.id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "user_name": user.name if user else None,
            "metadata": log.metadata_json,
            "created_at": log.created_at,
        }
        for log, user in rows
    ]
