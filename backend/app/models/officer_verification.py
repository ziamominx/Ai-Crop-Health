"""Officer verification / diagnosis corrections."""
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OfficerVerification(Base):
    __tablename__ = "officer_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("crop_reports.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_disease: Mapped[str | None] = mapped_column(String(120), nullable=True)
    corrected_disease: Mapped[str | None] = mapped_column(String(120), nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lab_sample_requested: bool = False
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
