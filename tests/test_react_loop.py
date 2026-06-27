import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Any

from ops_guardian.config import Settings
from ops_guardian.data_loader import DemoData
from ops_guardian.model_adapters import ModelAdapter
from ops_guardian.models import AgentDecision, CreateRunRequest, FrameWindow, SceneObservation, ToolCall
from ops_guardian.runner import ScenarioRunner
from ops_guardian.storage import Storage

SCENARIO_ID = "safety_forklift_near_miss"


class TwoStepReActAdapter(ModelAdapter):
    """Returns done=False + one tool on the first call, done=True + a different
    tool on the second, so a single step_run drives two loop iterations."""

    def __init__(self):
        self.plan_calls = 0
        self.tool_results_seen: list[list[dict]] = []

    async def analyze_scene(self, frame_window: FrameWindow, context: dict[str, Any]) -> SceneObservation:
        return SceneObservation(
            scenario_id=context["scenario"]["scenario_id"],
            step_index=int(context["step_index"]),
        )

    async def plan_next_action(
        self,
        observation: SceneObservation,
        active_risks: list,
        available_tools: list[str],
        context: dict[str, Any],
        tool_results: list[dict] | None = None,
    ) -> AgentDecision:
        self.plan_calls += 1
        self.tool_results_seen.append(list(tool_results or []))
        if self.plan_calls == 1:
            return AgentDecision(
                summary="first",
                tool_calls=[ToolCall(tool_name="notify_shift_lead", arguments={"zone_id": "z", "message": "m"})],
                done=False,
            )
        return AgentDecision(
            summary="second",
            tool_calls=[ToolCall(tool_name="notify_safety_officer", arguments={"zone_id": "z", "message": "m"})],
            done=True,
        )


class NeverDoneAdapter(ModelAdapter):
    """Always done=False with a tool call, to exercise the max-iteration cap."""

    def __init__(self):
        self.plan_calls = 0

    async def analyze_scene(self, frame_window: FrameWindow, context: dict[str, Any]) -> SceneObservation:
        return SceneObservation(
            scenario_id=context["scenario"]["scenario_id"],
            step_index=int(context["step_index"]),
        )

    async def plan_next_action(
        self,
        observation: SceneObservation,
        active_risks: list,
        available_tools: list[str],
        context: dict[str, Any],
        tool_results: list[dict] | None = None,
    ) -> AgentDecision:
        self.plan_calls += 1
        return AgentDecision(
            summary="again",
            tool_calls=[ToolCall(tool_name="notify_shift_lead", arguments={"zone_id": "z", "message": "m"})],
            done=False,
        )


class ReActLoopTest(unittest.TestCase):
    def _runner(self, adapter: ModelAdapter, **overrides) -> ScenarioRunner:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        settings = Settings(
            data_dir=Path("data"),
            database_url=f"sqlite:///{Path(tempdir.name) / 'react_test.db'}",
            model_provider="mock",
            **overrides,
        )
        demo_data = DemoData(settings.data_dir)
        storage = Storage(settings.sqlite_path)
        return ScenarioRunner(settings, storage, demo_data, adapter)

    def test_loop_runs_until_done_executing_all_tools(self):
        adapter = TwoStepReActAdapter()
        runner = self._runner(adapter)
        state = runner.start_run(CreateRunRequest(scenario_id=SCENARIO_ID))
        state = asyncio.run(runner.step_run(state.run_id))

        # Two iterations: planner called twice, loop stopped on done=True.
        self.assertEqual(adapter.plan_calls, 2)
        executed = {c.tool_name for c in state.tool_calls if c.status == "completed"}
        self.assertIn("notify_shift_lead", executed)
        self.assertIn("notify_safety_officer", executed)
        # The second plan call saw the first tool's result fed back.
        self.assertEqual(adapter.tool_results_seen[0], [])
        self.assertEqual(len(adapter.tool_results_seen[1]), 1)
        self.assertEqual(adapter.tool_results_seen[1][0]["tool_name"], "notify_shift_lead")

    def test_loop_respects_max_tool_iterations(self):
        adapter = NeverDoneAdapter()
        runner = self._runner(adapter, max_tool_iterations=3)
        state = runner.start_run(CreateRunRequest(scenario_id=SCENARIO_ID))
        asyncio.run(runner.step_run(state.run_id))

        self.assertEqual(adapter.plan_calls, 3)


if __name__ == "__main__":
    unittest.main()
