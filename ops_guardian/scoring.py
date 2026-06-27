"""Deterministic risk scoring.

Implements the PRD risk model:

    risk_score = severity * probability * exposure * time_urgency * confidence

All factors are normalized to 0..1 so the product is a comparable 0..1 score used
to rank the live risk board. This replaces the previous severity+confidence sort
with the full PRD formula.
"""
from __future__ import annotations

SEVERITY_WEIGHT = {"P0": 1.0, "P1": 0.75, "P2": 0.5, "P3": 0.25}
PROBABILITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


def time_urgency(time_to_event_seconds: int | None) -> float:
    """Sooner events are more urgent. Unknown timing -> moderate urgency.

    0s -> 1.0, ~10 min -> ~0.1. Clamped to [0.1, 1.0].
    """
    if time_to_event_seconds is None:
        return 0.5
    urgency = 1.0 - (max(time_to_event_seconds, 0) / 600.0)
    return max(0.1, min(1.0, urgency))


def compute_risk_score(
    severity: str,
    probability: str,
    confidence: float,
    time_to_event_seconds: int | None = None,
    exposure: float = 1.0,
) -> float:
    severity_w = SEVERITY_WEIGHT.get(severity, 0.25)
    probability_w = PROBABILITY_WEIGHT.get(probability, 0.6)
    exposure_w = max(0.1, min(1.0, exposure))
    confidence_w = max(0.0, min(1.0, confidence))
    score = severity_w * probability_w * exposure_w * time_urgency(time_to_event_seconds) * confidence_w
    return round(score, 4)
