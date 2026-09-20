"""Farms owned by farmers."""
from datetime import datetime

from sqlalchemy import String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    farm_name: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(120))          # e.g. Nashik / Pune / ...
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True, default="Maharashtra")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
