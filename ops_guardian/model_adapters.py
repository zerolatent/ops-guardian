from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from .config import Settings
from .models import AgentDecision, Evidence, FrameWindow, Risk, SceneObservation, ToolCall
from .schemas import PlanResponse, SceneAnalysisResponse


class ModelAdapterError(RuntimeError):
    pass


class ModelAdapter(ABC):
    @abstractmethod
    async def analyze_scene(self, frame_window: FrameWindow, context: dict[str, Any]) -> SceneObservation:
        raise NotImplementedError

    @abstractmethod
    async def plan_next_action(
        self,
        observation: SceneObservation,
        active_risks: list[Risk],
        available_tools: list[str],
        context: dict[str, Any],
        tool_results: list[dict] | None = None,
    ) -> AgentDecision:
        raise NotImplementedError


class OpenAICompatibleAdapter(ModelAdapter):
    def __init__(self, settings: Settings):
        self.settings = settings

    def _require_config(self) -> None:
        missing = []
        if not self.settings.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.settings.vision_model:
            missing.append("VISION_MODEL")
        if not self.settings.planner_model:
            missing.append("PLANNER_MODEL")
        if missing:
            joined = ", ".join(missing)
            raise ModelAdapterError(f"Missing required live model configuration: {joined}")

    async def analyze_scene(self, frame_window: FrameWindow, context: dict[str, Any]) -> SceneObservation:
        self._require_config()
        prompt = {
            "task": "Analyze this industrial operations video window for current scene state.",
            "scenario": context.get("scenario"),
            "frame_window": frame_window.model_dump(mode="json", exclude={"images_base64"}),
            "frames_attached": len(frame_window.images_base64),
            "site_map": context.get("site_map"),
            "relevant_context": context.get("relevant_context"),
            "output_schema": {
                "visible_entities": ["string"],
                "movement": ["string"],
                "posture": ["string"],
                "hazards": ["string"],
                "workflow_step": "string or null",
                "uncertainty": "string or null",
                "evidence_descriptions": ["string"]
            },
        }
        data = await self._request_json(
            self.settings.vision_model or "",
            prompt,
            images=frame_window.images_base64,
            image_mime=frame_window.image_mime,
            schema=SceneAnalysisResponse,
        )
        evidence = [
            Evidence(
                type="frame",
                source=frame_window.camera_id,
                description=description,
                uri=frame_window.frames[min(index, len(frame_window.frames) - 1)] if frame_window.frames else frame_window.clip_path,
                confidence=None,
            )
            for index, description in enumerate(data.get("evidence_descriptions", []) or [])
        ]
        return SceneObservation(
            scenario_id=str(context["scenario"]["scenario_id"]),
            step_index=int(context["step_index"]),
            visible_entities=list(data.get("visible_entities", [])),
            movement=list(data.get("movement", [])),
            posture=list(data.get("posture", [])),
            hazards=list(data.get("hazards", [])),
            workflow_step=data.get("workflow_step"),
            uncertainty=data.get("uncertainty"),
            evidence=evidence,
        )

    async def plan_next_action(
        self,
        observation: SceneObservation,
        active_risks: list[Risk],
        available_tools: list[str],
        context: dict[str, Any],
        tool_results: list[dict] | None = None,
    ) -> AgentDecision:
        self._require_config()
        prompt = {
            "task": "Act as Line Guardian. Choose approved tools to prevent or escalate risks.",
            "observation": observation.model_dump(mode="json"),
            "active_risks": [risk.model_dump(mode="json") for risk in active_risks],
            "available_tools": available_tools,
            "tool_results": tool_results or [],
            "scenario": context.get("scenario"),
            "relevant_context": context.get("relevant_context"),
            "authority_matrix": context.get("authority_matrix"),
            "output_schema": {
                "summary": "string",
                "risks": [
                    {
                        "risk_type": "string",
                        "severity": "P0|P1|P2|P3",
                        "probability": "low|medium|high",
                        "confidence": "number 0-1",
                        "time_to_event_seconds": "integer or null",
                        "recommended_actions": ["string"],
                        "applicable_policy_ids": ["string"]
                    }
                ],
                "tool_calls": [
                    {"tool_name": "string", "arguments": {"key": "value"}}
                ],
                "verification_notes": ["string"],
                "done": "boolean (true when no further tool calls are needed)"
            },
        }
        data = await self._request_json(self.settings.planner_model or "", prompt, schema=PlanResponse)
        scenario = context["scenario"]
        observation_evidence_ids = [item.evidence_id for item in observation.evidence]
        risks = [
            Risk(
                risk_type=item["risk_type"],
                severity=item["severity"],
                zone_id=scenario["zone_id"],
                camera_ids=scenario.get("camera_ids", []),
                probability=item.get("probability", "medium"),
                confidence=float(item.get("confidence", 0.7)),
                time_to_event_seconds=item.get("time_to_event_seconds"),
                evidence_ids=observation_evidence_ids,
                applicable_policy_ids=item.get("applicable_policy_ids", []),
                recommended_actions=item.get("recommended_actions", []),
            )
            for item in data.get("risks", [])
        ]
        tool_calls = [
            ToolCall(tool_name=item["tool_name"], arguments=item.get("arguments", {}))
            for item in data.get("tool_calls", [])
        ]
        return AgentDecision(
            summary=data.get("summary", "No summary returned by planner."),
            risks=risks,
            tool_calls=tool_calls,
            verification_notes=data.get("verification_notes", []),
            done=bool(data.get("done", True)),
        )

    async def _chat_completions_request(
        self,
        model: str,
        prompt: dict[str, Any],
        images: list[str] | None = None,
        image_mime: str = "image/jpeg",
    ) -> dict[str, Any]:
        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"}
        text = (
            "Return only valid JSON matching the requested schema. "
            f"Request:\n{json.dumps(prompt)}"
        )
        if images:
            content: Any = [{"type": "text", "text": text}]
            for image in images:
                content.append(
                    {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image}"}}
                )
        else:
            content = text
        body = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": self.settings.chat_max_tokens,
        }
        if self.settings.chat_think is not None:
            body["think"] = self.settings.chat_think
        last_error: Exception | None = None
        for _attempt in range(self.settings.max_model_retries + 1):
            try:
                return await self._post_chat_completions(url, headers, body)
            except Exception as exc:  # pragma: no cover - live network path
                last_error = exc
        raise ModelAdapterError(f"Live model request failed: {last_error}")

    async def _post_chat_completions(self, url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()

    async def _request_json(
        self,
        model: str,
        prompt: dict[str, Any],
        images: list[str] | None = None,
        image_mime: str = "image/jpeg",
        schema: type[BaseModel] | None = None,
    ) -> dict[str, Any]:
        """Request JSON and, when a schema is given, validate it.

        On a parse or schema-validation failure the error is appended to the prompt
        and the model is asked again, up to max_model_retries times.
        """
        last_error: Exception | None = None
        attempt_prompt = prompt
        for _attempt in range(self.settings.max_model_retries + 1):
            payload = await self._chat_completions_request(model, attempt_prompt, images=images, image_mime=image_mime)
            try:
                data = self._extract_json(payload)
            except ModelAdapterError as exc:
                last_error = exc
                attempt_prompt = {**prompt, "previous_error": "Your last response was not valid JSON. Return ONLY a JSON object matching output_schema."}
                continue
            if schema is None:
                return data
            try:
                return schema.model_validate(data).model_dump(mode="python")
            except ValidationError as exc:
                last_error = exc
                detail = str(exc.errors())[:400]
                attempt_prompt = {**prompt, "previous_error": f"Your last JSON failed schema validation: {detail}. Fix it and return ONLY valid JSON matching output_schema."}
        raise ModelAdapterError(f"Model response did not satisfy schema after retries: {last_error}")

    def _extract_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidates: list[str] = []
        if isinstance(payload.get("output_text"), str):
            candidates.append(payload["output_text"])
        for item in payload.get("output", []) or []:
            for content in item.get("content", []) or []:
                text = content.get("text")
                if isinstance(text, str):
                    candidates.append(text)
        for choice in payload.get("choices", []) or []:
            message = choice.get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                candidates.append(content)
            elif isinstance(content, list):
                for item in content:
                    text = item.get("text") if isinstance(item, dict) else None
                    if isinstance(text, str):
                        candidates.append(text)
        for text in candidates:
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:].strip()
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
        raise ModelAdapterError("Model response did not contain valid JSON.")


