from functools import lru_cache
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Line Guardian"
    data_dir: Path = Field(default=Path("data"))
    database_url: str = "sqlite:///./data/ops_guardian.db"
    model_provider: Literal["openai", "mock"] = "openai"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    vision_model: str | None = None
    planner_model: str | None = None
    p0_motionless_threshold_seconds: int = 15
    p0_confirmation_confidence: float = 0.75
    quality_hold_mode: str = "autonomous_for_high_confidence"
    safe_stop_mode: str = "simulated_request_only"
    frame_window_seconds: int = 5
    max_model_retries: int = 1
    max_tool_iterations: int = 4
    request_timeout_seconds: int = 60
    vlm_max_images: int = 3
    chat_max_tokens: int = 512
    chat_think: bool | None = None
    enable_perception: bool = False
    detector_model: str = "models/yolo11n.pt"
    pose_model: str = "models/yolo11n-pose.pt"

    @property
    def sqlite_path(self) -> Path:
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("Only sqlite:/// DATABASE_URL values are supported by the demo storage layer.")
        return Path(self.database_url.removeprefix("sqlite:///"))


@lru_cache
def get_settings() -> Settings:
    env = _load_dotenv(Path(".env")) | dict(os.environ)
    openai_base_url = env.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    chat_think = _optional_bool(env.get("CHAT_THINK"))
    if chat_think is None and "127.0.0.1:11434" in openai_base_url:
        chat_think = False
    return Settings(
        data_dir=Path(env.get("DATA_DIR", "data")),
        database_url=env.get("DATABASE_URL", "sqlite:///./data/ops_guardian.db"),
        model_provider=env.get("MODEL_PROVIDER", "openai"),
        openai_api_key=env.get("OPENAI_API_KEY"),
        openai_base_url=openai_base_url,
        vision_model=env.get("VISION_MODEL"),
        planner_model=env.get("PLANNER_MODEL"),
        p0_motionless_threshold_seconds=int(env.get("P0_MOTIONLESS_THRESHOLD_SECONDS", "15")),
        p0_confirmation_confidence=float(env.get("P0_CONFIRMATION_CONFIDENCE", "0.75")),
        quality_hold_mode=env.get("QUALITY_HOLD_MODE", "autonomous_for_high_confidence"),
        safe_stop_mode=env.get("SAFE_STOP_MODE", "simulated_request_only"),
        frame_window_seconds=int(env.get("FRAME_WINDOW_SECONDS", "5")),
        max_model_retries=int(env.get("MAX_MODEL_RETRIES", "1")),
        max_tool_iterations=int(env.get("MAX_TOOL_ITERATIONS", "4")),
        request_timeout_seconds=int(env.get("REQUEST_TIMEOUT_SECONDS", "60")),
        vlm_max_images=int(env.get("VLM_MAX_IMAGES", "3")),
        chat_max_tokens=int(env.get("CHAT_MAX_TOKENS", "512")),
        chat_think=chat_think,
        enable_perception=_optional_bool(env.get("ENABLE_PERCEPTION")) or False,
        detector_model=env.get("DETECTOR_MODEL", "models/yolo11n.pt"),
        pose_model=env.get("POSE_MODEL", "models/yolo11n-pose.pt"),
    )


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _optional_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")
