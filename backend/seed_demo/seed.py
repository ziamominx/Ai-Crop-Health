"""Agricure demo-data seeding.

Creates clearly-labelled DEMO users, farms, sensor readings, reports, referrals,
notifications and model versions. Run from the backend directory:

    cd backend
    .venv/Scripts/python -m seed_demo.seed

Idempotent: demo users are matched by email; existing rows are kept.
"""
import argparse
import random
import sys
from datetime import datetime, timedelta, timezone

import json  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.agents.pipeline import run_full_pipeline  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import (AgentDecision, CropReport, Farm, ModelVersion,  # noqa: E402
                        Notification, Referral, SensorReading, User)
from ml.disease_catalog import CROPS, DISEASE_MAP, TRAP_TYPES  # noqa: E402

LOCATIONS = ["Nashik", "Pune", "Ahmednagar", "Nagpur", "Kolhapur"]
LOCATION_COORDS = {
    "Nashik": (19.9975, 73.7898),
    "Pune": (18.5204, 73.8567),
    "Ahmednagar": (19.0948, 74.7480),
    "Nagpur": (21.1458, 79.0882),
    "Kolhapur": (16.7050, 74.2433),
}

FARMER_SEEDS = [
    ("Ramesh Patil", "demo@agricure.app", "demo1234"),
    ("Anita Sharma", "anita.demo@agricure.app", "demo1234"),
    ("Vijay More", "vijay.demo@agricure.app", "demo1234"),
    ("Meena Rao", "meena.demo@agricure.app", "demo1234"),
    ("Farhan Shaikh", "farhan.demo@agricure.app", "demo1234"),
]
OFFICER_SEEDS = [
    ("Dr. S. Kulkarni", "officer@agricure.gov.in", "officer1234"),
    ("Sarita Jadhav", "sarita.officer@agricure.gov.in", "officer1234"),
]
ADMIN_SEEDS = [
    ("Agricure Admin", "admin@agricure.gov.in", "admin1234"),
]

FARM_NAMES = ["Green Fields Plot", "Riverside Farm", "Hilltop Plot", "Canal Side Farm",
              "Sunrise Orchard", "Old Wadi Plot"]


def _synthetic_leaf_image(farmer_id: int, crop: str, healthy: bool, index: int) -> tuple[str, str]:
    """Generate a small synthetic leaf image matching the scenario.

    Green blotch = healthy leaf; brown/yellow lesions = diseased leaf. The bytes
    are stored through the normal LOCAL storage provider so reports carry a real
    image the admin live view can display.
    """
    import io
    import os
    import uuid

    from PIL import Image

    w = h = 240
    img = Image.new("RGB", (w, h), (70, 130, 60))
    px = img.load()
    if not healthy:
        # Scatter lesion blobs (brown + yellow) across the leaf
        n_blobs = 14 + (index % 5) * 6
        for k in range(n_blobs):
            cx, cy = (k * 37 + index * 13) % (w - 6) + 3, (k * 53 + index * 29) % (h - 6) + 3
            colour = (110, 72, 40) if k % 2 == 0 else (188, 172, 70)
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx * dx + dy * dy <= 9:
                        x, y = cx + dx, cy + dy
                        if 0 <= x < w and 0 <= y < h:
                            px[x, y] = colour
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    data = buf.getvalue()

    from app.services.storage import _save_local  # deliberate reuse of the demo path
    os.makedirs("uploads", exist_ok=True)  # storage writes relative to CWD (backend/)
    name = f"f{farmer_id}_{uuid.uuid4().hex[:12]}.jpg"
    url, path = _save_local(data, name)
    return url, path


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)


def get_or_create_user(db, name, email, password, role, language="en"):
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user, False
    user = User(name=name, email=email, password_hash=hash_password(password),
                role=role, language=language)
    db.add(user)
    db.flush()
    return user, True


def ensure_model_version(db):
    mv = db.query(ModelVersion).filter(ModelVersion.version == settings.MODEL_VERSION).first()
    if not mv:
        mv = ModelVersion(
            version=settings.MODEL_VERSION,
            model_name="Agricure Crop Disease Model (DEMO)" if settings.AI_MODE == "DEMO_MODEL"
            else "Agricure Crop Disease Model",
            status="ACTIVE" if settings.AI_MODE == "REAL_MODEL" else "DEMO",
            training_samples=0,
            accuracy=None,
            notes=("Demo/simulated inference mode — no trained model weights installed. "
                   "Real inference requires MODEL_PATH + AI_MODE=REAL_MODEL."),
        )
        db.add(mv)
        db.flush()
    return mv


