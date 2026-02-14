import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if "tools.agent_cli" not in sys.modules:
    agent_cli_stub = types.ModuleType("tools.agent_cli")
    agent_cli_stub.load_config = lambda *_args, **_kwargs: {}
    agent_cli_stub.parse_plan_from_answer = lambda *_args, **_kwargs: {}
    agent_cli_stub.run_requirement_query = lambda *_args, **_kwargs: {"answer": ""}
    sys.modules["tools.agent_cli"] = agent_cli_stub

import tools.agent_server as agent_server


class RouterBudgetGateTests(unittest.TestCase):
    def test_cost_estimation_helper(self):
        self.assertAlmostEqual(agent_server._estimate_cost_usd(1000.0), 0.01, places=6)

    def test_max_steps_gate_blocks_before_execution(self):
        payload = {
            "task_spec": {
                "task_id": "task_gate_ut",
                "goal": "gate test",
                "context": {"domain": "address_governance"},
                "constraints": {"budget": {"max_steps": 1, "max_cost_usd": 5}},
            },
            "max_rounds": 3,
        }
        result = agent_server._run_orchestrated_workflow(payload)
        self.assertEqual(result.get("status"), "error")
        self.assertIn("ROUTER_GATE_MAX_STEPS_EXCEEDED", str(result.get("error")))

    def test_gate_defaults_can_be_overridden_by_env(self):
        with patch.dict(
            "os.environ",
            {
                "FACTORY_GATE_MAX_STEPS": "2",
                "FACTORY_GATE_MAX_COST_USD": "3.5",
                "FACTORY_GATE_MAX_DURATION_SEC": "120",
                "FACTORY_GATE_COST_PER_1K_TOKENS_USD": "0.02",
            },
            clear=False,
        ):
            defaults = agent_server._load_router_gate_defaults()
        self.assertEqual(defaults["max_steps"], 2)
        self.assertAlmostEqual(defaults["max_cost_usd"], 3.5, places=6)
        self.assertEqual(defaults["max_duration_sec"], 120)
        self.assertAlmostEqual(defaults["cost_per_1k_tokens_usd"], 0.02, places=6)


if __name__ == "__main__":
    unittest.main()
