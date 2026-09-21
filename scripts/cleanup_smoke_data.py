"""Remove smoke-test artifacts from the dev database (smoke.* users and their data)."""
import os
import sys

# The app resolves sqlite URLs relative to backend/ — match that regardless of cwd.
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, _BACKEND)
os.chdir(_BACKEND)

from app.database import SessionLocal  # noqa: E402
from app.models import (AgentActivity, AgentDecision, AuditLog, CropReport,
                        Farm, ModelFeedback, Notification, OfficerVerification,
                        Recommendation, Referral, SensorReading, User)  # noqa: E402

SMOKE_EMAILS = ("smoke.farmer@agricure.dev", "smoke.officer@agricure.dev")

db = SessionLocal()
smoke_users = db.query(User).filter(User.email.in_(SMOKE_EMAILS)).all()
ids = [u.id for u in smoke_users]
if not ids:
    print("No smoke users found — nothing to clean.")
    sys.exit(0)

report_ids = [r.id for r in db.query(CropReport.id).filter(CropReport.farmer_id.in_(ids))]
farm_ids = [f.id for f in db.query(Farm.id).filter(Farm.farmer_id.in_(ids))]

def wipe(model, col, values):
    if values:
        n = db.query(model).filter(col.in_(values)).delete(synchronize_session=False)
        print(f"  {model.__tablename__}: -{n}")
        return n
    return 0

print("Deleting smoke-test rows...")
wipe(AgentActivity, AgentActivity.report_id, report_ids)
wipe(AgentDecision, AgentDecision.report_id, report_ids)
wipe(Recommendation, Recommendation.report_id, report_ids)
wipe(OfficerVerification, OfficerVerification.report_id, report_ids)
db.query(ModelFeedback).filter(ModelFeedback.report_id.in_(report_ids))\
    .delete(synchronize_session=False) if report_ids else None
wipe(Notification, Notification.report_id, report_ids)
wipe(Referral, Referral.report_id, report_ids)
wipe(CropReport, CropReport.id, report_ids)
wipe(SensorReading, SensorReading.farm_id, farm_ids)
wipe(Farm, Farm.id, farm_ids)
wipe(Notification, Notification.user_id, ids)
wipe(Referral, Referral.farmer_id, ids)
db.query(AuditLog).filter((AuditLog.user_id.in_(ids))).delete(synchronize_session=False)
wipe(User, User.id, ids)
db.commit()
print(f"Done. Remaining users: {db.query(User).count()}, "
      f"reports: {db.query(CropReport).count()}")
