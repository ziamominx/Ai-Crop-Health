"""Build the fixture bundle used by the static (GitHub Pages) demo.

GitHub Pages can host the React app but cannot run Python, so the published demo
serves bundled data instead of calling the API. To keep that data honest, this
script does NOT invent anything:

1. it seeds a throwaway SQLite database with the normal demo seed (users, farms,
   reports, referrals, notifications, sensors, model version);
2. for each of the 11 demo photos it runs the **real agent pipeline** (the same
   heuristic CV inference, risk engine and decision engine the API uses) and
   captures the full result — disease, confidence, severity, risk factors,
   agent decision, recommendations and the activity trace;
3. it rewrites image paths to the static /demo-photos assets and writes
   frontend/src/demo/fixtures.json.

Run:
    backend/.venv/Scripts/python scripts/export_static_demo.py
    (then: cd frontend && npm run build:pages)
"""
import io
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
DEMO_PHOTOS = os.path.join(ROOT, "frontend", "public", "demo-photos")
OUT = os.path.join(ROOT, "frontend", "src", "demo", "fixtures.json")

# A throwaway database so the real one is never touched
TMP_DIR = tempfile.mkdtemp(prefix="agricure_fixtures_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TMP_DIR, 'fixtures.db').replace(os.sep, '/')}"
os.environ["AI_MODE"] = "HEURISTIC_CV"
os.environ["WEATHER_MODE"] = "DEMO_WEATHER"

sys.path.insert(0, BACKEND)
sys.path.insert(0, ROOT)   # for database/seed.py
os.chdir(BACKEND)          # match how the app resolves uploads/paths

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.agents.pipeline import nearby_similar_count, recent_activity, run_full_pipeline  # noqa: E402
from app.models import (AgentDecision, CropReport, Farm, ModelVersion, Notification,  # noqa: E402
                        Recommendation, Referral, SensorReading, User)
from database.seed import seed_all  # noqa: E402

CROPS = ["Tomato", "Wheat", "Cotton", "Rice", "Onion"]
LOCATIONS = ["Nashik", "Pune", "Ahmednagar", "Nagpur", "Kolhapur"]


def static_photo(crop: str, healthy: bool, variant_known: bool = True) -> str:
    """Path to the bundled demo photo for a crop."""
    stem = crop.lower()
    if healthy:
        return f"/demo-photos/{stem}-healthy.jpg"
    return f"/demo-photos/{stem}.jpg"


def iso(value):
    return value.isoformat() if value else None


def report_payload(db, report: CropReport) -> dict:
    """Same shape the API returns from GET /api/reports/{id}."""
    decision = (db.query(AgentDecision)
                  .filter(AgentDecision.report_id == report.id)
                  .order_by(AgentDecision.created_at.desc()).first())
    recs = (db.query(Recommendation)
              .filter(Recommendation.report_id == report.id).order_by(Recommendation.id).all())
    activity = recent_activity(db, report.id)
    healthy = bool(report.is_healthy)

    payload = {
        "id": report.id,
        "farmer_id": report.farmer_id,
        "farm_id": report.farm_id,
        "crop": report.crop,
        "image_url": static_photo(report.crop, healthy),
        "image_path": None,
        "disease": report.disease,
        "is_healthy": healthy,
        "confidence": round(report.confidence or 0, 1),
        "severity": report.severity,
        "risk_level": report.risk_level,
        "risk_score": report.risk_score,
        "risk_factors": json.loads(report.risk_factors) if report.risk_factors else [],
        "model_version": report.model_version,
        "is_demo_inference": bool(report.is_demo_inference),
        "temperature": report.temperature,
        "humidity": report.humidity,
        "rainfall": report.rainfall,
        "soil_moisture": report.soil_moisture,
        "leaf_wetness": report.leaf_wetness,
        "pest_count": report.pest_count,
        "location": report.location,
        "status": report.status,
        "officer_verified": bool(report.officer_verified),
        "low_confidence": bool(report.low_confidence),
        "followup_days": report.followup_days,
        "created_at": iso(report.created_at),
        "updated_at": iso(report.updated_at),
        "farmer_name": report.farmer.name if report.farmer else None,
        "farm_name": report.farm.farm_name if report.farm else None,
        "agent_decision": None,
        "recommendations": [
            {"id": r.id, "recommendation": r.recommendation, "priority": r.priority}
            for r in recs
        ],
        "activity": [
            {"id": a.id, "stage": a.stage, "message": a.message, "created_at": iso(a.created_at)}
            for a in activity
        ],
        "nearby_similar": nearby_similar_count(db, report),
    }
    if decision is not None:
        payload["agent_decision"] = {
            "id": decision.id,
            "decision": decision.decision,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "spread_risk": decision.spread_risk,
            "spread_risk_score": decision.spread_risk_score,
            "priority": decision.priority,
            "recommended_action": decision.recommended_action,
            "officer_verification_needed": decision.officer_verification_needed,
            "lab_referral_recommended": decision.lab_referral_recommended,
            "regional_alert": decision.regional_alert,
            "followup_days": decision.followup_days,
            "factors": json.loads(decision.factors) if decision.factors else [],
            "created_at": iso(decision.created_at),
        }
    return payload


def ensure_heuristic_model_version(db) -> None:
    """Register the model version that actually produced these results.

    The seed registers only the demo-simulator row, which would misreport the
    analyses in the published dataset — they come from the rule-based CV model.
    """
    if db.query(ModelVersion).filter(ModelVersion.version == "heuristic-cv-v1").first():
        return
    db.add(ModelVersion(
        version="heuristic-cv-v1",
        model_name="Agricure Heuristic CV (rule-based image analysis)",
        status="ACTIVE",
        training_samples=0,
        accuracy=None,
        notes=("Rule-based leaf analysis (healthy/green, chlorosis, necrosis, powdery "
               "residue, lesion clustering). Real image analysis, but NOT a trained "
               "neural network — no crop-disease weights ship with this prototype. "
               "Plug in a trained model with AI_MODE=REAL_MODEL."),
    ))
    db.commit()


def realign_seeded_reports(db) -> None:
    """Re-analyse the seeded reports against the real bundled demo photos.

    The seed creates crude synthetic leaf images, whose pixel statistics saturate
    the classifier (every report ~95% confidence, low risk). Re-running the same
    pipeline over the actual demo photo for each crop keeps the published dataset
    coherent: the stored thumbnail IS the image that was analysed, and the risk
    spread across reports is realistic.
    """
    from app.models import AgentActivity

    reports = db.query(CropReport).order_by(CropReport.id).all()
    for report in reports:
        path = os.path.join(
            DEMO_PHOTOS,
            f"{report.crop.lower()}{'-healthy' if report.is_healthy else ''}.jpg",
        )
        if not os.path.exists(path):
            continue
        # drop the derived rows so the re-run does not duplicate them
        db.query(Recommendation).filter(Recommendation.report_id == report.id).delete()
        db.query(AgentDecision).filter(AgentDecision.report_id == report.id).delete()
        db.query(AgentActivity).filter(AgentActivity.report_id == report.id).delete()
        db.query(Notification).filter(Notification.report_id == report.id).delete()
        report.image_path = path
        report.image_url = None
        report.disease = None
        report.is_healthy = False
        report.confidence = 0.0
        report.risk_score = 0
        report.risk_level = "Low"
        report.risk_factors = None
        report.status = "PENDING"
        report.officer_verified = False
        run_full_pipeline(db, report)
        verdict = "Healthy" if report.is_healthy else report.disease
        print(f"  #{report.id:2d} {report.crop:7s} -> {verdict} "
              f"({report.confidence:.0f}%, risk {report.risk_level} {report.risk_score})")
    db.commit()


def build_demo_photo_results(db) -> dict:
    """Run the real pipeline over every bundled demo photo."""
    farmer = db.query(User).filter(User.role == "FARMER").order_by(User.id).first()
    farm = db.query(Farm).filter(Farm.farmer_id == farmer.id).order_by(Farm.id).first()
    results = {}

    for crop in CROPS:
        for healthy in (False, True):
            path = os.path.join(DEMO_PHOTOS, f"{crop.lower()}{'-healthy' if healthy else ''}.jpg")
            if not os.path.exists(path):
                print(f"  ! missing demo photo {path}")
                continue
            report = CropReport(
                farmer_id=farmer.id, farm_id=farm.id, crop=crop,
                location=farm.location, status="PENDING",
                image_path=path, image_url=None,
            )
            db.add(report)
            db.flush()
            run_full_pipeline(db, report)   # the project's own inference, unmodified
            db.commit()
            db.refresh(report)

            payload = report_payload(db, report)
            payload["image_url"] = static_photo(crop, healthy)
            key = f"{crop}:{'healthy' if healthy else 'diseased'}"
            results[key] = payload
            verdict = "Healthy" if payload["is_healthy"] else payload["disease"]
            print(f"  {key:22s} -> {verdict} ({payload['confidence']}%, risk {payload['risk_level']})")

    # The probe reports were only used to compute results — remove them so the
    # published dataset stays the clean seeded demo.
    db.query(Recommendation).filter(
        Recommendation.report_id > 10).delete(synchronize_session=False)
    db.query(AgentDecision).filter(
        AgentDecision.report_id > 10).delete(synchronize_session=False)
    from app.models import AgentActivity

    db.query(AgentActivity).filter(AgentActivity.report_id > 10).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.report_id > 10).delete(synchronize_session=False)
    db.query(CropReport).filter(CropReport.id > 10).delete(synchronize_session=False)
    db.commit()
    return results