class MockScenarioAdapter(ModelAdapter):
    async def analyze_scene(self, frame_window: FrameWindow, context: dict[str, Any]) -> SceneObservation:
        scenario_id = context["scenario"]["scenario_id"]
        step_index = int(context["step_index"])
        facts = _scenario_facts(scenario_id, step_index)
        evidence = [
            Evidence(
                type="frame",
                source=frame_window.camera_id,
                description=description,
                uri=frame_window.frames[0] if frame_window.frames else frame_window.clip_path,
                confidence=0.85,
            )
            for description in facts["evidence"]
        ]
        return SceneObservation(
            scenario_id=scenario_id,
            step_index=step_index,
            visible_entities=facts["visible_entities"],
            movement=facts["movement"],
            posture=facts["posture"],
            hazards=facts["hazards"],
            workflow_step=facts["workflow_step"],
            uncertainty=facts.get("uncertainty"),
            evidence=evidence,
        )

    async def plan_next_action(
        self,
        observation: SceneObservation,
        active_risks: list[Risk],
        available_tools: list[str],
        context: dict[str, Any],
        tool_results: list[dict] | None = None,
    ) -> AgentDecision:
        scenario = context["scenario"]
        scenario_id = scenario["scenario_id"]
        step_index = int(context["step_index"])
        evidence_ids = [evidence.evidence_id for evidence in observation.evidence]
        risk = _mock_risk(scenario, scenario_id, step_index, evidence_ids)
        tool_calls = [ToolCall(tool_name=name, arguments=args) for name, args in _mock_tools(scenario_id, step_index)]
        return AgentDecision(
            summary=_mock_summary(scenario_id, step_index),
            risks=[risk] if risk else [],
            tool_calls=tool_calls,
            verification_notes=["Schedule recheck and preserve before/after evidence."],
        )


