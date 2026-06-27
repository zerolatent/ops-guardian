import unittest

from ops_guardian.models import Risk, RunState, Scenario
from ops_guardian.scoring import compute_risk_score, time_urgency
from ops_guardian.tools import ToolRegistry


class ScoringTest(unittest.TestCase):
    def test_severe_urgent_confident_outranks_minor(self):
        hot = compute_risk_score("P0", "high", 0.95, time_to_event_seconds=10)
        cold = compute_risk_score("P3", "low", 0.4, time_to_event_seconds=300)
        self.assertGreater(hot, cold)

    def test_sooner_is_more_urgent(self):
        self.assertGreater(time_urgency(5), time_urgency(300))
        self.assertEqual(time_urgency(None), 0.5)

    def test_score_in_unit_range(self):
        self.assertLessEqual(compute_risk_score("P0", "high", 1.0, time_to_event_seconds=0), 1.0)
        self.assertGreaterEqual(compute_risk_score("P3", "low", 0.0, time_to_event_seconds=600), 0.0)

    def test_confidence_monotonic(self):
        low = compute_risk_score("P2", "medium", 0.3, time_to_event_seconds=60)
        high = compute_risk_score("P2", "medium", 0.9, time_to_event_seconds=60)
        self.assertGreater(high, low)


class RiskBoardRankingTest(unittest.TestCase):
    def test_board_sorts_by_risk_score(self):
        scenario = Scenario(
            scenario_id="s",
            title="t",
            description="d",
            clip_path="c.mp4",
            camera_ids=["cam"],
            zone_id="z",
            expected_event_class="x",
        )
        state = RunState(scenario=scenario)
        low = Risk(risk_type="minor", severity="P3", zone_id="z", risk_score=0.1)
        high = Risk(risk_type="major", severity="P1", zone_id="z", risk_score=0.8)
        state.risks = [low, high]

        board = ToolRegistry(data_sources={}).generate_live_risk_board(state, {})

        self.assertEqual(board["risks"][0]["risk_type"], "major")
        self.assertEqual(board["risks"][1]["risk_type"], "minor")


if __name__ == "__main__":
    unittest.main()
