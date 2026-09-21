"""Model management — versions, feedback submission, retraining queue (admin/officer)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import staff_required
from app.config import settings
from app.database import get_db
from app.models import ModelFeedback, ModelVersion
from app.models.user import User
from app.schemas.schemas import FeedbackIn, ModelVersionOut, RetrainQueueIn
from app.utils.audit import audit

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/versions", response_model=list[ModelVersionOut])
def model_versions(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    return db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()


@router.post("/versions", response_model=ModelVersionOut, status_code=201)
def create_version(version: str, model_name: str, notes: str | None = None,
                   current: User = Depends(staff_required), db: Session = Depends(get_db)):
    """Register a model version (metadata only — weights stay outside the DB)."""
    if db.query(ModelVersion).filter(ModelVersion.version == version).first():
        raise HTTPException(status_code=409, detail="Version already exists.")
    mv = ModelVersion(version=version, model_name=model_name, notes=notes,
                      status="ACTIVE" if settings.AI_MODE == "REAL_MODEL" else "QUEUED")
    db.add(mv)
    audit(db, current.id, "MODEL_VERSION_CREATED", "model_version", mv.id, {"version": version})
    db.commit()
    db.refresh(mv)
    return mv


@router.post("/feedback", status_code=201)
def submit_feedback(payload: FeedbackIn, current: User = Depends(staff_required),
                    db: Session = Depends(get_db)):
    """Direct feedback submission (used by the officer UI 'correct' flow too)."""
    fb = ModelFeedback(
        report_id=payload.report_id,
        predicted_disease=payload.predicted_disease,
        actual_disease=payload.actual_disease,
        was_correct=payload.was_correct,
        officer_id=current.id,
    )
    db.add(fb)
    audit(db, current.id, "MODEL_FEEDBACK_SUBMITTED", "report", payload.report_id,
          {"was_correct": payload.was_correct})
    db.commit()
    db.refresh(fb)
    return {"id": fb.id, "detail": "Feedback stored."}


@router.post("/retraining/queue", status_code=200)
def queue_retraining(payload: RetrainQueueIn, current: User = Depends(staff_required),
                     db: Session = Depends(get_db)):
    """Queue confirmed feedback rows for the NEXT retraining cycle.

    This does NOT retrain anything automatically — it marks rows as queued so a
    separate, explicit training process can pick them up.
    """
    q = db.query(ModelFeedback).filter(ModelFeedback.in_retraining_queue.is_(False))
    if payload.feedback_ids:
        q = q.filter(ModelFeedback.id.in_(payload.feedback_ids))
    rows = q.all()
    if not rows:
        return {"queued": 0, "detail": "Nothing new to queue."}
    for row in rows:
        row.in_retraining_queue = True
    # Ensure a queued model version exists to represent the next cycle
    next_version = f"retrain-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    if not db.query(ModelVersion).filter(ModelVersion.version == next_version).first():
        db.add(ModelVersion(version=next_version, model_name="Agricure Crop Disease Model",
                            status="QUEUED", notes="Created by retraining queue"))
    audit(db, current.id, "RETRAINING_QUEUED", "model_feedback", None,
          {"count": len(rows)})
    db.commit()
    return {"queued": len(rows), "detail": "Queued for the next model retraining cycle."}


@router.get("/status")
def model_status(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    """Runtime inference configuration (no secrets). Honors the admin override."""
    from app.services import ai_mode

    info = ai_mode.effective_ai_mode(db)
    active = info["mode"]
    if active == "GROK_VISION":
        note = "Grok vision inference via the xAI API — real third-party AI model."
    elif active == "REAL_MODEL":
        note = "Trained model inference (Keras weights loaded from MODEL_PATH)."
    elif active == "DEMO_MODEL":
        note = ("Demo inference is deterministic (hash-based) and clearly labelled — "
                "it is NOT a real classifier.")
    else:
        note = ("Rule-based image analysis of the uploaded photo — real pixel "
                "measurement, not a trained neural network.")
    if info["fallback_applied"]:
        note += f" (Fallback active: {info['fallback_applied']}.)"
    return {
        "ai_mode": active,
        "env_mode": info["env_mode"],
        "model_version": settings.MODEL_VERSION,
        "real_model_available": active == "REAL_MODEL",
        "grok_vision_ready": info["grok_available"],
        "grok_model": settings.GROK_MODEL,
        "demo_note": note,
    }
