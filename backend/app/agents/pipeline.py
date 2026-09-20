"""Agent pipeline — orchestrates the full Intelligent Agent loop for one report.

PERCEPTION → STATE/MEMORY → REASONING → DECISION → ACTION → FEEDBACK → LEARNING

Every stage appends a timestamped row to agent_activity (visible in the UI as
"AI Agent Activity", required for the viva demonstration). All important outputs
are persisted: analysis fields on crop_reports, one agent_decisions row,
recommendations, notifications.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.ai import inference_service
from app.config import settings
from app.models import (AgentActivity, AgentDecision, CropReport,
                        Recommendation, SensorReading, User)
from app.agents.decision_engine import run_decision_engine
from app.services.notification_service import notify


def log_activity(db: Session, report_id: int, stage: str, message: str) -> None:
    db.add(AgentActivity(report_id=report_id, stage=stage, message=message[:290]))


def recent_activity(db: Session, report_id: int):
    return (db.query(AgentActivity)
              .filter(AgentActivity.report_id == report_id)
              .order_by(AgentActivity.created_at.asc()).all())


def nearby_similar_count(db: Session, report: CropReport) -> int:
    """STATE/MEMORY: count recent similar reports in the same location (14 days)."""
    if not report.disease or not report.location:
        return 0
    since = datetime.now(timezone.utc) - timedelta(days=14)
    return (db.query(CropReport)
              .filter(CropReport.id != report.id,
                      CropReport.disease == report.disease,
                      CropReport.location == report.location,
                      CropReport.created_at >= since)
              .count())


def latest_farm_sensors(db: Session, farm_id: int | None) -> SensorReading | None:
    if farm_id is None:
        return None
    return (db.query(SensorReading)
              .filter(SensorReading.farm_id == farm_id)
              .order_by(SensorReading.recorded_at.desc())
              .first())


def run_full_pipeline(db: Session, report: CropReport) -> CropReport:
    """Execute the whole agent loop for a PENDING report. Returns the updated report.

    Caller is responsible for commit/rollback of the outer transaction.
    """
    farmer = db.get(User, report.farmer_id)

    # ---------- PERCEPTION: image received + inference ----------
    log_activity(db, report.id, "PERCEPTION", "Crop image received")
    prediction = inference_service.analyze_image(
        report.image_path, report.crop, fallback_seed=f"report-{report.id}"
    )
    log_activity(
        db, report.id, "PERCEPTION",
        (f"AI analysis completed: {'Healthy' if prediction.is_healthy else prediction.disease}"
         f" ({prediction.confidence:.0f}% confidence, {prediction.model_version}"
         f"{', DEMO' if prediction.is_demo else ''})"),
    )

    report.disease = prediction.disease
    report.is_healthy = prediction.is_healthy
    report.confidence = round(prediction.confidence, 1)
    report.severity = prediction.severity
    report.model_version = prediction.model_version
    report.is_demo_inference = prediction.is_demo
    report.low_confidence = (not prediction.is_healthy and prediction.confidence < 78)

    # ---------- PERCEPTION: environment ----------
    weather = None
    farm = report.farm
    if farm is not None:
        from app.services.weather import get_weather

        weather = get_weather(farm.latitude, farm.longitude, farm.location)
        report.temperature = report.temperature or weather["temperature"]
        report.humidity = report.humidity or weather["humidity"]
        report.rainfall = report.rainfall or weather["rainfall_24h"]
        log_activity(
            db, report.id, "PERCEPTION",
            (f"Environmental conditions checked ({weather['mode']}): "
             f"{report.temperature:.0f}°C, {report.humidity:.0f}% humidity, "
             f"{report.rainfall:.0f} mm rain/24h"),
        )

    sensors = latest_farm_sensors(db, report.farm_id)
    if sensors:
        report.soil_moisture = report.soil_moisture if report.soil_moisture is not None else sensors.soil_moisture
        report.leaf_wetness = report.leaf_wetness if report.leaf_wetness is not None else sensors.leaf_wetness
        report.pest_count = report.pest_count if report.pest_count is not None else sensors.pest_count
        log_activity(db, report.id, "PERCEPTION", "Sensor readings retrieved (pest trap / soil / leaf wetness)")

    # ---------- STATE / MEMORY: history + nearby ----------
    nearby = nearby_similar_count(db, report)
    log_activity(
        db, report.id, "MEMORY",
        f"Historical reports analyzed: {nearby} similar report(s) near {report.location or 'this area'} in the last 14 days",
    )

    # ---------- REASONING + DECISION ----------
    decision = run_decision_engine(
        disease=report.disease,
        is_healthy=report.is_healthy,
        confidence=report.confidence,
        severity=report.severity,
        crop=report.crop,
        temperature=report.temperature,
        humidity=report.humidity,
        rainfall=report.rainfall,
        soil_moisture=report.soil_moisture,
        leaf_wetness=report.leaf_wetness,
        pest_count=report.pest_count,
        location=report.location,
        nearby_reports=nearby,
    )
    log_activity(db, report.id, "REASONING",
                 "Risk engine evaluated disease + environmental + regional factors")
    log_activity(db, report.id, "DECISION",
                 f"Spread risk calculated: {decision.spread_risk.upper()} ({decision.spread_risk_score}/100) — {decision.decision}")

    import json

    report.risk_level = decision.spread_risk
    report.risk_score = decision.spread_risk_score
    report.risk_factors = json.dumps(decision.factors)
    report.followup_days = decision.followup_days
    report.status = "ANALYZED"

    db.add(AgentDecision(
        report_id=report.id,
        decision=decision.decision,
        reason=decision.reason,
        confidence=decision.confidence,
        spread_risk=decision.spread_risk,
        spread_risk_score=decision.spread_risk_score,
        priority=decision.priority,
        recommended_action=decision.recommended_action,
        officer_verification_needed=decision.officer_verification_needed,
        lab_referral_recommended=decision.lab_referral_recommended,
        regional_alert=decision.regional_alert,
        followup_days=decision.followup_days,
        factors=json.dumps(decision.factors),
    ))

    # ---------- ACTION: recommendations + notifications ----------
    log_activity(db, report.id, "ACTION", "Recommendations generated for farmer")
    for action in decision.actions:
        db.add(Recommendation(report_id=report.id, recommendation=action,
                              priority=decision.priority))

    notify(db, report.farmer_id, "RESULT",
           ("Healthy crop check" if report.is_healthy else "AI assessment ready"),
           (f"Your {report.crop} check is ready: "
            + ("looks healthy." if report.is_healthy
               else f"potential {report.disease}, spread risk {decision.spread_risk}.")),
           report_id=report.id)

    if decision.spread_risk == "High":
        log_activity(db, report.id, "ACTION", "Farmer notification created: high spread-risk detected")
        notify(db, report.farmer_id, "HIGH_RISK",
               "High spread-risk detected in your crop report.",
               f"Potential {report.disease} on your {report.crop} near {report.location or 'your farm'}. "
               "Please follow the recommended actions and monitor closely.")

    if decision.officer_verification_needed:
        log_activity(db, report.id, "ACTION", "Officer review recommended")
        _notify_officers_inline(db, report)

    if decision.lab_referral_recommended:
        log_activity(db, report.id, "ACTION", "Lab sample recommended")

    # ---------- LEARNING hook: queue for verification → feedback loop ----------
    log_activity(db, report.id, "LEARNING",
                 "Awaiting officer verification — confirmation/correction will enter the model feedback queue")

    return report


def _notify_officers_inline(db: Session, report: CropReport) -> None:
    """Notify officers within the caller's transaction (used by the request pipeline)."""
    from app.models.user import User
    from app.models.notification import Notification

    officers = (db.query(User)
                  .filter(User.role == "OFFICER", User.is_active.is_(True))
                  .all())
    for officer in officers:
        db.add(Notification(
            user_id=officer.id,
            report_id=report.id,
            type="VERIFICATION",
            title="New crop report requires verification",
            message=(f"Potential {report.disease} on {report.crop} near "
                     f"{report.location or 'unknown location'} — AI confidence "
                     f"{report.confidence:.0f}%, spread risk {report.risk_level}."),
        ))
