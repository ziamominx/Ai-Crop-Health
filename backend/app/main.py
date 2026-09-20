"""Agricure FastAPI application entrypoint."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (admin_router, analytics_router, auth_router,
                         demo_router, export_router, farm_router,
                         model_router, notification_router, referral_router,
                         report_router, sensor_router, verification_router)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "AI Crop Health & Early Warning Agent — REST API.\n\n"
        "Agent loop: PERCEPTION → STATE/MEMORY → REASONING → DECISION → ACTION → FEEDBACK → LEARNING"
    ),
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve locally-stored crop images (LOCAL storage provider demo fallback).
# On read-only serverless filesystems (e.g. Vercel) the directory can't be
# created and LOCAL storage can't persist files — configure SUPABASE or
# CLOUDINARY storage there; the mount is skipped rather than crashing the app.
_UPLOADS_READY = False
try:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    _UPLOADS_READY = True
except OSError as _exc:
    print(f"[Agricure] LOCAL image storage unavailable ({_exc}); uploads need "
          "STORAGE_PROVIDER=SUPABASE or CLOUDINARY.")
if _UPLOADS_READY:
    app.mount("/api/images", StaticFiles(directory=settings.UPLOAD_DIR), name="images")

API = settings.API_V1_PREFIX
for router in (auth_router, farm_router, report_router, sensor_router,
               referral_router, notification_router, analytics_router,
               verification_router, model_router, admin_router, export_router,
               demo_router):
    app.include_router(router.router, prefix=API)


@app.on_event("startup")
def create_tables():
    """Ensure the schema exists, then seed demo data on a fresh database.

    Both steps are idempotent, so a freshly deployed backend (e.g. on Vercel with
    a hosted PostgreSQL) is immediately usable with the demo logins — no manual
    seed step required. For production migrations use Alembic.
    """
    from app.database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    if not settings.DEMO_MODE:
        return
    from app.models.user import User

    db = SessionLocal()
    try:
        has_users = db.query(User.id).first() is not None
        if has_users:
            return
        from database.seed import seed_all

        created = seed_all(db)
        print(f"[Agricure] Fresh database detected — seeded demo data: {created}")
    finally:
        db.close()


@app.get("/", tags=["health"])
def root():
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "ai_mode": settings.AI_MODE,
        "weather_mode": settings.WEATHER_MODE,
        "demo_mode": settings.DEMO_MODE,
    }


@app.get("/api/health", tags=["health"])
def health():
    from sqlalchemy import text

    from app.database import _is_fallback_db, engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_state = "sqlite-fallback (PostgreSQL unreachable)" if _is_fallback_db else "connected"
        return {"status": "ok", "database": db_state}
    except Exception as exc:
        return {"status": "degraded", "database": f"unavailable: {exc}"}
