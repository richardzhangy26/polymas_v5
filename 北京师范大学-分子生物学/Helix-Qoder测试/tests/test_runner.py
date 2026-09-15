import importlib.util
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "run_tests.py"


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RUNNER.exists(), "缺少测试运行器")
        spec = importlib.util.spec_from_file_location("helix_test_runner", RUNNER)
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)

    def test_auth_error_is_not_success(self):
        raw = '{"type":"result","subtype":"success","is_error":true,"result":"Not logged in"}'
        self.assertFalse(self.runner.parse_trace(raw, 1)["completed"])

    def test_missing_final_is_incomplete(self):
        raw = '{"type":"assistant","message":{"content":[{"type":"text","text":"开始检索"}]}}'
        self.assertFalse(self.runner.parse_trace(raw, 0)["completed"])

    def test_execution_error_message_is_preserved(self):
        raw = '{"type":"result","is_error":true,"errors":["Connection interrupted"]}'
        self.assertEqual(self.runner.parse_trace(raw, 1)["errors"], ["Connection interrupted"])

    def test_tool_trace_is_preserved(self):
        raw = '\n'.join([
            '{"type":"system","subtype":"init","tools":["Read","Skill"],"skills":["bioinfo-db-search"]}',
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"bioinfo-db-search"}}]}}',
            '{"type":"result","is_error":false,"result":"待确认物种"}'
        ])
        result = self.runner.parse_trace(raw, 0)
        self.assertTrue(result["completed"])
        self.assertEqual(result["tool_calls"][0]["name"], "Skill")
        self.assertEqual(result["answer"], "待确认物种")

    def test_forbidden_tool_fails_environment_check(self):
        raw = '{"type":"system","subtype":"init","tools":["Read","Bash"],"skills":["bioinfo-db-search"]}'
        result = self.runner.parse_trace(raw, 0)
        self.assertEqual(result["unexpected_tools"], ["Bash"])


if __name__ == "__main__":
    unittest.main()
