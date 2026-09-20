"""Agricure backend configuration — all secrets and switches come from environment (.env).

DEMO_MODE keeps a single academic demo inside one clearly-labelled dataset.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Agricure — AI Crop Health & Early Warning Agent"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"

    # --- Database (PostgreSQL by default; SQLite fallback for zero-setup demos) ---
    DATABASE_URL: str = "postgresql+psycopg://agricure:agricure@localhost:5432/agricure"
    # Optional literal SQLite file override, e.g. "sqlite:///./agricure_dev.db"
    SQLITE_FALLBACK: bool = True

    # --- Security ---
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- AI model ---
    # HEURISTIC_CV = real analysis of the uploaded image (colour/lesion features; default)
    # DEMO_MODEL   = explicit simulated inference (clearly labelled, never shown as real AI)
    # REAL_MODEL   = pluggable trained model loaded via ml.model_loader
    AI_MODE: str = "HEURISTIC_CV"        # HEURISTIC_CV | DEMO_MODEL | REAL_MODEL
    MODEL_PATH: Optional[str] = None      # e.g. ./ml/weights/agricure_crop_disease.keras
    MODEL_LABELS_PATH: Optional[str] = None
    MODEL_VERSION: str = "demo-v0"

    # --- Weather provider ---
    WEATHER_MODE: str = "DEMO_WEATHER"    # DEMO_WEATHER | OPENWEATHER
    OPENWEATHER_API_KEY: Optional[str] = None
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # --- Image storage: LOCAL (demo fallback) | SUPABASE | CLOUDINARY ---
    STORAGE_PROVIDER: str = "LOCAL"
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 8
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    SUPABASE_BUCKET: str = "agricure-crop-images"
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None

    # --- Demo mode ---
    # When True, /api/demo/seed populates clearly-labelled demo users/reports.
    DEMO_MODE: bool = True
    DEMO_SEED_TAG: str = "DEMO"
    # Static demo credentials surfaced in the UI (only created when DEMO_MODE=True).
    DEMO_FARMER_EMAIL: str = "demo@agricure.app"
    DEMO_FARMER_PASSWORD: str = "demo1234"
    DEMO_OFFICER_EMAIL: str = "officer@agricure.gov.in"
    DEMO_OFFICER_PASSWORD: str = "officer1234"
    DEMO_ADMIN_EMAIL: str = "admin@agricure.gov.in"
    DEMO_ADMIN_PASSWORD: str = "admin1234"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def sqlalchemy_url(self) -> str:
        """DATABASE_URL as-is (PostgreSQL expected). Optionally allows literal sqlite URLs."""
        if self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL
        return self.DATABASE_URL

    @property
    def cors_origin_list(self):
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
