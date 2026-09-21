"""Offline unit tests for the Grok vision model's response parsing.

No network is used — only the JSON-extraction and prediction-mapping logic.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.grok_model import GrokVisionCropDiseaseModel, _extract_json  # noqa: E402

ALLOWED = ["Early Blight", "Late Blight", "Leaf Curl", "Bacterial Leaf Spot"]

checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not ok else ""))


model = GrokVisionCropDiseaseModel.__new__(GrokVisionCropDiseaseModel)
model.model = "test-model"
model.api_key = "test-key"


# ---- _extract_json ----
check("bare json", _extract_json('{"is_healthy": true}') == {"is_healthy": True})
check("fenced json", _extract_json('```json\n{"a": 1}\n```') == {"a": 1})
check("prose-wrapped json",
      _extract_json('Sure! Here it is: {"disease": "Late Blight"} hope that helps')
      == {"disease": "Late Blight"})
check("no json", _extract_json("I cannot classify that.") is None)

# ---- healthy prediction ----
p = model._prediction_from_text(
    '{"is_healthy": true, "disease": null, "confidence": 92, '
    '"severity": "Low", "reasoning": "uniform green canopy"}', "tomato", ALLOWED)
check("healthy: disease None", p.disease is None)
check("healthy: is_healthy", p.is_healthy is True)
check("healthy: not demo", p.is_demo is False)
check("healthy: version prefix", p.model_version.startswith("grok-vision"))
check("healthy: note cites grok", "Grok" in p.note)

# ---- diseased prediction ----
p = model._prediction_from_text(
    '{"is_healthy": false, "disease": "Late Blight", "confidence": 88, '
    '"severity": "High", "reasoning": "dark irregular lesions with yellow halo"}',
    "tomato", ALLOWED)
check("diseased: catalogue match", p.disease == "Late Blight")
check("diseased: confidence", p.confidence == 88.0)
check("diseased: severity", p.severity == "High")
check("diseased: not demo", p.is_demo is False)
check("diseased: alternatives offered", len(p.top_alternatives) == 2)

# ---- paraphrased disease snaps to catalogue ----
p = model._prediction_from_text(
    '{"is_healthy": false, "disease": "late blight", "confidence": 70, "severity": "moderate"}',
    "tomato", ALLOWED)
check("paraphrase snapped", p.disease == "Late Blight")

# ---- unknown disease kept but flagged ----
p = model._prediction_from_text(
    '{"is_healthy": false, "disease": "Mystery Wilt", "confidence": 55, "severity": "low"}',
    "tomato", ALLOWED)
check("unknown disease preserved", p.disease == "Mystery Wilt")

# ---- bad values clamped, not crashed ----
p = model._prediction_from_text(
    '{"is_healthy": false, "disease": "Leaf Curl", "confidence": 250, "severity": "EXTREME"}',
    "tomato", ALLOWED)
check("confidence clamped to 100", p.confidence == 100.0)
check("bad severity falls back to Moderate", p.severity == "Moderate")

failed = checks.count(False)
print(f"\n{len(checks) - failed}/{len(checks)} checks passed")
sys.exit(1 if failed else 0)
