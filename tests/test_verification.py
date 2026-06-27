import unittest

from ops_guardian.models import Risk, RunState, Scenario, SceneObservation
from ops_guardian.tools import ToolRegistry


def make_state(risks, observations=None) -> RunState:
    scenario = Scenario(
        scenario_id="safety_forklift_near_miss",
        title="Forklift near miss",
        description="Forklift and pedestrian converge at dock intersection.",
        clip_path="clips/forklift.mp4",
        camera_ids=["cam-dock-a"],
        zone_id="dock_intersection_a",
        expected_event_class="forklift_pedestrian_conflict",
    )
    state = RunState(scenario=scenario)
    state.risks = risks
    if observations:
        state.observations = observations
    return state


def make_observation(hazards=None, movement=None) -> SceneObservation:
    return SceneObservation(
        scenario_id="safety_forklift_near_miss",
        step_index=0,
        hazards=hazards or [],
        movement=movement or [],
    )


class VerifyRiskReducedTest(unittest.TestCase):
    def test_risk_mitigated_when_hazard_gone(self):
        risk = Risk(risk_type="forklift_pedestrian_conflict", severity="P2", zone_id="dock_intersection_a")
        # No risk_type tokens (forklift/pedestrian/conflict) appear -> hazard cleared.
        observation = make_observation(hazards=["aisle clear"], movement=["no traffic"])
        state = make_state([risk], [observation])

        result = ToolRegistry(data_sources={}).verify_risk_reduced(state, {})

        self.assertEqual(risk.status, "mitigated")
        self.assertIn(risk.risk_id, result["verified_risks"])
        self.assertEqual(result["still_present"], [])
        self.assertTrue(result["risk_reduced"])
        self.assertIsNotNone(result["evidence_id"])

    def test_risk_unresolved_when_hazard_present(self):
        risk = Risk(risk_type="forklift_pedestrian_conflict", severity="P2", zone_id="dock_intersection_a")
        observation = make_observation(
            hazards=["pedestrian in forklift path"],
            movement=["forklift approaching intersection"],
        )
        state = make_state([risk], [observation])

        result = ToolRegistry(data_sources={}).verify_risk_reduced(state, {})

        self.assertEqual(risk.status, "unresolved")
        self.assertIn(risk.risk_id, result["still_present"])
        self.assertEqual(result["verified_risks"], [])
        self.assertFalse(result["risk_reduced"])
        self.assertIsNotNone(result["evidence_id"])

    def test_status_unchanged_without_observation(self):
        risk = Risk(
            risk_type="forklift_pedestrian_conflict",
            severity="P2",
            zone_id="dock_intersection_a",
            status="active",
        )
        state = make_state([risk])

        result = ToolRegistry(data_sources={}).verify_risk_reduced(state, {})

        self.assertEqual(risk.status, "active")
        self.assertEqual(result["verified_risks"], [])
        self.assertEqual(result["still_present"], [])
        self.assertFalse(result["risk_reduced"])

    def test_p0_risk_never_downgraded(self):
        risk = Risk(
            risk_type="worker_collapse",
            severity="P0",
            zone_id="dock_intersection_a",
            status="escalated",
        )
        observation = make_observation(hazards=["area clear"], movement=["no one present"])
        state = make_state([risk], [observation])

        result = ToolRegistry(data_sources={}).verify_risk_reduced(state, {})

        self.assertEqual(risk.status, "escalated")
        self.assertNotIn(risk.risk_id, result["verified_risks"])
        self.assertNotIn(risk.risk_id, result["still_present"])


if __name__ == "__main__":
    unittest.main()
