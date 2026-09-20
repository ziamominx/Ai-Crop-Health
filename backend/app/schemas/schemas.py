"""Pydantic schemas (request/response validation)."""
from datetime import datetime
from typing import Any, Optional, List, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["FARMER", "OFFICER", "ADMIN"]


class AGBase(BaseModel):
    """Base schema allowing model_* field names (Pydantic v2 protected namespace)."""

    model_config = ConfigDict(protected_namespaces=())


# ---------------- Auth ----------------
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Role = "FARMER"
    phone: Optional[str] = Field(default=None, max_length=20)
    language: str = "en"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Role
    phone: Optional[str] = None
    language: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


# ---------------- Farms ----------------
class FarmIn(BaseModel):
    farm_name: str = Field(min_length=2, max_length=160)
    location: str = Field(min_length=2, max_length=120)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    district: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)


class FarmOut(FarmIn):
    id: int
    farmer_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- Sensors ----------------
class SensorReadingIn(BaseModel):
    farm_id: int
    trap_type: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=-20, le=60)
    humidity: Optional[float] = Field(default=None, ge=0, le=100)
    soil_moisture: Optional[float] = Field(default=None, ge=0, le=100)
    leaf_wetness: Optional[float] = Field(default=None, ge=0, le=24)
    pest_count: Optional[int] = Field(default=None, ge=0)


class SensorReadingOut(SensorReadingIn):
    id: int
    recorded_at: datetime

    class Config:
        from_attributes = True


# ---------------- Reports ----------------
class ReportCreate(BaseModel):
    farm_id: int
    crop: str = Field(min_length=2, max_length=60)
    notes: Optional[str] = None
    # optional manual/sensor overrides captured on the upload form
    pest_count: Optional[int] = Field(default=None, ge=0)
    soil_moisture: Optional[float] = Field(default=None, ge=0, le=100)
    leaf_wetness: Optional[float] = Field(default=None, ge=0, le=24)
    trap_type: Optional[str] = None


class AgentDecisionOut(AGBase):
    decision: str
    reason: str
    confidence: float
    spread_risk: str
    spread_risk_score: int
    priority: str
    recommended_action: str
    officer_verification_needed: bool
    lab_referral_recommended: bool
    regional_alert: bool
    followup_days: int
    factors: Any = []  # JSON string from ORM; list after router decode

    class Config:
        from_attributes = True


class RecommendationOut(AGBase):
    id: int
    recommendation: str
    priority: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentActivityOut(AGBase):
    id: int
    stage: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReportOut(AGBase):
    id: int
    farmer_id: int
    farm_id: Optional[int]
    crop: str
    image_url: Optional[str] = None
    disease: Optional[str] = None
    is_healthy: bool
    confidence: float
    severity: str
    risk_level: str
    risk_score: int
    risk_factors: Optional[Any] = None  # JSON string from ORM; list after router decode
    model_version: Optional[str] = None
    is_demo_inference: bool
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    soil_moisture: Optional[float] = None
    leaf_wetness: Optional[float] = None
    pest_count: Optional[int] = None
    location: Optional[str] = None
    status: str
    officer_verified: bool
    low_confidence: bool
    followup_days: int
    created_at: datetime
    updated_at: datetime
    # joined for convenience (populated by routers)
    farmer_name: Optional[str] = None
    farm_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReportDetail(ReportOut):
    agent_decision: Optional[AgentDecisionOut] = None
    recommendations: List[RecommendationOut] = []
    activity: List[AgentActivityOut] = []
    nearby_similar: int = 0


# ---------------- Verification / feedback ----------------
class VerifyIn(BaseModel):
    corrected_disease: Optional[str] = None
    remarks: Optional[str] = Field(default=None, max_length=500)
    lab_sample_requested: bool = False


class FeedbackIn(BaseModel):
    report_id: int
    predicted_disease: Optional[str] = None
    actual_disease: Optional[str] = None
    was_correct: bool


# ---------------- Referrals ----------------
class ReferralCreate(BaseModel):
    report_id: int
    reason: str = Field(min_length=3, max_length=300)


class ReferralStatusUpdate(BaseModel):
    status: Literal["ASSIGNED", "IN_PROGRESS", "RESOLVED"]
    officer_id: Optional[int] = None


class ReferralOut(AGBase):
    id: int
    report_id: int
    farmer_id: int
    officer_id: Optional[int]
    reason: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    farmer_name: Optional[str] = None
    crop: Optional[str] = None
    disease: Optional[str] = None
    location: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------- Notifications ----------------
class NotificationOut(AGBase):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    report_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- Analytics / dashboards ----------------
class HotspotOut(BaseModel):
    location: str
    report_count: int
    high_risk_count: int
    dominant_disease: Optional[str] = None
    dominant_risk: Optional[str] = None
    is_potential_hotspot: bool = False


class DashboardStats(BaseModel):
    total_reports: int = 0
    high_risk: int = 0
    moderate_risk: int = 0
    low_risk: int = 0
    pending_verification: int = 0
    open_referrals: int = 0
    recent_reports: List[ReportOut] = []


class AdminStats(BaseModel):
    total_farmers: int = 0
    total_officers: int = 0
    total_reports: int = 0
    high_risk_reports: int = 0
    pending_referrals: int = 0
    feedback_count: int = 0
    retraining_queue: int = 0
    model: Optional["ModelVersionOut"] = None


# ---------------- Model management ----------------
class ModelVersionOut(AGBase):
    id: int
    version: str
    model_name: str
    status: str
    training_samples: int
    accuracy: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RetrainQueueIn(BaseModel):
    feedback_ids: Optional[List[int]] = None  # None = all confirmed feedback


# ---------------- Weather ----------------
class WeatherOut(AGBase):
    temperature: float
    humidity: float
    rainfall_24h: float
    mode: str                    # DEMO_WEATHER | OPENWEATHER
    retrieved_at: datetime
    source: Optional[str] = None

    class Config:
        from_attributes = True


AdminStats.model_rebuild()