def build_model_adapter(settings: Settings) -> ModelAdapter:
    if settings.model_provider == "mock":
        return MockScenarioAdapter()
    return OpenAICompatibleAdapter(settings)


def _scenario_facts(scenario_id: str, step_index: int) -> dict[str, Any]:
    resolved_step = step_index > 0
    mapping: dict[str, dict[str, Any]] = {
        "safety_forklift_near_miss": {
            "visible_entities": ["loaded forklift", "pedestrian", "staged pallet"],
            "movement": ["forklift approaching blind turn", "pedestrian approaching crossing"] if not resolved_step else ["forklift slowed", "pedestrian stopped"],
            "posture": [],
            "hazards": ["blocked sightline", "forklift/pedestrian convergence"] if not resolved_step else ["mirror obstruction remains"],
            "workflow_step": "dock crossing",
            "evidence": ["Loaded forklift approaches Dock Intersection A", "Pedestrian approaches same crossing"],
        },
        "operations_conveyor_jam": {
            "visible_entities": ["cartons", "conveyor transfer"],
            "movement": ["queue growing at transfer point"] if not resolved_step else ["queue growth slowed"],
            "posture": [],
            "hazards": ["jam likely at C7"],
            "workflow_step": "outbound conveyor transfer",
            "evidence": ["Cartons accumulating at C7", "Queue exceeds normal operating pattern"],
        },
        "quality_missing_insert": {
            "visible_entities": ["open carton", "operator", "sealer"],
            "movement": ["carton approaching seal step"] if not resolved_step else ["carton held for QA"],
            "posture": [],
            "hazards": ["missing instruction insert"],
            "workflow_step": "packout before seal",
            "evidence": ["Carton is open before seal", "Required insert is not visible"],
        },
        "medical_worker_collapse": {
            "visible_entities": ["worker", "forklift lane"],
            "movement": ["worker remains motionless"] if not resolved_step else ["responder route open"],
            "posture": ["worker down"],
            "hazards": ["active forklift traffic nearby"],
            "workflow_step": "medical emergency response",
            "evidence": ["Worker down near Dock 3", "No visible movement beyond threshold"],
        },
        "security_forced_entry": {
            "visible_entities": ["restricted door", "unknown person"],
            "movement": ["door forced open"],
            "posture": [],
            "hazards": ["restricted area breach"],
            "workflow_step": "after-hours restricted access",
            "evidence": ["Restricted door forced open", "No badge match in access log"],
        },
        "adaptability_sop_swap": {
            "visible_entities": ["pedestrian", "Gate A", "cold-chain staging"],
            "movement": ["pedestrian routing through Gate A"],
            "posture": [],
            "hazards": ["route no longer compliant under cold-chain SOP"],
            "workflow_step": "traffic SOP update",
            "evidence": ["Cold-chain loading active", "Pedestrian route uses Gate A"],
        },
    }
    return mapping[scenario_id]


