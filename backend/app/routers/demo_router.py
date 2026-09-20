"""Demo mode endpoints — seed clearly-labelled demo data (DEMO_MODE only)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import staff_required
from app.config import settings
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/mode")
def demo_mode():
    return {
        "demo_mode": settings.DEMO_MODE,
        "ai_mode": settings.AI_MODE,
        "weather_mode": settings.WEATHER_MODE,
        "seed_tag": settings.DEMO_SEED_TAG,
    }


@router.post("/seed")
def run_seed(current: User = Depends(staff_required), db: Session = Depends(get_db)):
    """Seed demo users/farms/reports (officer/admin only, DEMO_MODE only)."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="DEMO_MODE is disabled on this server.")
    from database.seed import seed_all

    created = seed_all(db)
    return {"detail": "Demo data seeded.", **created}
