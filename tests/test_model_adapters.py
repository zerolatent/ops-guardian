import asyncio
import unittest

from ops_guardian.config import Settings
from ops_guardian.model_adapters import ModelAdapterError, OpenAICompatibleAdapter
from ops_guardian.models import FrameWindow


class RetryingAdapter(OpenAICompatibleAdapter):
    def __init__(self):
        super().__init__(
            Settings(
                model_provider="openai",
                openai_api_key="test-key",
                vision_model="vision",
                planner_model="planner",
                max_model_retries=1,
            )
        )
        self.calls = 0

    async def _chat_completions_request(self, model: str, prompt: dict, images=None, image_mime="image/jpeg"):
        self.calls += 1
        if self.calls == 1:
            return {"choices": [{"message": {"content": "not json"}}]}
        return {
            "choices": [{"message": {"content": (
                '{"visible_entities":["forklift"],"movement":[],"posture":[],'
                '"hazards":[],"workflow_step":"dock","uncertainty":null,'
                '"evidence_descriptions":["forklift visible"]}'
            )}}]
        }


class CapturingAdapter(OpenAICompatibleAdapter):
    def __init__(self):
        super().__init__(
            Settings(
                model_provider="openai",
                openai_api_key="test-key",
                vision_model="vision",
                planner_model="planner",
                chat_max_tokens=512,
                chat_think=False,
            )
        )
        self.captured_payload = None

    async def _post_chat_completions(self, url: str, headers: dict, body: dict) -> dict:
        self.captured_payload = body
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"visible_entities":["red square"],"movement":[],"posture":[],'
                            '"hazards":[],"workflow_step":null,"uncertainty":null,'
                            '"evidence_descriptions":["red square visible"]}'
                        )
                    }
                }
            ]
        }


class ModelAdapterTest(unittest.TestCase):
    def test_missing_live_model_config_fails_clearly(self):
        adapter = OpenAICompatibleAdapter(Settings(model_provider="openai"))
        frame_window = FrameWindow(camera_id="CAM", clip_path="missing.mp4", start_seconds=0, end_seconds=5)

        with self.assertRaisesRegex(ModelAdapterError, "OPENAI_API_KEY"):
            asyncio.run(adapter.analyze_scene(frame_window, {"scenario": {"scenario_id": "x"}, "step_index": 0}))

    def test_malformed_json_retries(self):
        adapter = RetryingAdapter()
        frame_window = FrameWindow(camera_id="CAM", clip_path="missing.mp4", start_seconds=0, end_seconds=5)
        observation = asyncio.run(
            adapter.analyze_scene(frame_window, {"scenario": {"scenario_id": "x"}, "step_index": 0})
        )

        self.assertEqual(adapter.calls, 2)
        self.assertEqual(observation.visible_entities, ["forklift"])

    def test_chat_request_includes_gemma4_controls(self):
        adapter = CapturingAdapter()
        frame_window = FrameWindow(camera_id="CAM", clip_path="missing.mp4", start_seconds=0, end_seconds=5)
        asyncio.run(adapter.analyze_scene(frame_window, {"scenario": {"scenario_id": "x"}, "step_index": 0}))

        self.assertIsNotNone(adapter.captured_payload)
        self.assertEqual(adapter.captured_payload["max_tokens"], 512)
        self.assertIs(adapter.captured_payload["think"], False)


if __name__ == "__main__":
    unittest.main()