def seed_all(db) -> dict:
    """Seed everything; returns a small summary dict."""
    ensure_schema()
    created = {"farmers": 0, "officers": 0, "admins": 0, "farms": 0,
               "reports": 0, "referrals": 0, "notifications": 0, "sensors": 0}

    # ----- model version -----
    ensure_model_version(db)

    # ----- users -----
    for name, email, password in FARMER_SEEDS:
        _, was_new = get_or_create_user(db, name, email, password, "FARMER")
        created["farmers"] += int(was_new)
    for name, email, password in OFFICER_SEEDS:
        _, was_new = get_or_create_user(db, name, email, password, "OFFICER")
        created["officers"] += int(was_new)
    for name, email, password in ADMIN_SEEDS:
        _, was_new = get_or_create_user(db, name, email, password, "ADMIN")
        created["admins"] += int(was_new)
    db.flush()

    demo_farmer = db.query(User).filter(User.email == "demo@agricure.app").one()
    officers = db.query(User).filter(User.role == "OFFICER").all()

    # ----- farms -----
    farms_by_farmer = {}
    for farmer in db.query(User).filter(User.role == "FARMER").all():
        existing = db.query(Farm).filter(Farm.farmer_id == farmer.id).all()
        if existing:
            farms_by_farmer[farmer.id] = existing
            continue
        farms = []
        for i in range(2):
            location = random.choice(LOCATIONS)
            lat, lon = LOCATION_COORDS[location]
            farm = Farm(farmer_id=farmer.id,
                        farm_name=f"{FARM_NAMES[(farmer.id + i) % len(FARM_NAMES)]} #{i + 1}",
                        location=location, latitude=lat + random.uniform(-0.05, 0.05),
                        longitude=lon + random.uniform(-0.05, 0.05),
                        district=location, state="Maharashtra")
            db.add(farm)
            db.flush()
            farms.append(farm)
            created["farms"] += 1
        farms_by_farmer[farmer.id] = farms

    # ----- sensor readings -----
    for farmer_id, farms in farms_by_farmer.items():
        for farm in farms:
            for _ in range(3):
                db.add(SensorReading(
                    farm_id=farm.id, trap_type=random.choice(TRAP_TYPES),
                    temperature=random.uniform(22, 34), humidity=random.uniform(50, 92),
                    soil_moisture=random.uniform(30, 85),
                    leaf_wetness=random.choice([0, 2, 4, 6, 9, 11]),
                    pest_count=random.randint(0, 30),
                    recorded_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 10)),
                ))
                created["sensors"] += 1
    db.flush()

    # ----- demo reports (synthetic leaf images + real agent pipeline) -----
    if db.query(CropReport).count() == 0:
        now = datetime.now(timezone.utc)
        scenarios = [
            # (crop, force_disease, severity_hint)
            ("Tomato", "Late Blight", "High"),
            ("Tomato", "Early Blight", "Moderate"),
            ("Wheat", "Yellow Rust", "High"),
            ("Wheat", "Powdery Mildew", "Low"),
            ("Cotton", "Bollworm Damage", "Moderate"),
            ("Rice", "Blast", "High"),
            ("Rice", "Bacterial Leaf Blight", "Low"),
            ("Onion", "Purple Blotch", "Moderate"),
            ("Tomato", None, "Low"),          # healthy
            ("Wheat", None, "Low"),           # healthy
        ]
        for i, (crop, disease, _sev) in enumerate(scenarios):
            farmer = db.query(User).filter(User.role == "FARMER").offset(i % 5).first()
            farm = farms_by_farmer[farmer.id][i % 2]
            report = CropReport(
                farmer_id=farmer.id, farm_id=farm.id, crop=crop,
                location=farm.location, status="PENDING",
                created_at=now - timedelta(days=(10 - i) * 0.6),
            )
            db.add(report)
            db.flush()

            # Generate a synthetic leaf image matching the scenario so the real
            # inference path has genuine bytes to analyse (and the admin live
            # view shows a stored sample image).
            url, path = _synthetic_leaf_image(farmer_id=farmer.id, crop=crop,
                                              healthy=(disease is None), index=i)
            report.image_url = url
            report.image_path = path

            run_full_pipeline(db, report)
            if disease is None:
                # Guarantee a clean healthy scenario regardless of inference mode
                report.disease = None
                report.is_healthy = True
                report.confidence = max(report.confidence, 90.0)
                report.severity = "Low"
                report.risk_level = "Low"
                report.risk_score = 0
                report.risk_factors = json.dumps(["No disease detected"])
                report.status = "ANALYZED"
            elif report.disease != disease and settings.AI_MODE != "REAL_MODEL":
                # Keep the classic demo scenarios recognisable in non-real modes
                report.disease = disease
                report.is_healthy = False
                report.status = "ANALYZED"
            created["reports"] += 1

        # ----- referrals -----
        analysed = (db.query(CropReport)
                      .filter(CropReport.is_healthy.is_(False))
                      .order_by(CropReport.id).limit(4).all())
        reasons = ["Confirm diagnosis in person", "Send a sample to the lab",
                   "Outbreak risk to neighbouring farms", "Unsure how to treat safely"]
        for i, report in enumerate(analysed[:3]):
            db.add(Referral(report_id=report.id, farmer_id=report.farmer_id,
                            reason=reasons[i % len(reasons)],
                            status="RESOLVED" if i == 0 else "PENDING",
                            officer_id=officers[0].id if i == 0 else None,
                            resolved_at=now - timedelta(days=1) if i == 0 else None))
            created["referrals"] += 1

        # ----- notifications -----
        for user in db.query(User).filter(User.role == "FARMER").limit(3):
            db.add(Notification(user_id=user.id, type="SYSTEM", title="Welcome to Agricure",
                                message="This is a DEMO account with clearly-labelled demo data."))
            created["notifications"] += 1
        for officer in officers:
            db.add(Notification(user_id=officer.id, type="SYSTEM", title="Officer dashboard ready",
                                message="Demo reports are available for verification."))
            created["notifications"] += 1

    db.commit()
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Agricure demo data")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = seed_all(db)
        if not args.quiet:
            print("Seed complete:", summary)
            print("Demo logins:")
            print("  Farmer  :", FARMER_SEEDS[0][1], "/", FARMER_SEEDS[0][2])
            print("  Officer :", OFFICER_SEEDS[0][1], "/", OFFICER_SEEDS[0][2])
            print("  Admin   :", ADMIN_SEEDS[0][1], "/", ADMIN_SEEDS[0][2])
    finally:
        db.close()


if __name__ == "__main__":
    main()
