"""Agent Decision Engine — the REASONING + DECISION stage of the Agricure agent.

Deterministic, explainable rule engine. It consumes:
  * the disease prediction (from the AI inference layer)
  * environmental inputs (weather + sensors)
  * historical/nearby report context (state/memory)

and produces: spread risk, priority, recommended action, whether officer
verification is needed, whether a lab referral is recommended, whether a
regional alert is appropriate, and a follow-up interval.
"""
from dataclasses import dataclass, field

from app.agents.risk_engine import compute_risk


@dataclass
class AgentDecisionResult:
    decision: str
    reason: str
    confidence: float
    spread_risk: str
    spread_risk_score: int
    priority: str
    recommended_action: str
    actions: list = field(default_factory=list)
    officer_verification_needed: bool = False
    lab_referral_recommended: bool = False
    regional_alert: bool = False
    followup_days: int = 7
    factors: list = field(default_factory=list)


def run_decision_engine(
    *,
    disease: str | None,
    is_healthy: bool,
    confidence: float,
    severity: str,
    crop: str,
    temperature: float | None,
    humidity: float | None,
    rainfall: float | None,
    soil_moisture: float | None,
    leaf_wetness: float | None,
    pest_count: int | None,
    location: str | None,
    nearby_reports: int,
) -> AgentDecisionResult:
    """Produce the full explainable decision for one analysed report."""
    risk = compute_risk(
        disease=disease, confidence=confidence, severity=severity,
        humidity=humidity, temperature=temperature, rainfall=rainfall,
        soil_moisture=soil_moisture, leaf_wetness=leaf_wetness,
        pest_count=pest_count, nearby_reports=nearby_reports,
    )

    factors = [label for label, _ in risk.factors]

    # ---------- Healthy crop ----------
    if is_healthy or not disease:
        action = ("Continue routine monitoring. Recheck this plot in 7 days and keep "
                  "recording pest-trap counts.")
        return AgentDecisionResult(
            decision="LOW SPREAD RISK — MONITOR",
            reason=("No disease detected by the AI assessment"
                    + (f" (confidence {confidence:.0f}%)" if confidence else "")
                    + ". No environmental red flags require immediate action."),
            confidence=confidence,
            spread_risk="Low",
            spread_risk_score=risk.risk_score,
            priority="LOW",
            recommended_action=action,
            actions=["Continue routine monitoring", "Recheck this plot in 7 days"],
            officer_verification_needed=False,
            lab_referral_recommended=False,
            regional_alert=False,
            followup_days=7,
            factors=factors,
        )

    # ---------- Disease detected ----------
    followup_days = 2 if severity == "High" else 4 if severity == "Moderate" else 7
    verification_needed = confidence < 78 or severity == "High" or risk.risk == "High"
    lab_referral = severity == "High" and (pest_count is not None and pest_count >= 15
                                           or leaf_wetness is not None and leaf_wetness >= 8)
    regional_alert = (risk.risk == "High" and nearby_reports >= 3) or (
        risk.risk == "High" and severity == "High")

    if risk.risk == "High":
        decision = "HIGH SPREAD RISK"
        priority = "CRITICAL" if severity == "High" else "HIGH"
        reason = (
            f"{disease} detected with {confidence:.0f}% AI confidence under conditions "
            f"favourable for spread"
            + (f" — humidity {humidity:.0f}%" if humidity is not None else "")
            + (f", recent rainfall {rainfall:.0f} mm" if rainfall is not None else "")
            + (f", leaf wetness {leaf_wetness:.0f} h" if leaf_wetness is not None else "")
            + (f", {nearby_reports} nearby similar reports" if nearby_reports else "")
            + ". Risk increased because multiple environmental and regional factors "
              "are favorable for disease spread."
        )
        action = "Isolate and remove severely affected plants; improve drainage and sanitation."
        actions = [
            "Isolate and remove severely affected plants immediately",
            "Improve field drainage and sanitation",
            "Request an on-site visit from an agriculture officer",
            "Avoid working in the field while leaves are wet",
        ]
    elif risk.risk == "Moderate":
        decision = "MODERATE SPREAD RISK — MONITOR CLOSELY"
        priority = "MEDIUM"
        reason = (
            f"{disease} detected with {confidence:.0f}% AI confidence. Some environmental "
            "factors are favourable for spread but conditions are not yet critical."
        )
        action = "Remove the worst-affected leaves and improve airflow; monitor every 2-3 days."
        actions = [
            "Remove and destroy the worst-affected leaves",
            "Improve airflow between rows",
            "Check neighbouring plants for the same signs",
            "Contact your local Krishi Vigyan Kendra if it spreads",
        ]
    else:
        decision = "LOW SPREAD RISK — MONITOR"
        priority = "LOW"
        reason = (
            f"{disease} detected with {confidence:.0f}% AI confidence, but current "
            "environmental conditions are not favourable for spread."
        )
        action = "Monitor the affected plants every 2-3 days and remove visibly damaged leaves."
        actions = [
            "Monitor the affected plants every 2-3 days",
            "Remove any visibly damaged leaves",
            "Continue normal watering and spacing",
        ]

    return AgentDecisionResult(
        decision=decision,
        reason=reason,
        confidence=confidence,
        spread_risk=risk.risk,
        spread_risk_score=risk.risk_score,
        priority=priority,
        recommended_action=action,
        actions=actions,
        officer_verification_needed=verification_needed,
        lab_referral_recommended=bool(lab_referral),
        regional_alert=regional_alert,
        followup_days=followup_days,
        factors=factors,
    )
