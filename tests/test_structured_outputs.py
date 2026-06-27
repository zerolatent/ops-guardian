import asyncio
import unittest

from ops_guardian.config import Settings
from ops_guardian.model_adapters import ModelAdapterError, OpenAICompatibleAdapter
from ops_guardian.models import SceneObservation
from ops_guardian.schemas import PlanResponse
from ops_guardian.tools import ToolRegistry


def _choice(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


class SchemaValidationRetryAdapter(OpenAICompatibleAdapter):
    """First plan response is missing the required `severity`; second is valid."""

    def __init__(self):
        super().__init__(
            Settings(
                model_provider="openai",
                openai_api_key="k",
                vision_model="v",
                planner_model="p",
                max_model_retries=2,
            )
        )
        self.calls = 0
        self.last_prompt_had_feedback = False

    async def _chat_completions_request(self, model, prompt, images=None, image_mime="image/jpeg"):
        self.calls += 1
        if self.calls == 1:
            return _choice('{"summary":"x","risks":[{"risk_type":"forklift_pedestrian_conflict"}],"tool_calls":[]}')
        self.last_prompt_had_feedback = "previous_error" in prompt
        return _choice(
            '{"summary":"ok","risks":[{"risk_type":"forklift_pedestrian_conflict","severity":"P2",'
            '"confidence":0.8}],"tool_calls":[{"tool_name":"notify_shift_lead","arguments":{}}]}'
        )


class StructuredOutputTest(unittest.TestCase):
    def _observation(self) -> SceneObservation:
        return SceneObservation(scenario_id="safety_forklift_near_miss", step_index=0)

    def _context(self) -> dict:
        return {
            "scenario": {"scenario_id": "safety_forklift_near_miss", "zone_id": "dock_intersection_a", "camera_ids": ["CAM"]},
            "step_index": 0,
        }

    def test_invalid_plan_triggers_validated_retry(self):
        adapter = SchemaValidationRetryAdapter()
        decision = asyncio.run(
            adapter.plan_next_action(self._observation(), [], ToolRegistry({}).available_tools, self._context())
        )

        self.assertEqual(adapter.calls, 2)  # first failed validation, second passed
        self.assertTrue(adapter.last_prompt_had_feedback)  # the error was fed back
        self.assertEqual(decision.summary, "ok")
        self.assertEqual(len(decision.risks), 1)
        self.assertEqual(decision.risks[0].severity, "P2")
        self.assertEqual(decision.tool_calls[0].tool_name, "notify_shift_lead")

    def test_schema_fills_defaults_and_coerces(self):
        validated = PlanResponse.model_validate(
            {"risks": [{"risk_type": "x", "severity": "P1"}]}
        ).model_dump(mode="python")
        self.assertEqual(validated["summary"], "No summary returned by planner.")
        self.assertEqual(validated["risks"][0]["probability"], "medium")
        self.assertEqual(validated["risks"][0]["confidence"], 0.7)

    def test_unsatisfiable_schema_raises_after_retries(self):
        class AlwaysInvalidAdapter(SchemaValidationRetryAdapter):
            async def _chat_completions_request(self, model, prompt, images=None, image_mime="image/jpeg"):
                self.calls += 1
                return _choice('{"risks":[{"risk_type":"x"}]}')  # never has severity

        adapter = AlwaysInvalidAdapter()
        with self.assertRaises(ModelAdapterError):
            asyncio.run(
                adapter.plan_next_action(self._observation(), [], ToolRegistry({}).available_tools, self._context())
            )


if __name__ == "__main__":
    unittest.main()
