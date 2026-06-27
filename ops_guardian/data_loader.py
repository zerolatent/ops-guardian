from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Scenario


class DemoData:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def read_json(self, relative_path: str, default: Any | None = None) -> Any:
        path = self.data_dir / relative_path
        if not path.exists():
            if default is not None:
                return default
            raise FileNotFoundError(f"Missing demo data file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def read_text(self, relative_path: str) -> str:
        path = self.data_dir / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Missing demo text file: {path}")
        return path.read_text(encoding="utf-8")

    def scenarios(self) -> list[Scenario]:
        raw = self.read_json("scenarios.json", default=[])
        return [Scenario.model_validate(item) for item in raw]

    def scenario(self, scenario_id: str) -> Scenario:
        for scenario in self.scenarios():
            if scenario.scenario_id == scenario_id:
                return scenario
        raise KeyError(f"Unknown scenario_id: {scenario_id}")

    def all_context(self) -> dict[str, Any]:
        return {
            "site_map": self.read_json("site_map.json", default={}),
            "wms": self.read_json("wms_orders.json", default={}),
            "mes": self.read_json("mes_events.json", default={}),
            "cmms": self.read_json("cmms_assets.json", default={}),
            "access_control": self.read_json("access_control_log.json", default={}),
            "emergency_policy": self.read_json("emergency_policy.json", default={}),
            "security_policy": self.read_json("security_policy.json", default={}),
            "sops": self.load_sops(),
        }

    def load_sops(self) -> dict[str, str]:
        sops_dir = self.data_dir / "sops"
        if not sops_dir.exists():
            return {}
        return {path.stem: path.read_text(encoding="utf-8") for path in sorted(sops_dir.glob("*.md"))}
