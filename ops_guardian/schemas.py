"""Pydantic schemas for validating raw LLM responses.

These are the contract between the model and the adapter. The adapter validates
each model response against the relevant schema and, on failure, feeds the
validation error back to the model and retries — instead of silently accepting
malformed free-text JSON.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .models import Probability, Severity


class SceneAnalysisResponse(BaseModel):
    """Vision model output. All fields optional so partial scene reads still parse."""

    visible_entities: list[str] = Field(default_factory=list)
    movement: list[str] = Field(default_factory=list)
    posture: list[str] = Field(default_factory=list)
    hazards: list[str] = Field(default_factory=list)
    workflow_step: str | None = None
    uncertainty: str | None = None
    evidence_descriptions: list[str] = Field(default_factory=list)


class PlanRiskItem(BaseModel):
    # risk_type and severity are required — a risk without them is not actionable.
    risk_type: str
    severity: Severity
    probability: Probability = "medium"
    confidence: float = 0.7
    time_to_event_seconds: int | None = None
    recommended_actions: list[str] = Field(default_factory=list)
    applicable_policy_ids: list[str] = Field(default_factory=list)


class PlanToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    summary: str = "No summary returned by planner."
    risks: list[PlanRiskItem] = Field(default_factory=list)
    tool_calls: list[PlanToolCall] = Field(default_factory=list)
    verification_notes: list[str] = Field(default_factory=list)
    done: bool = True
