"""GrokVisionCropDiseaseModel — real AI inference via the xAI (Grok) API.

Sends the uploaded crop photo to a vision-capable Grok model and asks it to
classify the disease against the crop's catalogue. This is a genuine
third-party AI model (not simulated), used when AI_MODE=GROK_VISION and a
GROK_API_KEY is configured.

The request/response schema follows xAI's OpenAI-compatible API:
    POST {GROK_BASE_URL}/chat/completions
    Authorization: Bearer <key>
    body: { model, messages: [{role, content: [{type:text},{type:image_url}]}] }
"""

import base64
import json
import re
from typing import Optional

import httpx

from app.config import settings
from ml.disease_catalog import DISEASE_MAP
from ml.inference import Prediction

_SYSTEM_PROMPT = (
    "You are a plant-pathology assistant for an academic crop-health system. "
    "You will be shown one photo of a crop. Classify its health. "
    "Respond ONLY with a JSON object, no markdown, using exactly these keys:\n"
    '{"is_healthy": <true|false>, "disease": <string or null>, '
    '"confidence": <integer 0-100>, "severity": <"Low"|"Moderate"|"High">, '
    '"reasoning": <one short sentence citing visible symptoms>}\n'
    "Rules: if the plant looks healthy, disease must be null and is_healthy true. "
    "If diseased, choose the single best-matching disease from the allowed list "
    "given in the user message; if none match, use \"Unidentified Stress\". "
    "Confidence must reflect genuine uncertainty; never output a fixed number. "
    "Base severity on how extensive the visible symptoms are."
)

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class GrokVisionCropDiseaseModel:
    """predict(image_bytes, crop) -> Prediction, via a vision-capable Grok model."""

    VERSION_PREFIX = "grok-vision"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROK_API_KEY
        self.model = model or settings.GROK_MODEL
        if not self.api_key:
            raise RuntimeError("GROK_API_KEY is not configured")

    # ---- interface -------------------------------------------------------

    @property
    def version(self) -> str:
        return f"{self.VERSION_PREFIX}:{self.model}"

    def predict(self, image_bytes: bytes, crop: str) -> Prediction:
        allowed = DISEASE_MAP.get(crop, ["Unidentified Stress"])
        content = [
            {"type": "text", "text": (
                f"Crop: {crop}. Allowed diseases: {', '.join(allowed)}. "
                "Classify the photo now."
            )},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode()}",
            }},
        ]
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{settings.GROK_BASE_URL.rstrip('/')}/chat/completions"

        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Grok API returned {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Grok API unreachable: {exc}") from exc

        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Grok response shape: {body}") from exc

        return self._prediction_from_text(text, crop, allowed)

    # ---- response parsing (unit-testable) --------------------------------

    def _prediction_from_text(self, text: str, crop: str, allowed: list) -> Prediction:
        data = _extract_json(text)
        if data is None:
            raise RuntimeError(f"Grok returned non-JSON content: {text[:200]}")

        is_healthy = bool(data.get("is_healthy"))
        disease = data.get("disease")
        if disease in (None, "", "null"):
            disease = None
        elif isinstance(disease, str):
            # Snap to the catalogue when Grok paraphrases a known disease.
            lower = disease.strip().lower()
            disease = next(
                (d for d in allowed if d.lower() == lower),
                next((d for d in allowed if lower in d.lower() or d.lower() in lower),
                     disease.strip()),
            )

        try:
            conf = max(0.0, min(100.0, float(data.get("confidence", 70))))
        except (TypeError, ValueError):
            conf = 70.0

        severity = str(data.get("severity", "Moderate")).title()
        if severity not in ("Low", "Moderate", "High"):
            severity = "Moderate" if not is_healthy else "Low"

        reasoning = str(data.get("reasoning", ""))[:300]

        if is_healthy or disease is None:
            return Prediction(None, True, conf, "Low", self.version, False,
                              note=f"Grok vision: {reasoning}")

        return Prediction(disease, False, conf, severity, self.version, False,
                          top_alternatives=[{"disease": d} for d in allowed
                                            if d != disease][:2],
                          note=f"Grok vision: {reasoning}")


def _extract_json(text: str) -> Optional[dict]:
    """Pull the first JSON object out of a model reply (tolerates ``` fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    bare = re.search(r"\{.*\}", text, re.DOTALL)
    if bare:
        try:
            return json.loads(bare.group(0))
        except json.JSONDecodeError:
            return None
    return None
