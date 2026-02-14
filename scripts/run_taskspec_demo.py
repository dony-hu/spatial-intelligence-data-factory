#!/usr/bin/env python3
"""Run end-to-end TaskSpec demo through new orchestrator + adapters."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.runtime.orchestrator import Orchestrator
from src.agents.planner_adapter import PlannerAdapter
from src.agents.executor_adapter import ExecutorAdapter
from src.agents.evaluator_adapter import EvaluatorAdapter
from scripts._mode_guard import ensure_demo_allowed


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ensure_demo_allowed("scripts/run_taskspec_demo.py")
    parser = argparse.ArgumentParser(description="Run TaskSpec e2e demo")
    parser.add_argument(
        "--mode",
        choices=["success", "fail_approval", "fail_gate"],
        default="success",
        help="Run mode for success or failure path reproduction",
    )
    args = parser.parse_args()

    task_path = PROJECT_ROOT / "schemas" / "agent" / "examples" / "task-spec.sample.json"
    task_spec = json.loads(task_path.read_text(encoding="utf-8"))
    task_id = f"{task_spec['task_id']}_{args.mode}"
    task_spec["task_id"] = task_id

    out_dir = PROJECT_ROOT / "output" / "agent_demo" / task_id
    out_dir.mkdir(parents=True, exist_ok=True)

    planner = PlannerAdapter()
    executor = ExecutorAdapter()
    evaluator = EvaluatorAdapter()
    orchestrator = Orchestrator()

    plan, approval_pack = planner.plan(task_spec)
    changeset = planner.build_changeset(task_spec, plan, approval_pack)

    orchestrator.submit(task_id, context=task_spec, approvals_required=changeset.get("requires_approvals", []))
    orchestrator.transition(task_id, "PLANNED")

    approvals = [item["type"] for item in approval_pack.get("items", []) if item.get("blocking", True)]

    if approvals:
        orchestrator.transition(task_id, "APPROVAL_PENDING")
        if args.mode != "fail_approval":
            for ap in approvals:
                orchestrator.grant_approval(task_id, ap, actor="demo-human-gate")

    approval_check = orchestrator.check_approvals(task_id)
    if not approval_check["pass"]:
        orchestrator.transition(task_id, "FAILED", metadata={"reason": "approval gate fail"})
        save_json(out_dir / "task_spec.json", task_spec)
        save_json(out_dir / "plan.json", plan)
        save_json(out_dir / "approval_pack.json", approval_pack)
        save_json(out_dir / "changeset.json", changeset)
        save_json(out_dir / "final_state.json", orchestrator.get(task_id))
        save_json(out_dir / "evidence.json", {"task_id": task_id, "records": orchestrator.evidence(task_id)})
        print(f"TaskSpec demo failed (approval): {out_dir}")
        return 1

    orchestrator.transition(task_id, "APPROVED")
    orchestrator.transition(task_id, "CHANGESET_READY")
    orchestrator.transition(task_id, "EXECUTING")
    if args.mode == "fail_gate":
        changeset["operations"][0]["idempotency_key"] = ""

    execution_result = executor.execute(task_spec, changeset, approvals)
    for gate in execution_result.get("gates", {}).get("checks", []):
        orchestrator.record_event(
            task_id=task_id,
            actor="evaluator",
            action="gate_check",
            artifact_ref=f"{task_id}#gate:{gate.get('name', 'unknown')}",
            result=str(gate.get("status", "UNKNOWN")).lower(),
            metadata={"details": gate.get("details", "")},
        )

    if execution_result.get("status") != "PASS":
        orchestrator.transition(task_id, "FAILED", metadata={"reason": "execution fail", "details": execution_result})
        final_state = orchestrator.get(task_id)
        save_json(out_dir / "final_state.json", final_state)
        save_json(out_dir / "execution_result.json", execution_result)
        save_json(out_dir / "evidence.json", {"task_id": task_id, "records": orchestrator.evidence(task_id)})
        print(f"TaskSpec demo failed (execution): {out_dir}")
        return 1

    orchestrator.transition(task_id, "EVALUATING")
    report = evaluator.evaluate(task_spec, changeset, execution_result)
    orchestrator.record_event(
        task_id=task_id,
        actor="evaluator",
        action="eval_report",
        artifact_ref=f"{task_id}#eval-report",
        result=report["status"].lower(),
        metadata={"checks": report.get("checks", [])},
    )

    if report["status"] == "PASS":
        orchestrator.transition(task_id, "COMPLETED")
    elif report["status"] == "NEEDS_HUMAN":
        orchestrator.transition(task_id, "NEEDS_HUMAN")
    else:
        orchestrator.transition(task_id, "FAILED", metadata={"reason": "eval fail", "report": report})

    save_json(out_dir / "task_spec.json", task_spec)
    save_json(out_dir / "plan.json", plan)
    save_json(out_dir / "approval_pack.json", approval_pack)
    save_json(out_dir / "changeset.json", changeset)
    save_json(out_dir / "execution_result.json", execution_result)
    save_json(out_dir / "eval_report.json", report)
    save_json(out_dir / "final_state.json", orchestrator.get(task_id))
    save_json(out_dir / "evidence.json", {"task_id": task_id, "records": orchestrator.evidence(task_id)})

    print(f"TaskSpec demo completed: {out_dir}")
    print(f"Final status: {report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
