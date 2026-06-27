import asyncio
import tempfile
import unittest
from pathlib import Path

from ops_guardian.config import Settings
from ops_guardian.data_loader import DemoData
from ops_guardian.model_adapters import MockScenarioAdapter
from ops_guardian.models import CreateRunRequest
from ops_guardian.runner import ScenarioRunner
from ops_guardian.storage import Storage


def _runner(tmp: str) -> ScenarioRunner:
    s = Settings(data_dir=Path("data"), database_url=f"sqlite:///{Path(tmp)/'t.db'}", model_provider="mock")
    return ScenarioRunner(s, Storage(s.sqlite_path), DemoData(s.data_dir), MockScenarioAdapter())


class StepTraceTest(unittest.TestCase):
    def test_create_run_request_accepts_mode(self):
        self.assertEqual(CreateRunRequest(scenario_id="x").mode, "demo")
        self.assertEqual(CreateRunRequest(scenario_id="x", mode="hybrid").mode, "hybrid")

    def test_demo_run_captures_step_traces(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            st = runner.start_run(CreateRunRequest(scenario_id="medical_worker_collapse"))
            self.assertEqual(st.mode, "demo")
            fin = asyncio.run(runner.complete_run(st.run_id))

            self.assertEqual(len(fin.traces), fin.scenario.max_steps)
            t = fin.traces[0]
            # what's passed to the VLM is reconstructed faithfully
            self.assertIn("frames_attached", t.vlm_input)
            self.assertIn("output_schema", t.vlm_input)
            self.assertEqual(t.camera_id, "CAM-DOCK-03")
            # the VLM's read + the agent's reasoning are persisted
            self.assertEqual(t.vlm_observation.get("posture"), ["worker down"])
            self.assertTrue(t.agent_summary)
            # demo mode: perception is off, so no detections / annotated frame
            self.assertEqual(t.mode, "demo")
            self.assertEqual(t.detections, [])
            self.assertIsNone(t.annotated_frame_b64)


if __name__ == "__main__":
    unittest.main()