def _mock_risk(scenario: dict[str, Any], scenario_id: str, step_index: int, evidence_ids: list[str]) -> Risk | None:
    common = {
        "zone_id": scenario["zone_id"],
        "camera_ids": scenario.get("camera_ids", []),
        "evidence_ids": evidence_ids,
    }
    if scenario_id == "safety_forklift_near_miss":
        return Risk(
            risk_type="forklift_pedestrian_conflict",
            severity="P2",
            probability="high",
            confidence=0.84,
            time_to_event_seconds=12 if step_index == 0 else None,
            status="active" if step_index == 0 else "mitigated",
            recommended_actions=["Activate local warning", "Notify dock lead", "Clear blocked mirror"],
            applicable_policy_ids=["traffic_sop_v1"],
            **common,
        )
    if scenario_id == "operations_conveyor_jam":
        return Risk(
            risk_type="conveyor_jam_likely",
            severity="P3",
            probability="high",
            confidence=0.78,
            time_to_event_seconds=240,
            status="active" if step_index == 0 else "mitigated",
            recommended_actions=["Notify shift lead", "Create maintenance inspection task"],
            applicable_policy_ids=["mes_line_c7", "cmms_asset_c7"],
            **common,
        )
    if scenario_id == "quality_missing_insert":
        return Risk(
            risk_type="quality_escape_missing_insert",
            severity="P3",
            probability="high",
            confidence=0.88,
            status="active" if step_index == 0 else "mitigated",
            recommended_actions=["Pause release", "Create QA hold", "Notify quality lead"],
            applicable_policy_ids=["packout_sop_acme"],
            **common,
        )
    if scenario_id == "medical_worker_collapse":
        return Risk(
            risk_type="medical_collapse",
            severity="P0",
            probability="high",
            confidence=0.9,
            status="escalated",
            recommended_actions=["Request local safe-stop", "Notify onsite responder", "Mock EMS escalation"],
            applicable_policy_ids=["emergency_action_plan"],
            **common,
        )
    if scenario_id == "security_forced_entry":
        return Risk(
            risk_type="security_forced_entry",
            severity="P0",
            probability="high",
            confidence=0.82,
            status="escalated",
            recommended_actions=["Notify security", "Mock police escalation if policy allows"],
            applicable_policy_ids=["security_policy"],
            **common,
        )
    if scenario_id == "adaptability_sop_swap":
        return Risk(
            risk_type="cold_chain_crossing_policy_violation",
            severity="P2",
            probability="medium",
            confidence=0.81,
            status="active",
            recommended_actions=["Notify area lead", "Route pedestrians through Gate B"],
            applicable_policy_ids=["traffic_sop_v2_cold_chain"],
            **common,
        )
    return None


