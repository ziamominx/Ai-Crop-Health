"""Officer feedback on model predictions — feeds the learning loop."""
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModelFeedback(Base):
    __tablename__ = "model_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("crop_reports.id"), index=True)
    predicted_disease: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actual_disease: Mapped[str | None] = mapped_column(String(120), nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    in_retraining_queue: Mapped[bool] = mapped_column(Boolean, default=False)
    model_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
