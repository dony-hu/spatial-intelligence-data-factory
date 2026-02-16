import tempfile
import unittest
from pathlib import Path

from scripts.line_execution_tc06 import (
    collect_failed_replay_cases,
    load_failed_queue,
    replay_failed_queue,
    save_failed_queue,
    build_line_feedback_payload,
)


class Tc06LineExecutionTests(unittest.TestCase):
    def test_collect_failed_replay_cases_maps_raw_address(self):
        requirement_input = [
            {"id": "case-1", "raw": "中山东一路1号"},
            {"id": "case-2", "raw": "上海市浦东新区世纪大道100号"},
        ]
        workflow_result = {
            "stages": {
                "task_executions": {
                    "failed_cases": [
                        {"source_id": "case-1", "stage": "cleaning", "reason": "CLEANING_INVALID_OUTPUT"}
                    ]
                }
            }
        }

        failures = collect_failed_replay_cases(workflow_result, requirement_input)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["raw_address"], "中山东一路1号")
        self.assertEqual(failures[0]["stage"], "cleaning")

    def test_save_and_load_failed_queue(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            queue_path = Path(tmp_dir) / "failed_queue.json"
            items = [
                {"raw_address": "中山东一路1号", "stage": "cleaning", "reason": "CLEANING_INVALID_OUTPUT", "attempts": 0}
            ]
            save_failed_queue(queue_path, items)
            loaded = load_failed_queue(queue_path)
            self.assertEqual(loaded, items)

    def test_replay_failed_queue_removes_succeeded_items(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            queue_path = Path(tmp_dir) / "failed_queue.json"
            save_failed_queue(
                queue_path,
                [
                    {"raw_address": "中山东一路1号", "stage": "cleaning", "reason": "CLEANING_INVALID_OUTPUT", "attempts": 0},
                    {"raw_address": "上海市浦东新区世纪大道100号", "stage": "graph", "reason": "GRAPH_EMPTY_OUTPUT", "attempts": 0},
                ],
            )

            success_targets = {"上海市浦东新区世纪大道100号"}

            def fake_runner(raw_address: str):
                if raw_address in success_targets:
                    return {"status": "completed"}
                return {"status": "failed"}

            report = replay_failed_queue(queue_path, fake_runner, limit=10)
            self.assertEqual(report["replayed"], 2)
            self.assertEqual(report["recovered"], 1)

            remaining = load_failed_queue(queue_path)
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0]["raw_address"], "中山东一路1号")

    def test_build_line_feedback_payload_consumes_contract_refs(self):
        contract = {
            "required_fields": [
                "status",
                "done",
                "next",
                "blocker",
                "eta",
                "test_report_ref",
                "failure_queue_snapshot_ref",
                "replay_result_ref",
                "release_decision",
            ],
            "failure_queue_snapshot_ref": "sqlite://database/tc06_line_execution.db#failure_queue",
            "replay_result_ref": "sqlite://database/tc06_line_execution.db#replay_runs",
        }
        payload = build_line_feedback_payload(
            contract=contract,
            replay_report_ref="output/line_runs/tc06_failure_replay_2026-02-15_190000_000000.json",
            status="done",
        )

        self.assertEqual(payload["failure_queue_snapshot_ref"], contract["failure_queue_snapshot_ref"])
        self.assertEqual(payload["replay_result_ref"], contract["replay_result_ref"])
        self.assertEqual(payload["status"], "done")
        self.assertEqual(payload["release_decision"], "GO")

    def test_build_line_feedback_payload_accepts_pg_contract_refs(self):
        contract = {
            "required_fields": [
                "status",
                "done",
                "next",
                "blocker",
                "eta",
                "test_report_ref",
                "failure_queue_snapshot_ref",
                "replay_result_ref",
                "release_decision",
            ],
            "failure_queue_snapshot_ref": "pg://address_line.failure_queue",
            "replay_result_ref": "pg://address_line.replay_runs",
        }
        payload = build_line_feedback_payload(
            contract=contract,
            replay_report_ref="output/line_runs/tc06_failure_replay_2026-02-15_210327_583381.json",
            status="done",
        )
        self.assertEqual(payload["failure_queue_snapshot_ref"], contract["failure_queue_snapshot_ref"])
        self.assertEqual(payload["replay_result_ref"], contract["replay_result_ref"])


if __name__ == "__main__":
    unittest.main()
