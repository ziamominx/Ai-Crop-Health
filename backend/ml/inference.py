"""CropDiseaseModel — the AI inference interface.

Three implementations:
  * RealCropDiseaseModel  — loads a trained Keras model via ml.model_loader.
  * HeuristicCropDiseaseModel — actual computer-vision analysis of the uploaded
    image (colour/lesion statistics), mapped to the crop's disease catalogue.
    It genuinely inspects the picture, but it is a rule-based heuristic, NOT a
    trained deep network — the UI labels it as such.
  * DemoCropDiseaseModel — deterministic, clearly-labelled simulated inference
    (fallback when no image analysis is possible).

The active implementation is chosen by settings.AI_MODE.
"""
import hashlib
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings
from ml.disease_catalog import DISEASE_MAP


@dataclass
class Prediction:
    disease: Optional[str]          # None => healthy
    is_healthy: bool
    confidence: float               # 0-100
    severity: str                   # Low / Moderate / High
    model_version: str
    is_demo: bool
    top_alternatives: list = field(default_factory=list)
    note: str = ""


class CropDiseaseModel:
    """Interface: predict(image_bytes, crop) -> Prediction."""

    def predict(self, image_bytes: bytes, crop: str) -> Prediction:
        raise NotImplementedError


class RealCropDiseaseModel(CropDiseaseModel):
    """Wraps a trained Keras model (see ml/model_loader.py)."""

    def __init__(self):
        self._model = None
        self._labels = None

    def _ensure_loaded(self):
        if self._model is None:
            from ml import model_loader

            self._model = model_loader.load_model()
            self._labels = model_loader.load_labels()

    def predict(self, image_bytes: bytes, crop: str) -> Prediction:
        self._ensure_loaded()
        import numpy as np
        from ml import preprocessing

        tensor = preprocessing.preprocess_image(image_bytes)
        preds = self._model.predict(tensor, verbose=0)[0]
        idx = int(np.argmax(preds))
        labels = self._labels or (["Healthy"] + [d for ds in DISEASE_MAP.values() for d in ds])
        label = labels[idx] if idx < len(labels) else "Unknown"
        conf = float(preds[idx]) * 100.0

        if label == "Healthy":
            return Prediction(None, True, conf, "Low", settings.MODEL_VERSION, False,
                              note="Real model inference")
        alternatives = [
            {"disease": labels[i], "confidence": round(float(preds[i]) * 100, 1)}
            for i in np.argsort(preds)[::-1][1:3] if i < len(labels)
        ]
        severity = "High" if conf >= 85 else "Moderate" if conf >= 70 else "Low"
        return Prediction(label, False, conf, severity, settings.MODEL_VERSION, False,
                          top_alternatives=alternatives, note="Real model inference")


