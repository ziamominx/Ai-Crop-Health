"""Model loader — pluggable crop-disease classifier.

REAL mode expects a Keras/TensorFlow model whose output classes match
``ml.disease_catalog.DISEASE_MAP`` plus a ``Healthy`` class. The loader is lazy:
TensorFlow is imported only when a real model is actually configured, so the
demo mode runs on a minimal dependency set.
"""
import os
from typing import Optional

from app.config import settings


class ModelNotAvailable(RuntimeError):
    """Raised when REAL_MODEL mode is requested but no usable model is configured."""


def load_model():
    """Load and cache the real model. Raises ModelNotAvailable if impossible."""
    if not settings.MODEL_PATH or not os.path.exists(settings.MODEL_PATH):
        raise ModelNotAvailable(
            "REAL_MODEL is configured but MODEL_PATH does not point to a valid model file."
        )
    try:
        from tensorflow import keras  # lazy import
    except ImportError as exc:  # pragma: no cover
        raise ModelNotAvailable(
            "TensorFlow is not installed. Add tensorflow to requirements and restart."
        ) from exc
    return keras.models.load_model(settings.MODEL_PATH)


def load_labels() -> Optional[list]:
    """Load class labels (one per line) if a labels file is configured."""
    if not settings.MODEL_LABELS_PATH or not os.path.exists(settings.MODEL_LABELS_PATH):
        return None
    with open(settings.MODEL_LABELS_PATH, "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]
