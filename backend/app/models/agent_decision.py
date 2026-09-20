"""Agent decisions — one explainable decision per analysed report (viva evidence)."""
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("crop_reports.id"), index=True)

    decision: Mapped[str] = mapped_column(String(60))          # e.g. HIGH SPREAD RISK
    reason: Mapped[str] = mapped_column(Text)                  # human-readable explanation
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    spread_risk: Mapped[str] = mapped_column(String(20), default="Low")
    spread_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    officer_verification_needed: Mapped[bool] = mapped_column(default=False)
    lab_referral_recommended: Mapped[bool] = mapped_column(default=False)
    regional_alert: Mapped[bool] = mapped_column(default=False)
    followup_days: Mapped[int] = mapped_column(Integer, default=7)

    factors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list of risk contributors
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
