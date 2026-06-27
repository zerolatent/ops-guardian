import unittest

from ops_guardian.models import Risk, RunState, Scenario, SceneObservation, ToolCall
from ops_guardian.tools import ToolRegistry


def make_state(risk: Risk, observation: SceneObservation | None) -> RunState:
    scenario = Scenario(
        scenario_id="medical_worker_collapse",
        title="Worker collapse",
        description="Worker collapses near forklift traffic.",
        clip_path="clips/collapse.mp4",
        camera_ids=["CAM-DOCK-03"],
        zone_id="outbound_dock_3",
        expected_event_class="p0_medical_emergency",
    )
    state = RunState(scenario=scenario)
    state.risks = [risk]
    if observation is not None:
        state.observations = [observation]
    return state


def collapse_observation() -> SceneObservation:
    return SceneObservation(
        scenario_id="medical_worker_collapse",
        step_index=0,
        posture=["worker down"],
        movement=["worker remains motionless"],
        hazards=["active forklift traffic nearby"],
    )


class P0GateTest(unittest.TestCase):
    def test_confirmed_p0_allows_emergency_call(self):
        risk = Risk(
            risk_type="medical_collapse",
            severity="P0",
            zone_id="outbound_dock_3",
            status="escalated",
            confidence=0.9,
        )
        state = make_state(risk, collapse_observation())
        tools = ToolRegistry(data_sources={}, confirmation_confidence=0.75)

        call = tools.execute(state, ToolCall(tool_name="call_ems", arguments={"zone_id": "outbound_dock_3"}))

        self.assertEqual(call.status, "completed")
        self.assertTrue(any(a.action_type == "emergency_call" for a in state.actions))

    def test_low_confidence_p0_is_blocked_and_review_recorded(self):
        risk = Risk(
            risk_type="medical_collapse",
            severity="P0",
            zone_id="outbound_dock_3",
            status="escalated",
            confidence=0.5,  # below threshold -> unconfirmed
        )
        state = make_state(risk, collapse_observation())
        tools = ToolRegistry(data_sources={}, confirmation_confidence=0.75)

        call = tools.execute(state, ToolCall(tool_name="call_ems", arguments={"zone_id": "outbound_dock_3"}))

        self.assertEqual(call.status, "blocked")
        self.assertEqual(call.policy_check, "p0_unconfirmed")
        self.assertFalse(any(a.action_type == "emergency_call" for a in state.actions))
        self.assertTrue(
            any(a.owner_role == "shift_supervisor" and a.payload.get("reason") == "p0_unconfirmed" for a in state.actions)
        )

    def test_no_observation_blocks_emergency_call(self):
        risk = Risk(
            risk_type="medical_collapse",
            severity="P0",
            zone_id="outbound_dock_3",
            status="escalated",
            confidence=0.9,
        )
        state = make_state(risk, None)  # cannot corroborate without an observation
        tools = ToolRegistry(data_sources={}, confirmation_confidence=0.75)

        call = tools.execute(state, ToolCall(tool_name="call_ems", arguments={"zone_id": "outbound_dock_3"}))

        self.assertEqual(call.status, "blocked")
        self.assertFalse(any(a.action_type == "emergency_call" for a in state.actions))


if __name__ == "__main__":
    unittest.main()
