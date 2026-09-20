"""Timestamped agent activity trace — the visible PERCEPTION→LEARNING pipeline (viva evidence)."""
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentActivity(Base):
    __tablename__ = "agent_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("crop_reports.id"), index=True)
    stage: Mapped[str] = mapped_column(String(40))   # PERCEPTION / MEMORY / REASONING / DECISION / ACTION / FEEDBACK / LEARNING
    message: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