class HeuristicCropDiseaseModel(CropDiseaseModel):
    """Real image analysis (no trained network): extracts colour/lesion features
    from the photo and maps them onto the crop's disease catalogue.

    What it genuinely measures (deterministic, explainable):
      * fraction of healthy green pixels
      * fraction of chlorotic (yellow) pixels
      * fraction of necrotic brown/dark lesion pixels
      * dark-spot clustering (blob-ish count via downsampled grid)
      * white powdery residue fraction
    """

    VERSION = "heuristic-cv-v1"

    def predict(self, image_bytes: bytes, crop: str) -> Prediction:
        import numpy as np
        from ml import preprocessing

        img = ImageArray.from_bytes(image_bytes)
        feats = img.features()

        disease_list = DISEASE_MAP.get(crop, ["Unidentified Stress"])

        # ---- decision rules over the measured features ----
        green = feats["green_frac"]
        yellow = feats["yellow_frac"]
        brown = feats["brown_frac"]
        dark = feats["dark_frac"]
        white = feats["white_frac"]
        spots = feats["dark_spots"]

        # Healthy: mostly green canopy with negligible lesions.
        # Ratios are relative to the green area so sunlit/yellowish healthy
        # fields are not misread, and a strict spot limit catches early lesions
        # scattered through dense foliage.
        gsafe = max(green, 0.01)
        ratio_yellow = yellow / gsafe
        ratio_necrotic = (brown + dark) / gsafe
        symptom = yellow + brown + dark
        is_healthy_img = (
            green >= 0.40
            and ratio_yellow <= 0.35
            and ratio_necrotic <= 0.15
            and spots <= 10   # real leaves show a few vein shadows; lesions show 15+
            and symptom <= max(0.07, 0.35 * green)
        )
        if is_healthy_img:
            conf = round(min(95, 72 + green * 30), 1)
            return Prediction(None, True, conf, "Low", self.VERSION, False,
                              note="Heuristic CV analysis of the uploaded image")

        # Pick the most plausible catalogue disease for this crop from symptoms
        def rank(disease: str) -> float:
            d = disease.lower()
            score = 0.0
            # necrotic spots -> blights/spots
            if ("blight" in d or "spot" in d or "blast" in d or "blotch" in d or "rust" in d):
                score += (brown + dark) * 2.0 + min(spots, 12) / 12 * 0.6
            # yellowing/chlorosis -> viruses, mildews, yellows
            if ("curl" in d or "mildew" in d or "yellow" in d or "virus" in d):
                score += yellow * 1.8 + white * 0.8
            # pest-driven damage -> bollworm
            if "bollworm" in d or "borer" in d:
                score += (dark + brown) * 0.9 + min(spots, 10) / 10 * 0.3
            return score

        ranked = sorted(disease_list, key=rank, reverse=True)
        top = ranked[0]
        top_score = rank(top)
        runner_score = rank(ranked[1]) if len(ranked) > 1 else 0.0

        # severity from symptom fraction + lesion clustering
        lesion = brown + dark + yellow
        severity = "High" if lesion >= 0.28 or spots >= 8 else "Moderate" if lesion >= 0.12 or spots >= 4 else "Low"

        # confidence: separation between top-2 candidates + symptom clarity
        margin = top_score - runner_score
        base = 62 + min(24, margin * 40)
        clarity = min(12, lesion * 40)
        conf = round(max(55, min(96, base + clarity)), 1)

        alternatives = [
            {"disease": d, "confidence": round(max(0, rank(d) * 100 / max(top_score, 0.01)), 1)}
            for d in ranked[1:3]
        ]
        return Prediction(top, False, conf, severity, self.VERSION, False,
                          top_alternatives=alternatives,
                          note=("Heuristic CV analysis of the uploaded image "
                                "(rule-based, not a trained neural network)"))


class ImageArray:
    """Small helper wrapping the pixel math for the heuristic model."""

    def __init__(self, rgb: "np.ndarray"):
        import numpy as np

        self.arr = rgb  # (H, W, 3) float 0..1
        self.np = np

    @classmethod
    def from_bytes(cls, image_bytes: bytes) -> "ImageArray":
        from ml import preprocessing

        tensor = preprocessing.preprocess_image(image_bytes)[0]  # (224,224,3)
        return cls(tensor)

    def _masks(self):
        np = self.np
        r, g, b = self.arr[..., 0], self.arr[..., 1], self.arr[..., 2]
        mx = self.arr.max(axis=-1)
        mn = self.arr.min(axis=-1)
        sat = mx - mn
        # approximate HSV hue for classification
        hue = np.zeros_like(r)
        denom = np.maximum(mx - mn, 1e-6)
        hue = np.where(mx == r, (60 * ((g - b) / denom) + 360) % 360, hue)
        hue = np.where(mx == g, (60 * ((b - r) / denom) + 120) % 360, hue)
        hue = np.where(mx == b, (60 * ((r - g) / denom) + 240) % 360, hue)
        return r, g, b, hue, sat

    def features(self) -> dict:
        np = self.np
        r, g, b, hue, sat = self._masks()
        total = r.size

        green = ((hue >= 70) & (hue <= 170) & (sat > 0.15) & (g > 0.18)).sum() / total
        yellow = ((hue >= 35) & (hue < 70) & (sat > 0.2)).sum() / total
        brown = ((hue >= 10) & (hue < 35) & (sat > 0.15) & (r > 0.15)).sum() / total
        dark = ((r < 0.22) & (g < 0.22) & (b < 0.22)).sum() / total
        white = ((sat < 0.12) & (r > 0.72) & (g > 0.72) & (b > 0.72)).sum() / total

        # crude dark-spot clustering: count grid cells dominated by necrotic pixels
        cell = self.arr.shape[0] // 14
        cells = 0
        if cell > 0:
            hh, ww = self.arr.shape[0] // cell, self.arr.shape[1] // cell
            dark_mask = (r < 0.3) & (g < 0.3) & (b < 0.3)
            for i in range(hh):
                for j in range(ww):
                    block = dark_mask[i * cell:(i + 1) * cell, j * cell:(j + 1) * cell]
                    if block.size and block.mean() > 0.35:
                        cells += 1
        return {
            "green_frac": round(float(green), 4),
            "yellow_frac": round(float(yellow), 4),
            "brown_frac": round(float(brown), 4),
            "dark_frac": round(float(dark), 4),
            "white_frac": round(float(white), 4),
            "dark_spots": cells,
        }


