"""Transparent risk engine — deterministic and explainable (prototype model).

Outputs a LOW/MODERATE/HIGH spread-risk with a 0-100 score and a list of
labelled factors. This is a rule-based PROTOTYPE decision model, not a
scientifically validated epidemiological model — the API and UI label it as such.
"""
from dataclasses import dataclass, field


@dataclass
class RiskResult:
    risk: str                     # LOW / MODERATE / HIGH
    risk_score: int               # 0-100
    factors: list = field(default_factory=list)   # [(label, points), ...]


def compute_risk(
    *,
    disease: str | None,
    confidence: float,
    severity: str,
    humidity: float | None,
    temperature: float | None,
    rainfall: float | None,
    soil_moisture: float | None,
    leaf_wetness: float | None,
    pest_count: int | None,
    nearby_reports: int,
) -> RiskResult:
    score = 0
    factors: list[tuple[str, int]] = []

    # --- Disease pressure ---
    if disease:
        score += 25
        factors.append((f"Active disease: {disease}", 25))
        if severity == "High":
            score += 15
            factors.append(("High severity symptoms", 15))
        elif severity == "Moderate":
            score += 8
            factors.append(("Moderate severity symptoms", 8))
        if confidence >= 80:
            score += 10
            factors.append((f"High AI confidence ({confidence:.0f}%)", 10))
        elif confidence < 70:
            score += 5
            factors.append((f"Uncertain AI confidence ({confidence:.0f}%)", 5))
    else:
        factors.append(("No disease detected", 0))

    # --- Environmental factors (weather + sensors) ---
    if humidity is not None and humidity >= 80:
        score += 12
        factors.append((f"High humidity ({humidity:.0f}%)", 12))
    elif humidity is not None and humidity >= 65:
        score += 6
        factors.append((f"Elevated humidity ({humidity:.0f}%)", 6))

    if rainfall is not None and rainfall >= 10:
        score += 10
        factors.append((f"Recent rainfall ({rainfall:.0f} mm)", 10))
    elif rainfall is not None and rainfall >= 3:
        score += 5
        factors.append((f"Light rainfall ({rainfall:.0f} mm)", 5))

    if temperature is not None and 20 <= temperature <= 30:
        score += 6
        factors.append((f"Favourable temperature for spread ({temperature:.0f}°C)", 6))

    if soil_moisture is not None and soil_moisture >= 75:
        score += 6
        factors.append((f"Waterlogged soil moisture ({soil_moisture:.0f}%)", 6))

    if leaf_wetness is not None and leaf_wetness >= 8:
        score += 12
        factors.append((f"Extended leaf wetness ({leaf_wetness:.0f} h)", 12))
    elif leaf_wetness is not None and leaf_wetness >= 4:
        score += 6
        factors.append((f"Leaf wetness present ({leaf_wetness:.0f} h)", 6))

    if pest_count is not None and pest_count >= 20:
        score += 10
        factors.append((f"High pest pressure ({pest_count} in trap)", 10))
    elif pest_count is not None and pest_count >= 8:
        score += 5
        factors.append((f"Moderate pest pressure ({pest_count} in trap)", 5))

    # --- Regional signal ---
    if nearby_reports >= 5:
        score += 15
        factors.append((f"Nearby similar reports ({nearby_reports})", 15))
    elif nearby_reports >= 2:
        score += 8
        factors.append((f"Nearby similar reports ({nearby_reports})", 8))
    elif nearby_reports == 1:
        score += 4
        factors.append(("Nearby similar report (1)", 4))

    score = max(0, min(100, score))
    risk = "High" if score >= 60 else "Moderate" if score >= 30 else "Low"
    return RiskResult(risk=risk, risk_score=score, factors=factors)
