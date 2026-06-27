from __future__ import annotations

from datetime import timedelta
from typing import Any, Callable

from .models import Action, EmergencyIncident, Evidence, RunState, ShiftHandover, ToolCall, utc_now

EMERGENCY_TOOLS = {"call_ems", "call_fire", "call_police"}
GENERIC_EMERGENCY_TOKENS = {
    "collapse", "collapsed", "motionless", "down", "unconscious", "injured",
    "fall", "fallen", "fire", "smoke", "explosion", "weapon", "gun", "knife",
    "forced", "breach", "intrusion", "assault", "violence",
}


class AuthorityGuard:
    def check(self, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        if tool_name in {"call_ems", "call_fire", "call_police"}:
            return True, "allowed_mock_endpoint_only"
        if tool_name == "request_safe_stop":
            return True, "allowed_simulated_safe_stop_request_only"
        if tool_name in {"activate_warning_beacon", "create_quality_hold"}:
            return True, "allowed_configured_demo_action"
        if tool_name in {"discipline_worker", "identify_worker_by_face", "control_safety_plc"}:
            return False, "blocked_by_non_goal"
        return True, "allowed"


class ToolRegistry:
    def __init__(
        self,
        data_sources: dict[str, Any],
        guard: AuthorityGuard | None = None,
        confirmation_confidence: float = 0.75,
    ):
        self.data_sources = data_sources
        self.guard = guard or AuthorityGuard()
        self.confirmation_confidence = confirmation_confidence
        self._tools: dict[str, Callable[[RunState, dict[str, Any]], dict[str, Any]]] = {
            "retrieve_sop": self.retrieve_sop,
            "retrieve_emergency_action_plan": self.retrieve_emergency_action_plan,
            "retrieve_security_policy": self.retrieve_security_policy,
            "retrieve_site_map": self.retrieve_site_map,
            "query_wms": self.query_wms,
            "query_mes": self.query_mes,
            "query_cmms": self.query_cmms,
            "query_access_control": self.query_access_control,
            "get_nearest_emergency_entry": self.get_nearest_emergency_entry,
            "get_nearest_aed": self.get_nearest_aed,
            "activate_warning_beacon": self.activate_warning_beacon,
            "send_radio_alert": self.send_radio_alert,
            "notify_shift_lead": self.notify_shift_lead,
            "notify_safety_officer": self.notify_safety_officer,
            "notify_quality_lead": self.notify_quality_lead,
            "notify_security": self.notify_security,
            "create_preventive_task": self.create_preventive_task,
            "pause_work_release": self.pause_work_release,
            "create_quality_hold": self.create_quality_hold,
            "request_safe_stop": self.request_safe_stop,
            "schedule_recheck": self.schedule_recheck,
            "call_ems": self.call_ems,
            "call_fire": self.call_fire,
            "call_police": self.call_police,
            "notify_onsite_first_responder": self.notify_onsite_first_responder,
            "start_employee_accountability_check": self.start_employee_accountability_check,
            "stream_incident_to_command_center": self.stream_incident_to_command_center,
            "open_emergency_incident_card": self.open_emergency_incident_card,
            "verify_risk_reduced": self.verify_risk_reduced,
            "verify_task_completed": self.verify_task_completed,
            "generate_live_risk_board": self.generate_live_risk_board,
            "generate_prevention_scorecard": self.generate_prevention_scorecard,
            "generate_shift_handover": self.generate_shift_handover,
        }

    @property
    def available_tools(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, state: RunState, tool_call: ToolCall) -> ToolCall:
        allowed, policy = self.guard.check(tool_call.tool_name, tool_call.arguments)
        tool_call.policy_check = policy
        if not allowed:
            tool_call.status = "blocked"
            tool_call.output = {"error": policy}
            return tool_call
        if tool_call.tool_name in EMERGENCY_TOOLS and not self._p0_confirmed(state):
            self._record_p0_review(state, tool_call)
            tool_call.status = "blocked"
            tool_call.policy_check = "p0_unconfirmed"
            tool_call.output = {"error": "p0_unconfirmed", "review_required": True}
            return tool_call
        tool = self._tools.get(tool_call.tool_name)
        if tool is None:
            tool_call.status = "failed"
            tool_call.output = {"error": f"Unknown tool: {tool_call.tool_name}"}
            return tool_call
        try:
            tool_call.status = "allowed"
            tool_call.output = tool(state, tool_call.arguments)
            tool_call.status = "completed"
        except Exception as exc:
            tool_call.status = "failed"
            tool_call.output = {"error": str(exc)}
        return tool_call

    def retrieve_sop(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        process_name = args["process_name"]
        text = self.data_sources.get("sops", {}).get(process_name)
        if text is None:
            raise KeyError(f"Unknown SOP: {process_name}")
        evidence = Evidence(type="sop_snippet", source=process_name, description=text.splitlines()[0], uri=f"sop://{process_name}")
        state.evidence.append(evidence)
        return {"process_name": process_name, "snippet": text[:500], "evidence_id": evidence.evidence_id}

    def retrieve_emergency_action_plan(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "site_id": args.get("site_id"),
            "policy": self.data_sources.get("emergency_policy", {}),
            "sop": self.data_sources.get("sops", {}).get("emergency_action_plan", ""),
        }

    def retrieve_security_policy(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "site_id": args.get("site_id"),
            "policy": self.data_sources.get("security_policy", {}),
            "sop": self.data_sources.get("sops", {}).get("security_policy", ""),
        }

    def retrieve_site_map(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        return self.data_sources.get("site_map", {})

    def query_wms(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        order_id = args.get("order_id")
        orders = self.data_sources.get("wms", {}).get("orders", {})
        return orders.get(order_id, {"error": f"Unknown order_id: {order_id}"})

    def query_mes(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        line_id = args.get("line_id")
        lines = self.data_sources.get("mes", {}).get("lines", {})
        return lines.get(line_id, {"error": f"Unknown line_id: {line_id}"})

    def query_cmms(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        asset_id = args.get("asset_id")
        assets = self.data_sources.get("cmms", {}).get("assets", {})
        return assets.get(asset_id, {"error": f"Unknown asset_id: {asset_id}"})

    def query_access_control(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        door_id = args.get("door_id")
        doors = self.data_sources.get("access_control", {}).get("doors", {})
        return doors.get(door_id, {"error": f"Unknown door_id: {door_id}"})

    def get_nearest_emergency_entry(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        zone = self._zone(args.get("zone_id") or state.scenario.zone_id)
        return {"zone_id": args.get("zone_id") or state.scenario.zone_id, "nearest_entry": zone.get("nearest_entry")}

    def get_nearest_aed(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        zone = self._zone(args.get("zone_id") or state.scenario.zone_id)
        return {"zone_id": args.get("zone_id") or state.scenario.zone_id, "nearest_aed": zone.get("nearest_aed")}

    def activate_warning_beacon(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(
            state,
            "warning",
            "dock_lead",
            {"zone_id": args.get("zone_id"), "message": args.get("message"), "simulated": True},
            status="sent",
        )
        return {"action_id": action.action_id, "simulated": True}

    def send_radio_alert(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "notification", "radio_channel", args, status="sent")
        return {"action_id": action.action_id}

    def notify_shift_lead(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "notification", "shift_lead", args, status="sent")
        return {"action_id": action.action_id, "acknowledgment_requested": True}

    def notify_safety_officer(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "notification", "safety_officer", args, status="sent")
        return {"action_id": action.action_id}

    def notify_quality_lead(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "notification", "quality_lead", args, status="sent")
        return {"action_id": action.action_id}

    def notify_security(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "notification", "security", args, status="sent")
        return {"action_id": action.action_id}

    def create_preventive_task(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        due_at = utc_now() + timedelta(minutes=2 if args.get("due_time") != "immediate" else 0)
        action = self._add_action(
            state,
            "task",
            args.get("owner_role", "area_lead"),
            args,
            status="created",
            due_at=due_at,
        )
        return {"task_id": action.action_id, "due_at": due_at.isoformat()}

    def pause_work_release(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "hold", "pack_station_operator", args, status="sent")
        return {"action_id": action.action_id, "release_paused": True}

    def create_quality_hold(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "hold", "quality_lead", args, status="created")
        return {"hold_id": action.action_id, "mock_hold": True}

    def request_safe_stop(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "safe_stop_request", "area_lead", {**args, "simulated": True}, status="sent")
        return {"action_id": action.action_id, "simulated": True}

    def schedule_recheck(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        evidence = Evidence(
            type="tool_output",
            source="schedule_recheck",
            description=f"Recheck scheduled for {args.get('condition')}",
            uri=f"recheck://{state.run_id}/{args.get('camera_id', state.scenario.camera_ids[0])}",
        )
        state.evidence.append(evidence)
        return {"recheck_id": evidence.evidence_id, "condition": args.get("condition"), "deadline": args.get("deadline")}

    def call_ems(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        return self._mock_emergency_call(state, args, "EMS")

    def call_fire(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        return self._mock_emergency_call(state, args, "FIRE")

    def call_police(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        return self._mock_emergency_call(state, args, "POLICE")

    def notify_onsite_first_responder(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "notification", "onsite_first_responder", args, status="sent")
        for incident in state.incidents:
            if "onsite_first_responder" not in incident.responders_notified:
                incident.responders_notified.append("onsite_first_responder")
        return {"action_id": action.action_id}

    def start_employee_accountability_check(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        action = self._add_action(state, "task", "shift_supervisor", args, status="created")
        return {"action_id": action.action_id, "accountability_check": "started"}

    def stream_incident_to_command_center(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        return {"incident_id": args.get("incident_id") or (state.incidents[-1].incident_id if state.incidents else None), "stream": "mock_command_center"}

    def open_emergency_incident_card(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        emergency_type = args.get("type", "medical")
        zone_id = args.get("zone_id") or state.scenario.zone_id
        zone = self._zone(zone_id)
        incident = EmergencyIncident(
            emergency_type=emergency_type,
            severity=args.get("severity", "P0"),
            site_id=self.data_sources.get("site_map", {}).get("site_id", "demo_dc"),
            building=self.data_sources.get("site_map", {}).get("building", "Building B"),
            zone_id=zone_id,
            nearest_entry=zone.get("nearest_entry", "Unknown"),
            camera_ids=state.scenario.camera_ids,
            observed_condition=args.get("observed_condition", state.scenario.description),
            hazards_nearby=zone.get("hazards", []),
            status="opened",
        )
        state.incidents.append(incident)
        return {"incident_id": incident.incident_id, "status": incident.status}

    def verify_risk_reduced(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        target_zone = args.get("zone_id")
        observation = state.observations[-1] if state.observations else None
        verified_risks: list[str] = []
        still_present: list[str] = []
        if observation is None:
            evidence = Evidence(
                type="tool_output",
                source="verify_risk_reduced",
                description="No scene observation available; risk status unchanged (cannot verify).",
                uri=f"verify://{state.run_id}/no_observation",
            )
            state.evidence.append(evidence)
            return {
                "verified_risks": verified_risks,
                "still_present": still_present,
                "risk_reduced": False,
                "evidence_id": evidence.evidence_id,
            }
        hazard_text = " ".join(observation.hazards + observation.movement).lower()
        for risk in state.risks:
            if target_zone is not None and risk.zone_id != target_zone:
                continue
            if risk.severity == "P0":
                risk.updated_at = utc_now()
                continue
            tokens = [token for token in risk.risk_type.lower().split("_") if token]
            hazard_present = any(token in hazard_text for token in tokens)
            if hazard_present:
                risk.status = "unresolved"
                still_present.append(risk.risk_id)
            else:
                risk.status = "mitigated"
                verified_risks.append(risk.risk_id)
            risk.updated_at = utc_now()
        evidence = Evidence(
            type="tool_output",
            source="verify_risk_reduced",
            description=(
                f"Verified against observation {observation.observation_id}: "
                f"cleared={verified_risks or 'none'}, still_present={still_present or 'none'}."
            ),
            uri=f"verify://{state.run_id}/{observation.observation_id}",
        )
        state.evidence.append(evidence)
        return {
            "verified_risks": verified_risks,
            "still_present": still_present,
            "risk_reduced": bool(verified_risks),
            "evidence_id": evidence.evidence_id,
        }

    def verify_task_completed(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        for action in state.actions:
            if args.get("task_id") in {action.action_id, "quality_hold"} and action.action_type in {"hold", "task"}:
                action.status = "completed"
        return {"task_id": args.get("task_id"), "verified": True}

    def generate_live_risk_board(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        # Rank by the PRD risk_score when available; fall back to severity + confidence.
        risks = sorted(
            state.risks,
            key=lambda risk: (
                -(risk.risk_score if risk.risk_score is not None else -1),
                order.get(risk.severity, 9),
                -(risk.confidence or 0),
            ),
        )
        return {"risks": [risk.model_dump(mode="json") for risk in risks]}

    def generate_prevention_scorecard(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        state.scorecard = {
            "predicted_risks": len(state.risks),
            "verified_reductions": len([risk for risk in state.risks if risk.status == "mitigated"]),
            "open_items": len([action for action in state.actions if action.status not in {"completed", "failed"}]),
            "emergency_incidents": len(state.incidents),
        }
        return state.scorecard

    def generate_shift_handover(self, state: RunState, args: dict[str, Any]) -> dict[str, Any]:
        handover = ShiftHandover(
            shift_id=state.shift_id,
            site_id=self.data_sources.get("site_map", {}).get("site_id", "demo_dc"),
            zone_id=state.scenario.zone_id,
            start_time=state.started_at,
            resolved_risks=[risk.risk_id for risk in state.risks if risk.status == "mitigated"],
            open_risks=[risk.risk_id for risk in state.risks if risk.status in {"active", "predicted", "unresolved"}],
            emergency_incidents=[incident.incident_id for incident in state.incidents],
            quality_holds=[action.action_id for action in state.actions if action.action_type == "hold"],
            maintenance_watch_items=[
                action.action_id for action in state.actions if action.owner_role in {"maintenance_tech", "maintenance_lead"}
            ],
            unresolved_tasks=[action.action_id for action in state.actions if action.action_type == "task" and action.status != "completed"],
            recommendations=self._recommendations(state),
        )
        state.handover = handover
        return handover.model_dump(mode="json")

    def _add_action(
        self,
        state: RunState,
        action_type: str,
        owner_role: str,
        payload: dict[str, Any],
        status: str = "created",
        due_at: Any | None = None,
    ) -> Action:
        risk_id = state.risks[-1].risk_id if state.risks else None
        action = Action(
            action_type=action_type,  # type: ignore[arg-type]
            risk_id=risk_id,
            owner_role=owner_role,
            status=status,  # type: ignore[arg-type]
            due_at=due_at,
            payload=payload,
            acknowledgment={"requested": status == "sent", "received": False},
        )
        state.actions.append(action)
        if risk_id:
            state.risks[-1].actions_taken.append(action.action_id)
        return action

    def _p0_confirmed(self, state: RunState) -> bool:
        active_statuses = {"active", "predicted", "unresolved", "escalated"}
        p0_risks = [
            risk
            for risk in state.risks
            if risk.severity == "P0"
            and risk.status in active_statuses
            and (risk.confidence or 0) >= self.confirmation_confidence
        ]
        if not p0_risks or not state.observations:
            return False
        observation = state.observations[-1]
        observed_text = " ".join(
            observation.hazards + observation.posture + observation.movement
        ).lower()
        if not observed_text.strip():
            return False
        for risk in p0_risks:
            tokens = {token for token in risk.risk_type.lower().split("_") if token} | GENERIC_EMERGENCY_TOKENS
            if any(token in observed_text for token in tokens):
                return True
        return False

    def _record_p0_review(self, state: RunState, tool_call: ToolCall) -> Action:
        payload = {
            "reason": "p0_unconfirmed",
            "blocked_tool": tool_call.tool_name,
            "blocked_arguments": tool_call.arguments,
            "message": "Emergency call blocked: independent P0 confirmation required before dispatch.",
            "manual_confirmation_required": True,
        }
        return self._add_action(state, "notification", "shift_supervisor", payload, status="sent")

    def _mock_emergency_call(self, state: RunState, args: dict[str, Any], responder: str) -> dict[str, Any]:
        zone_id = args.get("zone_id") or state.scenario.zone_id
        zone = self._zone(zone_id)
        payload = {
            "mock": True,
            "responder": responder,
            "site_id": args.get("site_id") or self.data_sources.get("site_map", {}).get("site_id", "demo_dc"),
            "building": self.data_sources.get("site_map", {}).get("building", "Building B"),
            "zone_id": zone_id,
            "nearest_entry": zone.get("nearest_entry"),
            "camera_ids": state.scenario.camera_ids,
            "timestamp": utc_now().isoformat(),
            "hazards_nearby": zone.get("hazards", []),
            "callback_route": args.get("callback_number", "demo-command-center"),
        }
        action = self._add_action(state, "emergency_call", responder.lower(), payload, status="sent")
        if state.incidents:
            incident = state.incidents[-1]
            incident.escalation_payload = payload
            incident.status = "responders_notified"
            if responder.lower() not in incident.responders_notified:
                incident.responders_notified.append(responder.lower())
        return {"action_id": action.action_id, "payload": payload}

    def _zone(self, zone_id: str) -> dict[str, Any]:
        return self.data_sources.get("site_map", {}).get("zones", {}).get(zone_id, {})

    def _recommendations(self, state: RunState) -> list[str]:
        recommendations = []
        if any(risk.risk_type == "forklift_pedestrian_conflict" for risk in state.risks):
            recommendations.append("Verify Dock Intersection A sightline is cleared.")
        if any(action.action_type == "hold" for action in state.actions):
            recommendations.append("Confirm QA disposition before shipment release.")
        if state.incidents:
            recommendations.append("Review emergency response acknowledgment timeline.")
        if any(risk.risk_type == "conveyor_jam_likely" for risk in state.risks):
            recommendations.append("Inspect C7 if queue growth repeats.")
        return recommendations or ["Continue monitoring active zone risks."]
