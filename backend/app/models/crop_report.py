"""Crop reports — the central entity of the agent workflow."""
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Text, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CropReport(Base):
    __tablename__ = "crop_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    farm_id: Mapped[int | None] = mapped_column(ForeignKey("farms.id"), nullable=True, index=True)
    crop: Mapped[str] = mapped_column(String(60), index=True)

    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    disease: Mapped[str | None] = mapped_column(String(120), nullable=True)  # None => healthy/unknown
    is_healthy: Mapped[bool] = mapped_column(default=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(
        Enum("Low", "Moderate", "High", name="severity"), default="Low"
    )
    risk_level: Mapped[str] = mapped_column(
        Enum("Low", "Moderate", "High", name="risklevel"), default="Low"
    )
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_factors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    model_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_demo_inference: Mapped[bool] = mapped_column(default=False)

    # Environmental inputs (weather + manual/sensor)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_moisture: Mapped[float | None] = mapped_column(Float, nullable=True)
    leaf_wetness: Mapped[float | None] = mapped_column(Float, nullable=True)
    pest_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    status: Mapped[str] = mapped_column(
        Enum("PENDING", "ANALYZED", "VERIFIED", "CORRECTED", "REJECTED", name="reportstatus"),
        default="PENDING",
    )
    officer_verified: Mapped[bool] = mapped_column(default=False)
    low_confidence: Mapped[bool] = mapped_column(default=False)
    followup_days: Mapped[int] = mapped_column(Integer, default=7)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    farmer = relationship("User", foreign_keys=[farmer_id], lazy="joined")
    farm = relationship("Farm", foreign_keys=[farm_id], lazy="joined")
