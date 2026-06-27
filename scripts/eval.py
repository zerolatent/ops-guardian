"""Evaluation harness: run every scenario and score output against ground-truth labels.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python scripts/eval.py

Exits 0 if every scenario passes its label checks, 1 otherwise.
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from ops_guardian.config import Settings
from ops_guardian.data_loader import DemoData
from ops_guardian.model_adapters import MockScenarioAdapter
from ops_guardian.models import CreateRunRequest
from ops_guardian.runner import ScenarioRunner
from ops_guardian.storage import Storage

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LABELS_PATH = DATA_DIR / "eval_labels.json"

SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _most_severe(severities: list[str]) -> str | None:
    if not severities:
        return None
    return min(severities, key=lambda s: SEVERITY_RANK.get(s, 99))


def run_eval() -> dict:
    """Run all scenarios with the mock adapter and score them. Returns a results dict."""
    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "eval.db"
        settings = Settings(
            data_dir=DATA_DIR,
            database_url=f"sqlite:///{db_path}",
            model_provider="mock",
        )
        demo_data = DemoData(settings.data_dir)
        storage = Storage(settings.sqlite_path)
        runner = ScenarioRunner(settings, storage, demo_data, MockScenarioAdapter())

        scenarios = {s.scenario_id for s in demo_data.scenarios()}
        per_scenario = []
        for scenario_id, label in labels.items():
            if scenario_id not in scenarios:
                per_scenario.append({"scenario": scenario_id, "error": "unknown scenario", "pass": False})
                continue

            state = runner.start_run(CreateRunRequest(scenario_id=scenario_id))
            final = asyncio.run(runner.complete_run(state.run_id))

            severities = [r.severity for r in final.risks]
            produced_max = _most_severe(severities)
            executed_tools = {c.tool_name for c in final.tool_calls if c.status == "completed"}
            emergency_dispatched = any(a.action_type == "emergency_call" for a in final.actions)
            incident_opened = len(final.incidents) > 0

            severity_ok = produced_max == label["expected_max_severity"]
            if label["expect_emergency"]:
                escalation_ok = emergency_dispatched and incident_opened
            else:
                escalation_ok = (not emergency_dispatched) and (not incident_opened)
            missing_tools = [t for t in label["expect_tools_include"] if t not in executed_tools]
            tools_ok = not missing_tools

            passed = severity_ok and escalation_ok and tools_ok
            per_scenario.append({
                "scenario": scenario_id,
                "expect_emergency": label["expect_emergency"],
                "emergency_dispatched": emergency_dispatched,
                "produced_max_severity": produced_max,
                "expected_max_severity": label["expected_max_severity"],
                "severity_ok": severity_ok,
                "escalation_ok": escalation_ok,
                "tools_ok": tools_ok,
                "missing_tools": missing_tools,
                "pass": passed,
            })

    # escalation precision / recall across scenarios
    tp = sum(1 for r in per_scenario if r.get("expect_emergency") and r.get("emergency_dispatched"))
    fp = sum(1 for r in per_scenario if not r.get("expect_emergency") and r.get("emergency_dispatched"))
    fn = sum(1 for r in per_scenario if r.get("expect_emergency") and not r.get("emergency_dispatched"))
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    total = len(per_scenario)
    passing = sum(1 for r in per_scenario if r.get("pass"))
    return {
        "per_scenario": per_scenario,
        "total": total,
        "passing": passing,
        "all_pass": passing == total,
        "escalation_precision": precision,
        "escalation_recall": recall,
    }


def main() -> int:
    results = run_eval()
    print("=" * 78)
    print("LINE GUARDIAN — EVAL SCORECARD (mock adapter vs. ground-truth labels)")
    print("=" * 78)
    header = f"{'scenario':30s} {'sev':>4s} {'esc':>4s} {'tools':>6s}  result"
    print(header)
    print("-" * 78)
    for r in results["per_scenario"]:
        if "error" in r:
            print(f"{r['scenario']:30s}  ERROR: {r['error']}")
            continue
        sev = "ok" if r["severity_ok"] else "X"
        esc = "ok" if r["escalation_ok"] else "X"
        tools = "ok" if r["tools_ok"] else "X"
        verdict = "PASS" if r["pass"] else "FAIL"
        line = f"{r['scenario']:30s} {sev:>4s} {esc:>4s} {tools:>6s}  {verdict}"
        if r["missing_tools"]:
            line += f"  missing={r['missing_tools']}"
        if not r["severity_ok"]:
            line += f"  sev={r['produced_max_severity']}!={r['expected_max_severity']}"
        print(line)
    print("-" * 78)
    print(
        f"passing: {results['passing']}/{results['total']}   "
        f"escalation precision={results['escalation_precision']:.2f}  "
        f"recall={results['escalation_recall']:.2f}"
    )
    print("RESULT:", "PASS" if results["all_pass"] else "FAIL")
    return 0 if results["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