def main() -> None:
    print(f"Building fixtures in a throwaway database: {TMP_DIR}")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        summary = seed_all(db)
        print(f"  seeded: {summary}")

        ensure_heuristic_model_version(db)
        print("Re-analysing the seeded reports against the real demo photos:")
        realign_seeded_reports(db)

        print("Running the real agent pipeline over the demo photos:")
        demo_photos = build_demo_photo_results(db)

        users = db.query(User).order_by(User.id).all()
        farms = db.query(Farm).order_by(Farm.id).all()
        reports = (db.query(CropReport).order_by(CropReport.id).all())
        report_payloads = {r.id: report_payload(db, r) for r in reports}
        name_of = {u.id: u.name for u in users}
        referrals = db.query(Referral).order_by(Referral.id).all()
        notifications = db.query(Notification).order_by(Notification.id.desc()).limit(60).all()
        sensors = db.query(SensorReading).order_by(SensorReading.recorded_at.desc()).all()
        models = db.query(ModelVersion).order_by(ModelVersion.id).all()

        fixtures = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": ("Bundled sample data for the static GitHub Pages demo. Every analysis "
                     "below was produced by the project's own heuristic CV inference, risk "
                     "engine and decision engine — nothing is fabricated. Live photo uploads "
                     "and database writes require running the FastAPI backend."),
            "crops": CROPS,
            "locations": LOCATIONS,
            "users": [
                {
                    "id": u.id, "name": u.name, "email": u.email, "role": u.role,
                    "phone": u.phone, "language": u.language,
                    "is_active": bool(u.is_active), "created_at": iso(u.created_at),
                }
                for u in users
            ],
            "farms": [
                {
                    "id": f.id, "farmer_id": f.farmer_id, "farm_name": f.farm_name,
                    "location": f.location, "latitude": f.latitude, "longitude": f.longitude,
                    "district": f.district, "state": f.state, "created_at": iso(f.created_at),
                }
                for f in farms
            ],
            "reports": list(report_payloads.values()),
            "referrals": [
                {
                    "id": r.id, "report_id": r.report_id, "farmer_id": r.farmer_id,
                    "officer_id": r.officer_id, "reason": r.reason, "status": r.status,
                    "created_at": iso(r.created_at), "resolved_at": iso(r.resolved_at),
                    "farmer_name": name_of.get(r.farmer_id),
                    "crop": (report_payloads.get(r.report_id) or {}).get("crop"),
                    "disease": (report_payloads.get(r.report_id) or {}).get("disease"),
                }
                for r in referrals
            ],
            "notifications": [
                {
                    "id": n.id, "user_id": n.user_id, "report_id": n.report_id,
                    "type": n.type, "title": n.title, "message": n.message,
                    "is_read": bool(n.is_read), "created_at": iso(n.created_at),
                }
                for n in notifications
            ],
            "sensor_readings": [
                {
                    "id": s.id, "farm_id": s.farm_id, "trap_type": s.trap_type,
                    "temperature": s.temperature, "humidity": s.humidity,
                    "soil_moisture": s.soil_moisture, "leaf_wetness": s.leaf_wetness,
                    "pest_count": s.pest_count, "recorded_at": iso(s.recorded_at),
                }
                for s in sensors
            ],
            "model_versions": [
                {
                    "id": m.id, "version": m.version, "model_name": m.model_name,
                    "status": m.status, "training_samples": m.training_samples,
                    "accuracy": m.accuracy, "notes": m.notes, "created_at": iso(m.created_at),
                }
                for m in models
            ],
            "demo_photos": demo_photos,
        }
    finally:
        db.close()
        shutil.rmtree(TMP_DIR, ignore_errors=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(fixtures, fh, ensure_ascii=False, indent=1)
    size = os.path.getsize(OUT) // 1024
    print(f"\nWrote {OUT} ({size} KB) — {len(fixtures['reports'])} reports, "
          f"{len(fixtures['users'])} users, {len(demo_photos)} precomputed demo analyses")


if __name__ == "__main__":
    main()
