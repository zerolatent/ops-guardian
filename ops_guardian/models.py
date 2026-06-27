from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Severity = Literal["P0", "P1", "P2", "P3"]
RunMode = Literal["demo", "hybrid", "live"]
RiskStatus = Literal["predicted", "active", "mitigated", "escalated", "unresolved", "false_alarm"]
Probability = Literal["low", "medium", "high"]
ToolStatus = Literal["planned", "allowed", "blocked", "completed", "failed"]
ActionStatus = Literal["created", "sent", "acknowledged", "completed", "failed"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10].upper()}"


class Scenario(BaseModel):
    scenario_id: str
    title: str
    description: str
    clip_path: str
    camera_ids: list[str]
    zone_id: str
    expected_event_class: str
    data_source_ids: list[str] = Field(default_factory=list)
    max_steps: int = 2


class FrameWindow(BaseModel):
    camera_id: str
    clip_path: str
    start_seconds: int
    end_seconds: int
    frames: list[str] = Field(default_factory=list)
    images_base64: list[str] = Field(default_factory=list)
    image_mime: str = "image/jpeg"
    perception: dict[str, Any] = Field(default_factory=dict)
    available: bool = False
    note: str | None = None


class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: new_id("EVID"))
    type: Literal["frame", "clip", "log_row", "sop_snippet", "map_region", "tool_output"]
    source: str
    timestamp: datetime = Field(default_factory=utc_now)
    description: str
    uri: str
    confidence: float | None = None


class SceneObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: new_id("OBS"))
    timestamp: datetime = Field(default_factory=utc_now)
    scenario_id: str
    step_index: int
    visible_entities: list[str] = Field(default_factory=list)
    movement: list[str] = Field(default_factory=list)
    posture: list[str] = Field(default_factory=list)
    hazards: list[str] = Field(default_factory=list)
    workflow_step: str | None = None
    uncertainty: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class Risk(BaseModel):
    risk_id: str = Field(default_factory=lambda: new_id("RISK"))
    risk_type: str
    severity: Severity
    zone_id: str
    camera_ids: list[str] = Field(default_factory=list)
    status: RiskStatus = "active"
    probability: Probability = "medium"
    confidence: float = 0.7
    risk_score: float | None = None
    time_to_event_seconds: int | None = None
    detected_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    evidence_ids: list[str] = Field(default_factory=list)
    applicable_policy_ids: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    verification_id: str | None = None


class ToolCall(BaseModel):
    tool_call_id: str = Field(default_factory=lambda: new_id("TOOL"))
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    policy_check: str = "pending"
    output: dict[str, Any] = Field(default_factory=dict)
    status: ToolStatus = "planned"
    timestamp: datetime = Field(default_factory=utc_now)


class Action(BaseModel):
    action_id: str = Field(default_factory=lambda: new_id("ACT"))
    action_type: Literal["warning", "notification", "task", "hold", "safe_stop_request", "emergency_call"]
    risk_id: str | None = None
    owner_role: str
    status: ActionStatus = "created"
    created_at: datetime = Field(default_factory=utc_now)
    due_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    acknowledgment: dict[str, Any] | None = None


class EmergencyIncident(BaseModel):
    incident_id: str = Field(default_factory=lambda: new_id("EMG"))
    emergency_type: Literal["medical", "fire", "security", "environmental", "operational"]
    severity: Literal["P0", "P1"]
    site_id: str
    building: str
    zone_id: str
    nearest_entry: str
    camera_ids: list[str] = Field(default_factory=list)
    observed_condition: str
    hazards_nearby: list[str] = Field(default_factory=list)
    responders_notified: list[str] = Field(default_factory=list)
    acknowledgment_status: dict[str, Any] = Field(default_factory=dict)
    escalation_payload: dict[str, Any] = Field(default_factory=dict)
    status: Literal["opened", "responders_notified", "acknowledged", "handed_off", "closed"] = "opened"


class ShiftHandover(BaseModel):
    shift_id: str
    site_id: str
    zone_id: str
    start_time: datetime
    end_time: datetime = Field(default_factory=utc_now)
    resolved_risks: list[str] = Field(default_factory=list)
    open_risks: list[str] = Field(default_factory=list)
    emergency_incidents: list[str] = Field(default_factory=list)
    quality_holds: list[str] = Field(default_factory=list)
    maintenance_watch_items: list[str] = Field(default_factory=list)
    unresolved_tasks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AgentDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: new_id("DEC"))
    summary: str
    risks: list[Risk] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    verification_notes: list[str] = Field(default_factory=list)
    done: bool = True


class StepTrace(BaseModel):
    """Per-step record of the pipeline's internals, for dashboard inspection."""

    step_index: int
    mode: RunMode = "demo"
    camera_id: str
    window: dict[str, int] = Field(default_factory=dict)
    perception: dict[str, Any] = Field(default_factory=dict)
    detections: list[dict[str, Any]] = Field(default_factory=list)
    pose: dict[str, Any] = Field(default_factory=dict)
    annotated_frame_b64: str | None = None
    vlm_input: dict[str, Any] = Field(default_factory=dict)
    vlm_observation: dict[str, Any] = Field(default_factory=dict)
    agent_summary: str = ""


class RunState(BaseModel):
    run_id: str = Field(default_factory=lambda: new_id("RUN"))
    scenario: Scenario
    status: Literal["created", "running", "completed", "failed"] = "created"
    mode: RunMode = "demo"
    shift_id: str = Field(default_factory=lambda: new_id("SHIFT"))
    step_index: int = 0
    perception_motionless_seconds: float = 0.0
    started_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    observations: list[SceneObservation] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    incidents: list[EmergencyIncident] = Field(default_factory=list)
    handover: ShiftHandover | None = None
    scorecard: dict[str, Any] = Field(default_factory=dict)
    traces: list[StepTrace] = Field(default_factory=list)


class CreateRunRequest(BaseModel):
    scenario_id: str
    mode: RunMode = "demo"


class RunSummary(BaseModel):
    run_id: str
    scenario_id: str
    title: str
    status: str
    step_index: int
    active_risks: int
    incidents: int


class ToolContext(BaseModel):
    run: RunState
    scenario: Scenario
    site_map: dict[str, Any]
    data_sources: dict[str, Any]
    settings: dict[str, Any]
