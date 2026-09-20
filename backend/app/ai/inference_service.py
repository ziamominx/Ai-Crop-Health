"""Backend AI inference service.

Bridges the API layer to the ml/ inference package. Keeps disease
classification strictly separate from the agent decision engine.
"""
import base64
import os

from fastapi import HTTPException

from app.config import settings
from ml.inference import Prediction, get_model
from ml import preprocessing

_model = None


def _model_instance():
    global _model
    if _model is None:
        _model = get_model()
    return _model


def read_image_bytes(image_path: str | None) -> bytes | None:
    """Load stored image bytes from local storage (other providers fetch via URL)."""
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as fh:
        return fh.read()


def analyze_image(image_path: str | None, crop: str, fallback_seed: str = "agricure") -> Prediction:
    """Run inference on a stored crop image.

    Raises 503 if the image is missing and no real model can substitute.
    """
    image_bytes = read_image_bytes(image_path)

    if image_bytes is None:
        # No stored bytes (e.g. legacy demo rows). Only the DEMO simulator can
        # produce a result without an image; real analysis needs the image.
        if settings.AI_MODE == "DEMO_MODEL":
            model = _model_instance()
            seed = f"demo-photo:{fallback_seed}:{crop}".encode()
            return model.predict(seed, crop)
        raise HTTPException(status_code=503,
                            detail="Stored image is unavailable for analysis.")

    return _model_instance().predict(image_bytes, crop)


def thumbnail_data_url(image_path: str | None) -> str | None:
    image_bytes = read_image_bytes(image_path)
    if image_bytes is None:
        return None
    return preprocessing.make_demo_thumbnail(image_bytes)
