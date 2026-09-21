"""Runtime AI-mode resolution + switching.

The active inference mode is `settings.AI_MODE` from the environment unless an
admin has stored an override in system_settings. GROK_VISION is only offered
when GROK_API_KEY is configured — without a key the app runs HEURISTIC_CV
(real image analysis) or DEMO_MODEL, so **the website works with or without
an API key**.
"""
from sqlalchemy.orm import Session

from app.config import settings
from app.models.system_setting import SystemSetting

AI_MODE_KEY = "AI_MODE"

VALID_MODES = ("HEURISTIC_CV", "GROK_VISION", "DEMO_MODEL", "REAL_MODEL")


def _env_mode() -> str:
    mode = settings.AI_MODE if settings.AI_MODE in VALID_MODES else "HEURISTIC_CV"
    return mode


def grok_available() -> bool:
    """Grok is usable only when a key is configured (and httpx is installed)."""
    if not settings.GROK_API_KEY:
        return False
    try:
        import httpx  # noqa: F401
        return True
    except ImportError:
        return False


def effective_ai_mode(db: Session) -> dict:
    """Resolve the active mode: DB override > environment. Never raises."""
    env_mode = _env_mode()
    row = db.get(SystemSetting, AI_MODE_KEY)
    override = row.value if row and row.value in VALID_MODES else None
    mode = override or env_mode

    # Downgrade to a key-free mode when the selected one is unusable.
    fallback_applied = None
    if mode == "GROK_VISION" and not grok_available():
        mode, fallback_applied = env_mode if env_mode != "GROK_VISION" else "HEURISTIC_CV", \
            "no GROK_API_KEY configured"
    if mode == "REAL_MODEL" and not settings.MODEL_PATH:
        mode, fallback_applied = "HEURISTIC_CV", "no MODEL_PATH configured"

    return {
        "env_mode": env_mode,
        "override": override,
        "mode": mode,                       # what will actually run
        "grok_available": grok_available(),
        "fallback_applied": fallback_applied,
    }


def set_ai_mode(db: Session, mode: str) -> dict:
    """Store/clear the admin override. Raises ValueError on invalid input."""
    if mode not in VALID_MODES:
        raise ValueError(f"AI_MODE must be one of {', '.join(VALID_MODES)}")
    if mode == "GROK_VISION" and not grok_available():
        raise ValueError("GROK_API_KEY is not configured — add the key before "
                         "switching to GROK_VISION.")

    if mode == _env_mode():
        row = db.get(SystemSetting, AI_MODE_KEY)
        if row:
            db.delete(row)
    else:
        row = db.get(SystemSetting, AI_MODE_KEY)
        if row:
            row.value = mode
        else:
            db.add(SystemSetting(key=AI_MODE_KEY, value=mode))
    db.flush()
    return effective_ai_mode(db)


def clear_cache() -> None:
    """Reset the inference singleton so the next analysis uses the new mode."""
    from app.ai import inference_service
    inference_service._model = None
