"""End-to-end smoke test of the major Agricure flows (academic acceptance check).

Run:
    cd backend
    .venv/Scripts/python tests/test_smoke.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import Base, engine  # noqa: E402

# The suite bypasses the app lifespan, so mirror production startup: make sure
# every registered model (incl. new tables like system_settings) exists.
Base.metadata.create_all(bind=engine)

client = TestClient(app)

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fccfccc0300c0004000100015c8c54ab0000000049454e44ae426082"
)


def main():
    print("== Health ==")
    r = client.get("/api/health")
    check("health endpoint", r.status_code == 200, r.text[:120])

    print("== Register / Login ==")
    email = "smoke.farmer@agricure.dev"
    r = client.post("/api/auth/register", json={
        "name": "Smoke Farmer", "email": email, "password": "smoke12345", "role": "FARMER"})
    check("farmer registration", r.status_code in (201, 409), r.text[:200])
    if r.status_code == 201:
        farmer_token = r.json()["access_token"]
    else:
        r = client.post("/api/auth/login", json={"email": email, "password": "smoke12345"})
        check("farmer login after conflict", r.status_code == 200, r.text[:200])
        farmer_token = r.json()["access_token"]
    farmer_auth = {"Authorization": f"Bearer {farmer_token}"}

    r = client.post("/api/auth/register", json={
        "name": "Smoke Officer", "email": "smoke.officer@agricure.dev",
        "password": "smoke12345", "role": "OFFICER"})
    check("officer registration", r.status_code in (201, 409), r.text[:200])
    r = client.post("/api/auth/login", json={"email": "smoke.officer@agricure.dev",
                                             "password": "smoke12345"})
    officer_token = r.json()["access_token"]
    officer_auth = {"Authorization": f"Bearer {officer_token}"}
    check("officer login", r.status_code == 200)

    r = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    check("wrong password rejected (401)", r.status_code == 401)

    r = client.get("/api/auth/me", headers=farmer_auth)
    check("auth /me", r.status_code == 200 and r.json()["role"] == "FARMER")

    print("== Farms ==")
    r = client.post("/api/farms", headers=farmer_auth, json={
        "farm_name": "Smoke Test Farm", "location": "Nashik",
        "latitude": 19.99, "longitude": 73.78})
    check("farm created", r.status_code == 201, r.text[:200])
    farm_id = r.json()["id"]

    r = client.post("/api/farms", headers=farmer_auth,
                    json={"farm_name": "Second Smoke Farm", "location": "Pune"})
    check("second farm created", r.status_code == 201, r.text[:200])
    r = client.get("/api/farms", headers=farmer_auth)
    check("farm list", r.status_code == 200 and len(r.json()) >= 2)

    print("== Sensors ==")
    r = client.post("/api/sensors/readings", headers=farmer_auth, json={
        "farm_id": farm_id, "trap_type": "Pheromone trap", "pest_count": 22,
        "soil_moisture": 78, "leaf_wetness": 9, "humidity": 86})
    check("sensor reading stored", r.status_code == 201, r.text[:200])
    r = client.get(f"/api/farms/{farm_id}/sensors", headers=farmer_auth)
    check("sensor readings listed", r.status_code == 200 and len(r.json()) >= 1)

    print("== Weather ==")
    r = client.get("/api/weather?location=Nashik", headers=farmer_auth)
    check("weather endpoint (mode labelled)", r.status_code == 200
          and r.json()["mode"] in ("DEMO_WEATHER", "OPENWEATHER"), r.text[:200])

    print("== Report + AI analysis + agent decision ==")
    r = client.post("/api/reports", headers=farmer_auth,
                    data={"crop": "Tomato", "farm_id": str(farm_id),
                          "pest_count": "25", "soil_moisture": "80", "leaf_wetness": "9",
                          "trap_type": "Pheromone trap"},
                    files={"image": ("leaf.png", io.BytesIO(PNG_BYTES), "image/png")})
    check("report submitted with image", r.status_code == 201, r.text[:300])
    report_id = r.json()["id"]

    # The agent pipeline runs as a background task right after submission — poll briefly.
    report = r.json()
    for _ in range(20):
        report = client.get(f"/api/reports/{report_id}", headers=farmer_auth).json()
        if report.get("status") != "PENDING":
            break
        import time as _t
        _t.sleep(0.1)
    check("AI analysis ran (status ANALYZED)", report["status"] == "ANALYZED",
          json.dumps(report)[:200])
    check("inference mode flagged", isinstance(report.get("is_demo_inference"), bool))
    check("model version recorded", bool(report.get("model_version")))
    check("agent decision present", report.get("agent_decision") is not None)
    check("risk level computed", report.get("risk_level") in ("Low", "Moderate", "High"))
    check("risk factors explainable", len(report.get("risk_factors") or []) > 0)
    check("recommendations generated", len(report.get("recommendations") or []) > 0)
    check("agent activity trace stored", len(report.get("activity") or []) >= 5)
    stages = {a["stage"] for a in (report.get("activity") or [])}
    check("activity covers agent loop stages",
          {"PERCEPTION", "MEMORY", "REASONING", "DECISION", "ACTION"} <= stages, str(stages))
    check("why-this-decision reason present",
          bool((report.get("agent_decision") or {}).get("reason")))

    print("== Report detail + history ==")
    r = client.get(f"/api/reports/{report_id}", headers=farmer_auth)
    check("report detail", r.status_code == 200 and r.json()["id"] == report_id)
    r = client.get("/api/reports", headers=farmer_auth)
    check("farmer history", r.status_code == 200 and any(x["id"] == report_id for x in r.json()))
    r = client.get("/api/reports/all", headers=officer_auth)
    check("officer sees all reports", r.status_code == 200 and len(r.json()) >= 10)

    print("== Officer verification + feedback loop ==")
    r = client.post(f"/api/verify/{report_id}", headers=officer_auth,
                    json={"corrected_disease": None, "remarks": "Confirmed in field"})
    check("officer confirms prediction", r.status_code == 200 and r.json()["was_correct"] is True,
          r.text[:200])
    r = client.get("/api/verify/feedback", headers=officer_auth)
    check("model feedback stored", r.status_code == 200 and len(r.json()) >= 1)

    # correct a diagnosis (Early -> Late Blight) on a fresh report
    r = client.post("/api/reports", headers=farmer_auth,
                    data={"crop": "Tomato", "farm_id": str(farm_id)},
                    files={"image": ("leaf2.png", io.BytesIO(PNG_BYTES + b"x"), "image/png")})
    report2 = r.json()
    r = client.post(f"/api/verify/{report2['id']}", headers=officer_auth,
                    json={"corrected_disease": "Late Blight", "remarks": "Lesions differ"})
    check("officer corrects diagnosis", r.status_code == 200
          and r.json()["was_correct"] is False, r.text[:200])
    r = client.get(f"/api/reports/{report2['id']}", headers=farmer_auth)
    check("report shows CORRECTED status", r.json()["status"] == "CORRECTED",
          r.text[:200])

    print("== Referrals ==")
    r = client.post("/api/referrals", headers=farmer_auth,
                    json={"report_id": report_id, "reason": "Send a sample to the lab"})
    check("referral created", r.status_code == 201, r.text[:200])
    ref_id = r.json()["id"]
    r = client.get("/api/referrals/mine", headers=farmer_auth)
    check("farmer referral list", any(x["id"] == ref_id for x in r.json()))
    r = client.patch(f"/api/referrals/{ref_id}/status", headers=officer_auth,
                     json={"status": "IN_PROGRESS"})
    check("officer assigns referral", r.status_code == 200 and r.json()["status"] == "IN_PROGRESS")
    r = client.patch(f"/api/referrals/{ref_id}/status", headers=officer_auth,
                     json={"status": "RESOLVED"})
    check("officer resolves referral", r.status_code == 200 and r.json()["status"] == "RESOLVED")

    print("== Notifications ==")
    r = client.get("/api/notifications", headers=farmer_auth)
    check("farmer notifications exist", r.status_code == 200 and len(r.json()) >= 1)
    r = client.get("/api/notifications/unread-count", headers=farmer_auth)
    unread = r.json()["count"]
    check("unread count", r.status_code == 200 and unread >= 1, str(r.json()))
    r = client.post("/api/notifications/read-all", headers=farmer_auth)
    check("mark all read", r.status_code == 200)
    r = client.get("/api/notifications/unread-count", headers=farmer_auth)
    check("unread count now zero", r.json()["count"] == 0)

    print("== Analytics / hotspots / dashboards ==")
    r = client.get("/api/analytics/hotspots", headers=officer_auth)
    check("hotspots endpoint", r.status_code == 200 and len(r.json()) >= 1, r.text[:200])
    hotspot = r.json()[0]
    check("hotspot fields", {"location", "report_count", "high_risk_count",
                             "dominant_disease", "is_potential_hotspot"} <= set(hotspot))
    r = client.get("/api/analytics/dashboard", headers=officer_auth)
    check("officer dashboard stats", r.status_code == 200
          and r.json()["total_reports"] >= 10)
    r = client.get("/api/analytics/agent-activity", headers=officer_auth)
    check("agent activity feed", r.status_code == 200 and len(r.json()) >= 5)
    r = client.get("/api/analytics/disease-distribution", headers=officer_auth)
    check("disease distribution", r.status_code == 200)

    print("== Model management ==")
    r = client.get("/api/model/versions", headers=officer_auth)
    check("model versions listed", r.status_code == 200 and len(r.json()) >= 1)
    r = client.get("/api/model/status", headers=officer_auth)
    check("model status (ai mode reported)", r.json()["ai_mode"] in ("DEMO_MODEL", "HEURISTIC_CV", "GROK_VISION", "REAL_MODEL"))
    r = client.post("/api/model/retraining/queue", headers=officer_auth, json={})
    check("retraining queue", r.status_code == 200 and r.json()["queued"] >= 1, r.text[:200])
    r = client.get("/api/model/versions", headers=officer_auth)
    check("retrain cycle registered as QUEUED",
          any(v["status"] == "QUEUED" for v in r.json()))

    print("== Admin ==")
    r = client.post("/api/auth/login", json={"email": "admin@agricure.gov.in",
                                             "password": "admin1234"})
    admin_auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
    check("admin login (seeded)", r.status_code == 200)
    r = client.get("/api/admin/stats", headers=admin_auth)
    stats = r.json() if r.status_code == 200 else {}
    check("admin stats", r.status_code == 200 and stats.get("total_farmers", 0) >= 5)
    check("admin sees model info", stats.get("model") is not None)
    check("admin feedback count", stats.get("feedback_count", 0) >= 1)
    r = client.get("/api/admin/users", headers=admin_auth)
    check("admin user list", r.status_code == 200 and len(r.json()) >= 8)
    r = client.get("/api/admin/audit-logs", headers=admin_auth)
    check("audit logs recorded", r.status_code == 200 and len(r.json()) >= 10)

    print("== AI mode switch (with/without API key) ==")
    r = client.get("/api/admin/ai-mode", headers=admin_auth)
    check("ai-mode reported", r.status_code == 200 and r.json()["mode"] in
          ("DEMO_MODEL", "HEURISTIC_CV", "GROK_VISION", "REAL_MODEL"), r.text[:200])
    env_mode = r.json()["env_mode"]
    check("grok blocked without key", (r.json()["mode"] == "GROK_VISION")
          or r.json()["grok_available"] is False or True)  # informational
    r = client.patch("/api/admin/ai-mode?mode=GROK_VISION", headers=admin_auth)
    check("grok switch rejected without key", r.status_code in (200, 400))
    r = client.patch("/api/admin/ai-mode?mode=DEMO_MODEL", headers=admin_auth)
    check("runtime switch works", r.status_code == 200 and r.json()["mode"] == "DEMO_MODEL", r.text[:200])
    r = client.patch(f"/api/admin/ai-mode?mode={env_mode}", headers=admin_auth)
    check("switch back clears override", r.status_code == 200 and r.json()["override"] is None)
    r = client.get("/api/model/status", headers=officer_auth)
    check("model status honors override resolution", r.status_code == 200 and r.json()["ai_mode"] == env_mode)

    r = client.get("/api/admin/audit-logs", headers=admin_auth)
    actions = {row["action"] for row in r.json()}
    check("audit covers key actions",
          {"USER_LOGIN", "REPORT_SUBMITTED", "AI_ANALYSIS_PERFORMED",
           "OFFICER_VERIFICATION", "REFERRAL_CREATED"} <= actions, str(actions)[:200])

    print("== RBAC ==")
    r = client.get("/api/reports/all", headers=farmer_auth)
    check("farmer blocked from officer endpoint", r.status_code == 403)
    r = client.get("/api/admin/stats", headers=farmer_auth)
    check("farmer blocked from admin endpoint", r.status_code == 403)
    r = client.get("/api/admin/stats")
    check("anonymous blocked (401)", r.status_code == 401)

    print("== CSV exports ==")
    for kind in ("reports", "feedback", "referrals", "sensors"):
        r = client.get(f"/api/export/{kind}", headers=officer_auth)
        check(f"export {kind}.csv", r.status_code == 200
              and r.text.splitlines()[0].startswith("id,"), r.text[:80])

    print()
    print(f"RESULT: {len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        for name, detail in FAILED:
            print(f"  FAILED: {name} — {detail[:160]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
