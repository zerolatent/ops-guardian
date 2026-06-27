import unittest

from ops_guardian.tools import AuthorityGuard


class AuthorityGuardTest(unittest.TestCase):
    def test_emergency_calls_are_mock_only(self):
        allowed, policy = AuthorityGuard().check("call_police", {"zone_id": "restricted_cage_door"})

        self.assertTrue(allowed)
        self.assertEqual(policy, "allowed_mock_endpoint_only")

    def test_forbidden_worker_actions_are_blocked(self):
        allowed, policy = AuthorityGuard().check("discipline_worker", {"worker_id": "unknown"})

        self.assertFalse(allowed)
        self.assertEqual(policy, "blocked_by_non_goal")


if __name__ == "__main__":
    unittest.main()