def _mock_tools(scenario_id: str, step_index: int) -> list[tuple[str, dict[str, Any]]]:
    if scenario_id == "safety_forklift_near_miss":
        return [
            ("retrieve_sop", {"process_name": "traffic_sop_v1"}),
            ("activate_warning_beacon", {"zone_id": "dock_intersection_a", "message": "Forklift crossing. Stop and check."}),
            ("notify_shift_lead", {"zone_id": "dock_intersection_a", "message": "Forklift/pedestrian convergence risk"}),
            ("create_preventive_task", {"owner_role": "material_handler", "priority": "high", "due_time": "immediate", "task": "Clear blocked mirror"}),
            ("schedule_recheck", {"camera_id": "CAM-DOCK-A", "condition": "risk_reduced", "deadline": "60 seconds"}),
            ("verify_risk_reduced", {"zone_id": "dock_intersection_a"}),
        ]
    if scenario_id == "operations_conveyor_jam":
        return [
            ("query_mes", {"line_id": "line_c7", "time_range": "last_10_minutes"}),
            ("query_cmms", {"asset_id": "asset_c7"}),
            ("notify_shift_lead", {"zone_id": "conveyor_transfer_c7", "message": "Queue buildup likely to cause jam"}),
            ("create_preventive_task", {"owner_role": "maintenance_tech", "priority": "medium", "due_time": "2 minutes", "task": "Inspect C7 transfer point"}),
            ("schedule_recheck", {"camera_id": "CAM-CONV-C7", "condition": "queue_reduced", "deadline": "2 minutes"}),
            ("generate_prevention_scorecard", {}),
        ]
    if scenario_id == "quality_missing_insert":
        return [
            ("retrieve_sop", {"process_name": "packout_sop_acme"}),
            ("query_wms", {"order_id": "A-1048"}),
            ("pause_work_release", {"workstation_id": "pack_station_02", "reason": "Missing required insert before seal"}),
            ("create_quality_hold", {"order_id": "A-1048", "reason": "Missing ACME instruction insert"}),
            ("notify_quality_lead", {"zone_id": "pack_station_02", "message": "QA hold created for missing insert"}),
            ("verify_task_completed", {"task_id": "quality_hold"}),
        ]
    if scenario_id == "medical_worker_collapse":
        return [
            ("retrieve_emergency_action_plan", {"site_id": "demo_dc"}),
            ("retrieve_site_map", {"site_id": "demo_dc"}),
            ("get_nearest_emergency_entry", {"zone_id": "outbound_dock_3"}),
            ("request_safe_stop", {"asset_id": "outbound_dock_zone", "reason": "Worker collapsed near active forklift traffic"}),
            ("open_emergency_incident_card", {"type": "medical", "severity": "P0"}),
            ("notify_onsite_first_responder", {"zone_id": "outbound_dock_3"}),
            ("call_ems", {"site_id": "demo_dc", "zone_id": "outbound_dock_3", "callback_number": "demo-command-center"}),
        ]
    if scenario_id == "security_forced_entry":
        return [
            ("query_access_control", {"door_id": "restricted_door", "time_range": "last_5_minutes"}),
            ("retrieve_security_policy", {"site_id": "demo_dc"}),
            ("notify_security", {"zone_id": "restricted_cage_door", "message": "Forced entry with no badge match"}),
            ("open_emergency_incident_card", {"type": "security", "severity": "P0"}),
            ("call_police", {"site_id": "demo_dc", "zone_id": "restricted_cage_door", "callback_number": "demo-command-center"}),
        ]
    if scenario_id == "adaptability_sop_swap":
        return [
            ("retrieve_sop", {"process_name": "traffic_sop_v2_cold_chain"}),
            ("notify_shift_lead", {"zone_id": "dock_intersection_a", "message": "Cold-chain loading requires Gate B crossing only"}),
            ("create_preventive_task", {"owner_role": "area_lead", "priority": "high", "due_time": "immediate", "task": "Brief Gate B cold-chain crossing rule"}),
        ]
    return []


def _mock_summary(scenario_id: str, step_index: int) -> str:
    summaries = {
        "safety_forklift_near_miss": "Forklift and pedestrian convergence risk detected; warning, notification, task, and recheck selected.",
        "operations_conveyor_jam": "Conveyor C7 queue growth matches prior jam pattern; maintenance task and recheck selected.",
        "quality_missing_insert": "Packout SOP requires ACME insert before seal; QA hold and quality notification selected.",
        "medical_worker_collapse": "Worker collapse meets P0 medical threshold; mock emergency protocol selected.",
        "security_forced_entry": "Forced entry with no badge match meets configured P0 security policy.",
        "adaptability_sop_swap": "Updated cold-chain traffic SOP changes crossing recommendation to Gate B.",
    }
    return summaries.get(scenario_id, f"Mock decision for step {step_index}.")
