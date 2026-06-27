from __future__ import annotations

import base64
from pathlib import Path

from .models import FrameWindow, Scenario


class VideoSampler:
    def __init__(self, frame_window_seconds: int = 5):
        self.frame_window_seconds = frame_window_seconds

    def sample(self, scenario: Scenario, step_index: int) -> FrameWindow:
        start = step_index * self.frame_window_seconds
        end = start + self.frame_window_seconds
        camera_id = scenario.camera_ids[0] if scenario.camera_ids else "UNKNOWN-CAMERA"
        clip_path = scenario.clip_path
        path = Path(clip_path)

        if not path.exists():
            return FrameWindow(
                camera_id=camera_id,
                clip_path=clip_path,
                start_seconds=start,
                end_seconds=end,
                frames=[f"placeholder://{scenario.scenario_id}/{camera_id}/{start}-{end}"],
                available=False,
                note="Clip file not present; using structured placeholder frame window.",
            )

        try:
            import cv2  # type: ignore
        except ModuleNotFoundError:
            return FrameWindow(
                camera_id=camera_id,
                clip_path=clip_path,
                start_seconds=start,
                end_seconds=end,
                frames=[f"clip://{clip_path}#t={start},{end}"],
                available=True,
                note="OpenCV not installed; returning clip time window instead of extracted frames.",
            )

        capture = cv2.VideoCapture(str(path))
        fps = capture.get(cv2.CAP_PROP_FPS) or 1
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frame_numbers = [int(start * fps), int(((start + end) / 2) * fps), int(max(end * fps - 1, 0))]
        frames: list[str] = []
        images: list[str] = []
        for frame_number in frame_numbers:
            if total_frames and frame_number >= total_frames:
                continue
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = capture.read()
            if not ok:
                continue
            encoded, buffer = cv2.imencode(".jpg", frame)
            if not encoded:
                continue
            frames.append(f"clip://{clip_path}#frame={frame_number}")
            images.append(base64.b64encode(buffer.tobytes()).decode("ascii"))
        capture.release()
        if not frames:
            frames.append(f"clip://{clip_path}#t={start},{end}")
        return FrameWindow(
            camera_id=camera_id,
            clip_path=clip_path,
            start_seconds=start,
            end_seconds=end,
            frames=frames,
            images_base64=images,
            available=True,
        )
