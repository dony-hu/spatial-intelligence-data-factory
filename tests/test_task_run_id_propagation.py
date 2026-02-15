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
from src.agents.executor_adapter import ExecutorAdapter


class _DummyRuntimeStore:
    def get_released_process(self, _process_code):
        return {"process_definition_id": "procdef_ut", "process_version_id": "procver_ut"}

    def create_task_run(self, **_kwargs):
        return "trun_ut_001"

    def add_task_input(self, **_kwargs):
        return "in_ut_001"

    def add_step_run(self, **_kwargs):
        return "srun_ut_001"

    def add_output_json(self, **_kwargs):
        return "out_ut_001"

    def update_task_run(self, **_kwargs):
        return None


class _DummyPlannerAdapter:
    def plan(self, task_spec):
        return {"plan_id": "plan_ut", "steps": []}, {"items": []}

    def build_changeset(self, task_spec, plan, approval_pack):
        return {"changeset_id": "cs_ut", "operations": [], "requires_approvals": []}

    def plan_from_strategy_patch(self, _strategy_patch):
        return []


class _DummyExecutorAdapter:
    def __init__(self):
        self.captured_task_specs = []

    def execute(self, task_spec, _changeset, approvals=None):
        self.captured_task_specs.append(task_spec)
        return {
            "status": "PASS",
            "workflow_result": {
                "stages": {
                    "task_executions": {
                        "unverifiable_online_list": [],
                        "strategy_patch": [],
                    }
                }
            },
        }


class _DummyEvaluatorAdapter:
    def evaluate(self, task_spec, changeset, execution_result):
        return {"status": "PASS", "checks": []}


class TaskRunIdPropagationTests(unittest.TestCase):
    def test_orchestrated_workflow_passes_task_run_id_into_executor_context(self):
        dummy_runtime = _DummyRuntimeStore()
        dummy_planner = _DummyPlannerAdapter()
        dummy_executor = _DummyExecutorAdapter()
        dummy_evaluator = _DummyEvaluatorAdapter()
        payload = {
            "task_spec": {
                "task_id": "task_tc_task_run_id",
                "goal": "task_run_id propagation",
                "context": {"domain": "address_governance"},
                "constraints": {"budget": {"max_steps": 2, "max_cost_usd": 5}},
            },
            "max_rounds": 1,
        }
        with patch.object(agent_server, "runtime_store", dummy_runtime), patch.object(
            agent_server, "planner_adapter", dummy_planner
        ), patch.object(agent_server, "executor_adapter", dummy_executor), patch.object(
            agent_server, "evaluator_adapter", dummy_evaluator
        ):
            result = agent_server._run_orchestrated_workflow(payload)
        self.assertEqual(result["task_run_id"], "trun_ut_001")
        self.assertEqual(dummy_executor.captured_task_specs[0]["context"]["task_run_id"], "trun_ut_001")

    def test_executor_verification_injects_task_run_id_into_verifier_input(self):
        adapter = ExecutorAdapter(runtime_store=None)
        workflow_result = {
            "stages": {
                "task_executions": {
                    "cleaning_case_details": [
                        {
                            "source_id": "src_1",
                            "input_item": {"id": 1, "raw": "test address"},
                            "output": {"standardized_address": "test address", "components": {"city": "x"}},
                        }
                    ]
                }
            }
        }
        captured = {}

        def _fake_verify(record_id, input_item, cleaning_output, policy_overrides):
            captured["task_run_id"] = input_item.get("task_run_id")
            return {
                "record_id": record_id,
                "verification_status": "VERIFIED_EXISTS",
                "reason_codes": [],
            }

        with patch.object(adapter.verifier, "verify", side_effect=_fake_verify):
            out = adapter._run_address_verification(workflow_result=workflow_result, task_run_id="trun_ut_002")
        self.assertEqual(captured["task_run_id"], "trun_ut_002")
        self.assertEqual(out["summary"]["task_run_id"], "trun_ut_002")


if __name__ == "__main__":
    unittest.main()
