import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_PATH = REPO_ROOT / "scripts" / "eval.py"


def _load_eval_module():
    spec = importlib.util.spec_from_file_location("ops_guardian_eval", EVAL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvalHarnessTest(unittest.TestCase):
    def test_all_mock_scenarios_meet_labels(self):
        eval_module = _load_eval_module()
        results = eval_module.run_eval()

        self.assertEqual(
            results["passing"],
            results["total"],
            msg=f"Failing scenarios: {[r for r in results['per_scenario'] if not r.get('pass')]}",
        )
        self.assertTrue(results["all_pass"])
        # No spurious emergency escalations.
        self.assertEqual(results["escalation_precision"], 1.0)
        self.assertEqual(results["escalation_recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
