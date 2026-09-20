"""Sensor readings — real database inputs that feed the risk engine."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import farmer_required, get_current_user
from app.database import get_db
from app.models.farm import Farm
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.schemas.schemas import SensorReadingIn, SensorReadingOut
from app.utils.audit import audit

router = APIRouter(tags=["sensors"])


@router.post("/sensors/readings", response_model=SensorReadingOut, status_code=201)
def add_reading(payload: SensorReadingIn, current: User = Depends(farmer_required),
                db: Session = Depends(get_db)):
    farm = db.get(Farm, payload.farm_id)
    if not farm or farm.farmer_id != current.id:
        raise HTTPException(status_code=404, detail="Farm not found.")
    reading = SensorReading(**payload.model_dump())
    db.add(reading)
    db.flush()
    audit(db, current.id, "SENSOR_READING_ADDED", "farm", farm.id)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/farms/{farm_id}/sensors", response_model=list[SensorReadingOut])
def farm_sensors(farm_id: int, limit: int = 50,
                 current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found.")
    if current.role == "FARMER" and farm.farmer_id != current.id:
        raise HTTPException(status_code=403, detail="Not your farm.")
    return (db.query(SensorReading)
              .filter(SensorReading.farm_id == farm_id)
              .order_by(SensorReading.recorded_at.desc())
              .limit(min(limit, 200)).all())
