"""Farms + weather routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import farmer_required, get_current_user
from app.database import get_db
from app.models.crop_report import CropReport
from app.models.farm import Farm
from app.models.user import User
from app.schemas.schemas import FarmIn, FarmOut, WeatherOut
from app.services.weather import get_weather
from app.utils.audit import audit

router = APIRouter(tags=["farms"])


def _get_own_farm(db: Session, farm_id: int, user: User) -> Farm:
    farm = db.get(Farm, farm_id)
    if not farm or farm.farmer_id != user.id:
        raise HTTPException(status_code=404, detail="Farm not found.")
    return farm


@router.get("/farms", response_model=list[FarmOut])
def my_farms(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Farm).filter(Farm.farmer_id == current.id).order_by(Farm.created_at).all()


@router.post("/farms", response_model=FarmOut, status_code=201)
def create_farm(payload: FarmIn, current: User = Depends(farmer_required),
                db: Session = Depends(get_db)):
    farm = Farm(farmer_id=current.id, **payload.model_dump())
    db.add(farm)
    db.flush()
    audit(db, current.id, "FARM_CREATED", "farm", farm.id, {"location": farm.location})
    db.commit()
    db.refresh(farm)
    return farm


@router.patch("/farms/{farm_id}", response_model=FarmOut)
def update_farm(farm_id: int, payload: FarmIn,
                current: User = Depends(farmer_required), db: Session = Depends(get_db)):
    farm = _get_own_farm(db, farm_id, current)
    for key, value in payload.model_dump().items():
        setattr(farm, key, value)
    audit(db, current.id, "FARM_UPDATED", "farm", farm.id)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/farms/{farm_id}", status_code=204)
def delete_farm(farm_id: int, current: User = Depends(farmer_required),
                db: Session = Depends(get_db)):
    farm = _get_own_farm(db, farm_id, current)
    has_reports = farm.id and db.query(CropReport).filter(CropReport.farm_id == farm.id).count() > 0
    if has_reports:
        raise HTTPException(status_code=409, detail="Farm has crop reports and cannot be deleted.")
    db.delete(farm)
    audit(db, current.id, "FARM_DELETED", "farm", farm_id)
    db.commit()


@router.get("/weather", response_model=WeatherOut)
def weather(lat: float | None = None, lon: float | None = None,
            location: str | None = None, current: User = Depends(get_current_user)):
    """Current weather for a farm location (DEMO_WEATHER sample data by default)."""
    return get_weather(lat, lon, location)
