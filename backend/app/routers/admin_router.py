"""Admin dashboard — users, system statistics, model overview, audit log."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.ai import inference_service
from app.auth.dependencies import admin_required
from app.config import settings
from app.database import engine, get_db
from app.models import (AuditLog, CropReport, ModelFeedback, ModelVersion,
                        Notification, Referral, User)
from app.schemas.schemas import AdminStats, ModelVersionOut, UserOut
from app.services import ai_mode
from app.services.db_view import generate_database_view
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


@router.get("/database-view", response_class=HTMLResponse)
def database_view(limit: int = 200, current: User = Depends(admin_required),
                  db: Session = Depends(get_db)):
    """Admin-only read-only snapshot of every table, rendered as a standalone page.

    The admin panel fetches this with its JWT and opens the result in a new tab,
    so no authentication token is ever put in a URL.
    """
    page = generate_database_view(
        engine,
        limit=max(10, min(limit, 1000)),
        image_base=settings.PUBLIC_BASE_URL,
    )
    audit(db, current.id, "DATABASE_VIEWED", "database", None, {"limit": limit})
    db.commit()
    return HTMLResponse(content=page)


@router.get("/ai-mode")
def get_ai_mode(current: User = Depends(admin_required), db: Session = Depends(get_db)):
    """Active AI inference mode with availability info (admin panel toggle)."""
    info = ai_mode.effective_ai_mode(db)
    info["valid_modes"] = list(ai_mode.VALID_MODES)
    info["grok_model"] = settings.GROK_MODEL
    return info


@router.patch("/ai-mode")
def set_ai_mode(mode: str, current: User = Depends(admin_required),
                db: Session = Depends(get_db)):
    """Switch the AI inference mode at runtime (stored in system_settings)."""
    try:
        info = ai_mode.set_ai_mode(db, mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    inference_service.reset_models()
    audit(db, current.id, "AI_MODE_CHANGED", "system_setting", None,
          {"mode": mode, "fallback_applied": info["fallback_applied"]})
    db.commit()
    return info


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
