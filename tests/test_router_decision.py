import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if "tools.agent_cli" not in sys.modules:
    agent_cli_stub = types.ModuleType("tools.agent_cli")
    agent_cli_stub.load_config = lambda *_args, **_kwargs: {}
    agent_cli_stub.parse_plan_from_answer = lambda *_args, **_kwargs: {}
    agent_cli_stub.run_requirement_query = lambda *_args, **_kwargs: {"answer": ""}
    sys.modules["tools.agent_cli"] = agent_cli_stub

import tools.agent_server as agent_server


class RouterDecisionTests(unittest.TestCase):
    def test_route_high_risk_prefers_process_expert(self):
        payload = {
            "requirement": "发布关键流程",
            "constraints": {"safety_level": "high", "budget": {"max_cost_usd": 10, "max_steps": 10}},
            "context": {"domain": "address_governance", "data_sources": ["a", "b"]},
        }
        task_spec = agent_server._make_task_spec_from_payload(payload)
        decision = agent_server._route_request(payload, task_spec)
        self.assertEqual(decision["route_mode"], "risk_first")
        self.assertEqual(decision["preferred_agent"], "process_expert")

    def test_route_low_cost_prefers_planner(self):
        payload = {
            "task_spec": {"task_id": "task_ut_route", "goal": "低成本执行", "context": {"domain": "address_governance"}},
            "constraints": {"safety_level": "medium", "budget": {"max_cost_usd": 1.5, "max_steps": 4}},
        }
        decision = agent_server._route_request(payload, payload["task_spec"])
        self.assertEqual(decision["route_mode"], "cost_guarded")
        self.assertIn(decision["preferred_agent"], {"planner", "executor", "process_expert"})


if __name__ == "__main__":
    unittest.main()
