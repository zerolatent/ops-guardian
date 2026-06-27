from __future__ import annotations

from typing import Any

from .config import Settings
from .data_loader import DemoData
from .model_adapters import ModelAdapter
from .models import CreateRunRequest, RunState, StepTrace
from .perception import Perceptor
from .scoring import compute_risk_score
from .storage import Storage
from .tools import ToolRegistry
from .video import VideoSampler


class ScenarioRunner:
    def __init__(
        self,
        settings: Settings,
        storage: Storage,
        demo_data: DemoData,
        mock_adapter: ModelAdapter,
        live_adapter: ModelAdapter | None = None,
    ):
        self.settings = settings
        self.storage = storage
        self.demo_data = demo_data
        self.mock_adapter = mock_adapter
        self.live_adapter = live_adapter
        self.sampler = VideoSampler(settings.frame_window_seconds)
        self.perceptor = Perceptor(
            enabled=True,
            detector_model=settings.detector_model,
            pose_model=settings.pose_model,
        )

    def _adapters_for(self, mode: str):
        """Return (analyze_adapter, plan_adapter, perception_on) for a run mode."""
        live = self.live_adapter or self.mock_adapter
        if mode == "live":
            return live, live, True
        if mode == "hybrid":
            return live, self.mock_adapter, True
        return self.mock_adapter, self.mock_adapter, False

    def list_scenarios(self) -> list[dict[str, Any]]:
        return [scenario.model_dump(mode="json") for scenario in self.demo_data.scenarios()]

    def start_run(self, request: CreateRunRequest) -> RunState:
        scenario = self.demo_data.scenario(request.scenario_id)
        state = RunState(scenario=scenario, status="running", mode=request.mode)
        return self.storage.save_run(state)

    async def step_run(self, run_id: str) -> RunState:
        state = self.storage.get_run(run_id)
        if state.status == "completed":
            return state
        data_sources = self.demo_data.all_context()
        tools = ToolRegistry(data_sources, confirmation_confidence=self.settings.p0_confirmation_confidence)
        analyze_adapter, plan_adapter, perception_on = self._adapters_for(state.mode)
        frame_window = self.sampler.sample(state.scenario, state.step_index)
        if perception_on:
            frame_window.perception = self.perceptor.analyze(frame_window, state.scenario, capture_trace=True)
        self._accumulate_motionless(state, frame_window)
        # cap frames sent to the VLM (perception already used the full clip); keeps local VLMs fast
        if self.settings.vlm_max_images and len(frame_window.images_base64) > self.settings.vlm_max_images:
            frame_window.images_base64 = frame_window.images_base64[: self.settings.vlm_max_images]
        context = self._context(state, data_sources)

        observation = await analyze_adapter.analyze_scene(frame_window, context)
        state.observations.append(observation)
        state.evidence.extend(observation.evidence)

        active_risks = [risk for risk in state.risks if risk.status in {"active", "predicted", "unresolved", "escalated"}]
        tool_results: list[dict] = []
        agent_summary = ""
        for _iteration in range(self.settings.max_tool_iterations):
            decision = await plan_adapter.plan_next_action(
                observation, active_risks, tools.available_tools, context, tool_results=tool_results
            )
            agent_summary = decision.summary or agent_summary
            for risk in decision.risks:
                risk.risk_score = compute_risk_score(
                    severity=risk.severity,
                    probability=risk.probability,
                    confidence=risk.confidence,
                    time_to_event_seconds=risk.time_to_event_seconds,
                    exposure=self._exposure(frame_window),
                )
            state.risks.extend(decision.risks)
            if not decision.tool_calls:
                break
            for tool_call in decision.tool_calls:
                tools.execute(state, tool_call)
                state.tool_calls.append(tool_call)
                tool_results.append(
                    {"tool_name": tool_call.tool_name, "status": tool_call.status, "output": tool_call.output}
                )
            if decision.done:
                break

        state.traces.append(self._build_step_trace(state, frame_window, context, observation, agent_summary))
        state.step_index += 1
        if state.step_index >= state.scenario.max_steps:
            self._complete_state(state, tools)
        return self.storage.save_run(state)

    def _build_step_trace(self, state, frame_window, context, observation, agent_summary) -> StepTrace:
        perception = frame_window.perception if isinstance(frame_window.perception, dict) else {}
        ptrace = perception.get("trace", {}) or {}
        facts = {k: v for k, v in perception.items() if k != "trace"}
        return StepTrace(
            step_index=state.step_index,
            mode=state.mode,
            camera_id=frame_window.camera_id,
            window={"start": frame_window.start_seconds, "end": frame_window.end_seconds},
            perception=facts,
            detections=ptrace.get("detections", []),
            pose=facts.get("pose", {}) or {},
            annotated_frame_b64=ptrace.get("annotated_frame_b64"),
            vlm_input=self._vlm_input(frame_window, context, facts),
            vlm_observation=observation.model_dump(mode="json"),
            agent_summary=agent_summary,
        )

    def _vlm_input(self, frame_window, context, facts) -> dict[str, Any]:
        return {
            "task": "Analyze this industrial operations video window for current scene state.",
            "frames_attached": len(frame_window.images_base64),
            "perception_facts": facts,
            "scenario_id": (context.get("scenario") or {}).get("scenario_id"),
            "relevant_context_keys": sorted((context.get("relevant_context") or {}).keys()),
            "output_schema": [
                "visible_entities", "movement", "posture", "hazards",
                "workflow_step", "uncertainty", "evidence_descriptions",
            ],
        }

    async def complete_run(self, run_id: str) -> RunState:
        state = self.storage.get_run(run_id)
        while state.status != "completed":
            state = await self.step_run(run_id)
        return state

    def get_run(self, run_id: str) -> RunState:
        return self.storage.get_run(run_id)

    def get_handover(self, run_id: str) -> dict[str, Any]:
        state = self.storage.get_run(run_id)
        if state.handover is None:
            tools = ToolRegistry(self.demo_data.all_context(), confirmation_confidence=self.settings.p0_confirmation_confidence)
            tools.generate_shift_handover(state, {})
            self.storage.save_run(state)
        return state.handover.model_dump(mode="json") if state.handover else {}

    def reset(self) -> dict[str, str]:
        self.storage.reset()
        return {"status": "reset"}

    def _accumulate_motionless(self, state: RunState, frame_window) -> None:
        """Carry motionless duration across windows so the P0 medical threshold is real."""
        perception = frame_window.perception or {}
        pose = perception.get("pose") if isinstance(perception, dict) else None
        if perception.get("available") and isinstance(pose, dict) and pose.get("state") == "prone":
            state.perception_motionless_seconds += float(pose.get("motionless_seconds_window") or 0.0)
        else:
            state.perception_motionless_seconds = 0.0
        if isinstance(pose, dict):
            threshold = self.settings.p0_motionless_threshold_seconds
            pose["motionless_seconds_cumulative"] = round(state.perception_motionless_seconds, 1)
            pose["p0_motionless_threshold_seconds"] = threshold
            pose["p0_threshold_met"] = state.perception_motionless_seconds >= threshold

    def _exposure(self, frame_window) -> float:
        """Approximate exposure (people/assets affected) from perception entity counts."""
        perception = frame_window.perception or {}
        if not perception.get("available"):
            return 1.0
        entities = int(perception.get("person_count", 0)) + int(perception.get("vehicle_count", 0))
        if entities <= 0:
            return 0.4
        return min(1.0, 0.4 + 0.2 * entities)

    def _complete_state(self, state: RunState, tools: ToolRegistry) -> None:
        tools.generate_prevention_scorecard(state, {})
        tools.generate_shift_handover(state, {})
        state.status = "completed"

    def _context(self, state: RunState, data_sources: dict[str, Any]) -> dict[str, Any]:
        scenario = state.scenario.model_dump(mode="json")
        return {
            "scenario": scenario,
            "step_index": state.step_index,
            "site_map": data_sources.get("site_map"),
            "relevant_context": self._relevant_context(state, data_sources),
            "authority_matrix": {
                "mock_emergency_only": True,
                "direct_safety_plc_control": "never",
                "worker_discipline": "never",
                "face_recognition": "off_by_default",
                "safe_stop_mode": self.settings.safe_stop_mode,
                "quality_hold_mode": self.settings.quality_hold_mode,
            },
            "settings": {
                "p0_motionless_threshold_seconds": self.settings.p0_motionless_threshold_seconds,
                "quality_hold_mode": self.settings.quality_hold_mode,
                "safe_stop_mode": self.settings.safe_stop_mode,
            },
        }

    def _relevant_context(self, state: RunState, data_sources: dict[str, Any]) -> dict[str, Any]:
        ids = set(state.scenario.data_source_ids)
        context: dict[str, Any] = {}
        if "site_map" in ids:
            context["site_map"] = data_sources.get("site_map")
        if "wms_orders" in ids:
            context["wms"] = data_sources.get("wms")
        if "mes_events" in ids:
            context["mes"] = data_sources.get("mes")
        if "cmms_assets" in ids:
            context["cmms"] = data_sources.get("cmms")
        if "access_control" in ids:
            context["access_control"] = data_sources.get("access_control")
        if "emergency_action_plan" in ids:
            context["emergency_policy"] = data_sources.get("emergency_policy")
        if "security_policy" in ids:
            context["security_policy"] = data_sources.get("security_policy")
        sops = data_sources.get("sops", {})
        context["sops"] = {key: value for key, value in sops.items() if key in ids or key.startswith("traffic_sop")}
        return context
