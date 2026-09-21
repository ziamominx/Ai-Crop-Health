"""Backend AI inference service.

Bridges the API layer to the ml/ inference package. Keeps disease
classification strictly separate from the agent decision engine.
"""
import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.services import ai_mode
from ml.inference import Prediction

_models: dict = {}


def _model_for_mode(mode: str):
    """One cached instance per mode, so a runtime switch takes effect immediately."""
    if mode not in _models:
        from ml.inference import get_model_for
        _models[mode] = get_model_for(mode)
    return _models[mode]


def reset_models() -> None:
    """Clear cached model instances (used after a runtime AI-mode switch)."""
    _models.clear()


def resolve_mode(db: Session) -> dict:
    """Active mode = admin override > env; GROK_VISION requires a key."""
    return ai_mode.effective_ai_mode(db)


def read_image_bytes(image_path: str | None) -> bytes | None:
    """Load stored image bytes from local storage (other providers fetch via URL)."""
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as fh:
        return fh.read()


def analyze_image(image_path: str | None, crop: str, fallback_seed: str = "agricure",
                  mode: str | None = None, db: Session | None = None) -> Prediction:
    """Run inference on a stored crop image.

    mode=None resolves the runtime mode (admin override > env). Raises 503 when
    the stored image is missing and no real analysis is possible.
    """
    if db is not None and mode is None:
        mode = ai_mode.effective_ai_mode(db)["mode"]
    mode = mode or settings.AI_MODE

    image_bytes = read_image_bytes(image_path)

    if image_bytes is None:
        # No stored bytes (e.g. legacy demo rows). Only the DEMO simulator can
        # produce a result without an image; real analysis needs the image.
        if mode == "DEMO_MODEL":
            model = _model_for_mode("DEMO_MODEL")
            seed = f"demo-photo:{fallback_seed}:{crop}".encode()
            return model.predict(seed, crop)
        raise HTTPException(status_code=503,
                            detail="Stored image is unavailable for analysis.")

    return _model_for_mode(mode).predict(image_bytes, crop)


def thumbnail_data_url(image_path: str | None) -> str | None:
    image_bytes = read_image_bytes(image_path)
    if image_bytes is None:
        return None
    from ml import preprocessing
    return preprocessing.make_demo_thumbnail(image_bytes)
