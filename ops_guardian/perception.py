"""Deterministic perception layer (YOLO detect + pose).

Produces structured, measured facts (object counts, posture, motionless fraction)
that the VLM reasons over instead of guessing. Optional and gracefully degrading:
if disabled, the clip is missing, or ultralytics/opencv are not installed, it
returns {"available": False, "reason": ...} and the rest of the system runs
unchanged.

The result dict is attached to FrameWindow.perception, which already flows into
the vision prompt via FrameWindow.model_dump — so no adapter change is required.
"""
from __future__ import annotations

import base64
import math
from pathlib import Path
from typing import Any

# COCO has no "forklift" class; these are the closest vehicle proxies.
VEHICLE_CLASSES = {"truck", "car", "bus", "motorcycle", "train"}
# Stillness is measured by frame-to-frame pixel change inside the person's bounding box
# (mean absolute difference, 0..1). This is robust to YOLO keypoint jitter, which
# dominates a centroid metric on horizontal/prone poses and falsely reads as motion.
STILL_PIXEL_THRESHOLD = 0.04
CROP_SIZE = 64


def _torso_angle(keypoints: list[list[float]]) -> tuple[float | None, tuple[float, float] | None]:
    """Angle of the shoulder->hip torso line vs. horizontal (~90 upright, ~0 lying)."""
    needed = {5, 6, 11, 12}  # COCO: shoulders (5,6), hips (11,12)
    if any(keypoints[j][2] < 0.3 for j in needed):
        return None, None
    sh = ((keypoints[5][0] + keypoints[6][0]) / 2, (keypoints[5][1] + keypoints[6][1]) / 2)
    hp = ((keypoints[11][0] + keypoints[12][0]) / 2, (keypoints[11][1] + keypoints[12][1]) / 2)
    dx = abs(sh[0] - hp[0])
    dy = abs(hp[1] - sh[1])
    angle = math.degrees(math.atan2(dy, dx))
    centroid = ((sh[0] + hp[0]) / 2, (sh[1] + hp[1]) / 2)
    return angle, centroid


def _bbox_crop(frame, box):
    """Normalized grayscale crop of the person bbox, for frame-to-frame diffing."""
    import cv2  # available: only called inside Perceptor.analyze after import succeeds

    x1, y1, x2, y2 = (int(max(v, 0)) for v in box)
    if x2 <= x1 or y2 <= y1:
        return None
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (CROP_SIZE, CROP_SIZE))


