import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ops_guardian.app import create_app
from ops_guardian.config import Settings
from ops_guardian.model_adapters import MockScenarioAdapter


class ScenarioApiTest(unittest.TestCase):
    def make_client(self):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        settings = Settings(
            data_dir=Path("data"),
            database_url=f"sqlite:///{Path(tempdir.name) / 'ops_guardian_test.db'}",
            model_provider="mock",
            vision_model="mock-vision",
            planner_model="mock-planner",
        )
        return TestClient(create_app(settings=settings, adapter=MockScenarioAdapter()))

    def complete_scenario(self, client: TestClient, scenario_id: str) -> dict:
        created = client.post("/api/runs", json={"scenario_id": scenario_id})
        self.assertEqual(created.status_code, 200, created.text)
        run_id = created.json()["run_id"]
        completed = client.post(f"/api/runs/{run_id}/complete")
        self.assertEqual(completed.status_code, 200, completed.text)
        return completed.json()

    def test_safety_scenario_records_warning_and_recheck(self):
        client = self.make_client()
        run = self.complete_scenario(client, "safety_forklift_near_miss")

        self.assertEqual(run["status"], "completed")
        self.assertTrue(any(risk["severity"] == "P2" for risk in run["risks"]))
        self.assertTrue(any(call["tool_name"] == "activate_warning_beacon" for call in run["tool_calls"]))
        self.assertTrue(any(call["tool_name"] == "verify_risk_reduced" for call in run["tool_calls"]))

    def test_operations_scenario_queries_mes_and_cmms(self):
        client = self.make_client()
        run = self.complete_scenario(client, "operations_conveyor_jam")

        tool_names = {call["tool_name"] for call in run["tool_calls"]}
        self.assertIn("query_mes", tool_names)
        self.assertIn("query_cmms", tool_names)
        self.assertTrue(any(action["owner_role"] == "maintenance_tech" for action in run["actions"]))

    def test_quality_scenario_creates_hold(self):
        client = self.make_client()
        run = self.complete_scenario(client, "quality_missing_insert")

        self.assertTrue(any(action["action_type"] == "hold" for action in run["actions"]))
        self.assertTrue(any(call["tool_name"] == "create_quality_hold" for call in run["tool_calls"]))

    def test_medical_scenario_creates_mock_ems_payload(self):
        client = self.make_client()
        run = self.complete_scenario(client, "medical_worker_collapse")

        self.assertTrue(any(incident["emergency_type"] == "medical" for incident in run["incidents"]))
        emergency_actions = [action for action in run["actions"] if action["action_type"] == "emergency_call"]
        self.assertTrue(emergency_actions)
        self.assertTrue(emergency_actions[-1]["payload"]["mock"])
        self.assertEqual(emergency_actions[-1]["payload"]["responder"], "EMS")

    def test_security_scenario_uses_mock_police_path(self):
        client = self.make_client()
        run = self.complete_scenario(client, "security_forced_entry")

        self.assertTrue(any(incident["emergency_type"] == "security" for incident in run["incidents"]))
        self.assertTrue(any(call["tool_name"] == "call_police" for call in run["tool_calls"]))
        self.assertTrue(any(action["payload"].get("responder") == "POLICE" for action in run["actions"]))

    def test_adaptability_scenario_retrieves_updated_sop(self):
        client = self.make_client()
        run = self.complete_scenario(client, "adaptability_sop_swap")

        self.assertTrue(
            any(
                call["tool_name"] == "retrieve_sop"
                and call["arguments"].get("process_name") == "traffic_sop_v2_cold_chain"
                for call in run["tool_calls"]
            )
        )
        self.assertTrue(any("cold_chain" in policy for risk in run["risks"] for policy in risk["applicable_policy_ids"]))


if __name__ == "__main__":
    unittest.main()