class DemoCropDiseaseModel(CropDiseaseModel):
    """Deterministic demo inference — hashed from the image bytes.

    The same image + crop always yields the same result (stable, explainable,
    testable) and the output is ALWAYS flagged is_demo=True so the UI can label
    it as simulated. This is not a real classifier and must never be presented
    as one.
    """

    VERSION = "demo-v0"

    def predict(self, image_bytes: bytes, crop: str) -> Prediction:
        digest = hashlib.sha256(image_bytes).hexdigest()
        # First 2 hex chars -> 0..255; thresholds chosen so ~15% of images look healthy.
        bucket = int(digest[:2], 16)
        disease_list = DISEASE_MAP.get(crop, ["Unidentified Stress"])
        disease = None if bucket < 38 else disease_list[bucket % len(disease_list)]

        if disease is None:
            return Prediction(None, True, 90 + bucket % 10, "Low", self.VERSION, True,
                              note="DEMO inference — simulated result, not a real model")

        # Confidence 64-97 derived deterministically from the hash
        conf = 64 + (int(digest[2:6], 16) % 34)
        severity = "Low" if conf < 75 else "Moderate" if conf < 88 else "High"
        return Prediction(disease, False, conf, severity, self.VERSION, True,
                          note="DEMO inference — simulated result, not a real model")


def get_model() -> CropDiseaseModel:
    """Factory honoring settings.AI_MODE. Falls back gracefully with a loud note."""
    if settings.AI_MODE == "REAL_MODEL":
        try:
            model = RealCropDiseaseModel()
            model._ensure_loaded()
            return model
        except Exception as exc:  # ModelNotAvailable, ImportError, load errors
            print(f"[Agricure] WARNING: REAL_MODEL unavailable ({exc}); "
                  "falling back to HEURISTIC_CV image analysis.")
            return HeuristicCropDiseaseModel()
    if settings.AI_MODE == "GROK_VISION":
        try:
            from ml.grok_model import GrokVisionCropDiseaseModel

            return GrokVisionCropDiseaseModel()
        except Exception as exc:  # missing key, import error
            print(f"[Agricure] WARNING: GROK_VISION unavailable ({exc}); "
                  "falling back to HEURISTIC_CV image analysis.")
            return HeuristicCropDiseaseModel()
    if settings.AI_MODE == "DEMO_MODEL":
        print("[Agricure] NOTE: AI_MODE=DEMO_MODEL simulates results without reading "
              "the image. Recommend AI_MODE=HEURISTIC_CV for real image analysis.")
        return DemoCropDiseaseModel()
    return HeuristicCropDiseaseModel()  # default: real image analysis