class Perceptor:
    def __init__(
        self,
        enabled: bool = False,
        detector_model: str = "models/yolo11n.pt",
        pose_model: str = "models/yolo11n-pose.pt",
        sample_frames: int = 8,
    ):
        self.enabled = enabled
        self.detector_model_path = detector_model
        self.pose_model_path = pose_model
        self.sample_frames = max(2, sample_frames)
        self._detector = None
        self._pose = None

    def analyze(self, frame_window, scenario: Any | None = None, capture_trace: bool = False) -> dict[str, Any]:
        if not self.enabled:
            return {"available": False, "reason": "perception_disabled"}
        clip = Path(frame_window.clip_path)
        if not clip.exists():
            return {"available": False, "reason": "clip_missing"}
        try:
            import cv2  # type: ignore
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on optional extras
            return {"available": False, "reason": f"deps_missing: {exc}"}

        if self._detector is None:
            self._detector = YOLO(self.detector_model_path)
        if self._pose is None:
            self._pose = YOLO(self.pose_model_path)

        cap = cv2.VideoCapture(str(clip))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        start_f = int(frame_window.start_seconds * fps)
        end_f = int(frame_window.end_seconds * fps)
        if total:
            start_f = min(start_f, max(total - 1, 0))
            end_f = min(end_f, max(total - 1, 0))
        if end_f <= start_f:
            end_f = start_f + 1
        step = max(1, (end_f - start_f) // self.sample_frames)

        class_counts: dict[str, int] = {}
        person_max = 0
        vehicle_max = 0
        angles: list[float] = []
        frames_buf: list[Any] = []
        boxes_buf: list[Any] = []
        det_results: list[Any] = []
        pose_results: list[Any] = []
        analyzed = 0

        for fi in range(start_f, end_f + 1, step):
            if total and fi >= total:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ok, frame = cap.read()
            if not ok:
                continue
            analyzed += 1

            det = self._detector(frame, verbose=False)[0]
            det_results.append(det)
            frame_counts: dict[str, int] = {}
            for box in det.boxes:
                name = det.names[int(box.cls)]
                frame_counts[name] = frame_counts.get(name, 0) + 1
            for name, count in frame_counts.items():
                class_counts[name] = max(class_counts.get(name, 0), count)
            person_max = max(person_max, frame_counts.get("person", 0))
            vehicle_max = max(vehicle_max, sum(c for n, c in frame_counts.items() if n in VEHICLE_CLASSES))

            frames_buf.append(frame)
            pose = self._pose(frame, verbose=False)[0]
            pose_results.append(pose)
            if pose.keypoints is not None and pose.boxes is not None and len(pose.boxes) > 0:
                confs = pose.boxes.conf.tolist()
                best = max(range(len(confs)), key=lambda k: confs[k])
                kp = pose.keypoints.data[best].tolist()
                angle, _centroid = _torso_angle(kp)
                if angle is not None:
                    angles.append(angle)
                boxes_buf.append(pose.boxes.xyxy[best].tolist())
            else:
                boxes_buf.append(None)

        cap.release()

        # Motionless fraction from frame-to-frame pixel change inside a STABLE crop region
        # (the union of detected person boxes). A fixed region avoids the bbox-jitter that
        # otherwise reads as motion even when the person is lying still.
        motionless_fraction = 0.0
        boxes = [b for b in boxes_buf if b is not None]
        if len(frames_buf) >= 2 and boxes:
            region = [
                min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes),
            ]
            crops = [c for c in (_bbox_crop(f, region) for f in frames_buf) if c is not None]
            intervals = 0
            still = 0
            for c0, c1 in zip(crops, crops[1:]):
                intervals += 1
                diff = float(cv2.absdiff(c1, c0).mean()) / 255.0
                if diff < STILL_PIXEL_THRESHOLD:
                    still += 1
            motionless_fraction = (still / intervals) if intervals else 0.0
        window_seconds = max(frame_window.end_seconds - frame_window.start_seconds, 0)
        median_angle = sorted(angles)[len(angles) // 2] if angles else None
        if median_angle is None:
            state = "unknown"
        elif median_angle < 45:
            state = "prone"
        else:
            state = "upright"

        result = {
            "available": True,
            "frames_analyzed": analyzed,
            "window_seconds": window_seconds,
            "detections": class_counts,
            "person_count": person_max,
            "vehicle_count": vehicle_max,
            "pose": {
                "state": state,
                "torso_angle_deg": round(median_angle, 1) if median_angle is not None else None,
                "motionless_fraction": round(motionless_fraction, 2),
                "motionless_seconds_window": round(motionless_fraction * window_seconds, 1),
            },
        }
        if capture_trace and frames_buf:
            result["trace"] = self._build_trace(cv2, frames_buf, det_results, pose_results)
        return result

    def _build_trace(self, cv2, frames_buf, det_results, pose_results) -> dict[str, Any]:
        """Per-step trace: detection list + an annotated keyframe (boxes + pose skeleton)."""
        mid = len(frames_buf) // 2
        trace: dict[str, Any] = {"detections": [], "annotated_frame_b64": None}
        try:
            det = det_results[mid]
            for b in det.boxes:
                trace["detections"].append({
                    "cls": det.names[int(b.cls)],
                    "conf": round(float(b.conf), 2),
                    "bbox": [round(float(v), 1) for v in b.xyxy[0].tolist()],
                })
        except Exception:
            pass
        try:
            annotated = pose_results[mid].plot()  # BGR ndarray: person boxes + skeleton
            ok, buf = cv2.imencode(".jpg", annotated)
            if ok:
                trace["annotated_frame_b64"] = base64.b64encode(buf.tobytes()).decode("ascii")
        except Exception:
            pass
        return trace
