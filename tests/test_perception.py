import unittest

from ops_guardian.models import FrameWindow
from ops_guardian.perception import Perceptor


def make_window(clip_path: str = "data/videos/missing.mp4") -> FrameWindow:
    return FrameWindow(camera_id="CAM", clip_path=clip_path, start_seconds=0, end_seconds=5)


class PerceptorTest(unittest.TestCase):
    def test_disabled_returns_unavailable(self):
        result = Perceptor(enabled=False).analyze(make_window())
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "perception_disabled")

    def test_missing_clip_returns_unavailable(self):
        result = Perceptor(enabled=True).analyze(make_window("data/videos/does_not_exist.mp4"))
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "clip_missing")

    def test_perception_rides_into_vision_prompt_dump(self):
        # The vision prompt uses model_dump(exclude={"images_base64"}); perception must survive that.
        fw = make_window()
        fw.perception = {"available": True, "person_count": 1, "pose": {"state": "prone"}}
        dumped = fw.model_dump(mode="json", exclude={"images_base64"})
        self.assertIn("perception", dumped)
        self.assertEqual(dumped["perception"]["pose"]["state"], "prone")


if __name__ == "__main__":
    unittest.main()
