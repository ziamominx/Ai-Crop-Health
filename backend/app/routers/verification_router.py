"""Officer verification + model feedback — the LEARNING stage of the agent loop."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import staff_required
from app.database import get_db
from app.models import (CropReport, ModelFeedback, ModelVersion, Notification,
                        OfficerVerification, Recommendation, User)
from app.schemas.schemas import VerifyIn
from app.services.notification_service import notify
from app.utils.audit import audit

router = APIRouter(prefix="/verify", tags=["verification"])


@router.post("/{report_id}", status_code=200)
def verify_report(report_id: int, payload: VerifyIn,
                  current: User = Depends(staff_required), db: Session = Depends(get_db)):
    """Officer confirms the AI prediction or corrects it.

    Confirm  -> officer_verification + was_correct=True feedback row.
    Correct  -> officer_verification + was_correct=False feedback row with both
                predicted and actual disease stored; report status becomes CORRECTED.
    """
    report = db.get(CropReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    original = report.disease
    corrected = payload.corrected_disease
    was_correct = corrected is None or corrected == original

    db.add(OfficerVerification(
        report_id=report.id,
        officer_id=current.id,
        original_disease=original,
        corrected_disease=corrected,
        remarks=payload.remarks,
        lab_sample_requested=payload.lab_sample_requested,
    ))

    # Model feedback row (learning loop)
    version = report.model_version or "unknown"
    db.add(ModelFeedback(
        report_id=report.id,
        predicted_disease=original,
        actual_disease=corrected if not was_correct else original,
        was_correct=was_correct,
        officer_id=current.id,
        model_version=version,
    ))

    if not was_correct and corrected:
        report.disease = corrected
        report.status = "CORRECTED"
    else:
        report.status = "VERIFIED"
    report.officer_verified = True
    report.low_confidence = False

    # Retrain recommendation rows may need updating if the disease changed — keep simple:
    if not was_correct and corrected:
        # Replace generic recommendations with the corrected-disease ones is a
        # manual officer task; we only note it in the audit + notification here.
        pass

    if payload.lab_sample_requested:
        notify(db, report.farmer_id, "REFERRAL", "Lab sample requested",
               "An agriculture officer has requested a lab sample for this report.",
               report_id=report.id)

    notify(db, report.farmer_id, "VERIFICATION",
           "Report reviewed by an officer",
           (f"Your {report.crop} report was verified by {current.name}"
            + (f" — diagnosis corrected to {corrected}." if not was_correct and corrected
               else " — AI assessment confirmed.")),
           report_id=report.id)

    notify(db, current.id, "FEEDBACK", "Model feedback recorded",
           (f"Feedback stored: predicted '{original or 'Healthy'}' → "
            f"actual '{corrected or original or 'Healthy'}'."))

    audit(db, current.id, "OFFICER_VERIFICATION", "report", report.id,
          {"correct": was_correct, "corrected_to": corrected})
    if not was_correct:
        audit(db, current.id, "DIAGNOSIS_CORRECTED", "report", report.id,
              {"from": original, "to": corrected})
    db.commit()
    return {"detail": "Verification stored.", "was_correct": was_correct,
            "status": report.status}


@router.get("/feedback", response_model=list[dict])
def list_feedback(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    """Model feedback rows (officer/admin)."""
    rows = (db.query(ModelFeedback, User, CropReport)
              .join(User, ModelFeedback.officer_id == User.id)
              .join(CropReport, ModelFeedback.report_id == CropReport.id)
              .order_by(ModelFeedback.created_at.desc())
              .limit(200).all())
    return [
        {
            "id": fb.id,
            "report_id": fb.report_id,
            "crop": report.crop,
            "predicted_disease": fb.predicted_disease,
            "actual_disease": fb.actual_disease,
            "was_correct": fb.was_correct,
            "officer_name": officer.name,
            "model_version": fb.model_version,
            "in_retraining_queue": fb.in_retraining_queue,
            "created_at": fb.created_at,
        }
        for fb, officer, report in rows
    ]
