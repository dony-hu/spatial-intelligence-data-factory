import tempfile
import unittest
from pathlib import Path

from scripts import run_p0_workpackage


class RunP0WorkpackageGateTests(unittest.TestCase):
    def test_compute_sha256(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir) / "a.json"
            p.write_text('{"k":"v"}\n', encoding="utf-8")
            digest = run_p0_workpackage._compute_sha256(p)
            self.assertEqual(len(digest), 64)
            self.assertTrue(all(c in "0123456789abcdef" for c in digest))

    def test_validate_line_feedback_hash_requires_match(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload = Path(tmp_dir) / "line_feedback.latest.json"
            payload.write_text('{"status":"done"}\n', encoding="utf-8")
            hash_file = Path(tmp_dir) / "line_feedback.latest.sha256"

            digest = run_p0_workpackage._compute_sha256(payload)
            hash_file.write_text(digest + "\n", encoding="utf-8")
            ok, details = run_p0_workpackage._validate_line_feedback_hash(payload, hash_file)
            self.assertTrue(ok)
            self.assertEqual(details["expected_sha256"], digest)
            self.assertEqual(details["actual_sha256"], digest)

            hash_file.write_text("0" * 64 + "\n", encoding="utf-8")
            ok, details = run_p0_workpackage._validate_line_feedback_hash(payload, hash_file)
            self.assertFalse(ok)
            self.assertNotEqual(details["expected_sha256"], details["actual_sha256"])

    def test_validate_sqlite_ref_requires_fixed_table(self):
        self.assertTrue(run_p0_workpackage._is_valid_sqlite_ref("sqlite://database/tc06_line_execution.db#failure_queue", "failure_queue"))
        self.assertTrue(run_p0_workpackage._is_valid_sqlite_ref("sqlite://database/tc06_line_execution.db#replay_runs", "replay_runs"))
        self.assertFalse(run_p0_workpackage._is_valid_sqlite_ref("sqlite://database/tc06_line_execution.db#unexpected", "replay_runs"))
        self.assertFalse(run_p0_workpackage._is_valid_sqlite_ref("file://database/tc06_line_execution.db#replay_runs", "replay_runs"))
        self.assertTrue(run_p0_workpackage._is_valid_pg_ref("pg://address_line.failure_queue", "failure_queue"))
        self.assertTrue(run_p0_workpackage._is_valid_pg_ref("pg://address_line.replay_runs", "replay_runs"))
        self.assertFalse(run_p0_workpackage._is_valid_pg_ref("pg://address_line.unknown", "replay_runs"))

    def test_validate_line_feedback_payload_requires_contract_match(self):
        payload = {
            "status": "done",
            "done": ["runtime_unify", "package_split", "r2_gate_closure"],
            "next": [],
            "blocker": "",
            "eta": "2026-02-15T19:00:00+08:00",
            "test_report_ref": "output/line_runs/tc06_failure_replay_2026-02-15_190000_000000.json",
            "failure_queue_snapshot_ref": "sqlite://database/tc06_line_execution.db#failure_queue",
            "replay_result_ref": "sqlite://database/tc06_line_execution.db#replay_runs",
            "release_decision": "GO",
        }
        required_fields = [
            "status",
            "done",
            "next",
            "blocker",
            "eta",
            "test_report_ref",
            "failure_queue_snapshot_ref",
            "replay_result_ref",
            "release_decision",
        ]
        ok, errors = run_p0_workpackage._validate_line_feedback_payload(
            payload,
            required_fields,
            expected_failure_ref="sqlite://database/tc06_line_execution.db#failure_queue",
            expected_replay_ref="sqlite://database/tc06_line_execution.db#replay_runs",
        )
        self.assertTrue(ok)
        self.assertEqual(errors, [])

        payload["replay_result_ref"] = "sqlite://database/tc06_line_execution.db#replay_run"
        ok, errors = run_p0_workpackage._validate_line_feedback_payload(
            payload,
            required_fields,
            expected_failure_ref="sqlite://database/tc06_line_execution.db#failure_queue",
            expected_replay_ref="sqlite://database/tc06_line_execution.db#replay_runs",
        )
        self.assertFalse(ok)
        self.assertTrue(errors)

    def test_validate_line_feedback_payload_accepts_pg_refs(self):
        payload = {
            "status": "done",
            "done": ["runtime_unify", "package_split", "r2_gate_closure"],
            "next": [],
            "blocker": "",
            "eta": "2026-02-15T19:00:00+08:00",
            "test_report_ref": "output/line_runs/tc06_failure_replay_2026-02-15_210327_583381.json",
            "failure_queue_snapshot_ref": "pg://address_line.failure_queue",
            "replay_result_ref": "pg://address_line.replay_runs",
            "release_decision": "GO",
        }
        required_fields = [
            "status",
            "done",
            "next",
            "blocker",
            "eta",
            "test_report_ref",
            "failure_queue_snapshot_ref",
            "replay_result_ref",
            "release_decision",
        ]
        ok, errors = run_p0_workpackage._validate_line_feedback_payload(
            payload,
            required_fields,
            expected_failure_ref="pg://address_line.failure_queue",
            expected_replay_ref="pg://address_line.replay_runs",
        )
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_validate_replay_store_requires_tables_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "tc06.db"
            with run_p0_workpackage.sqlite3.connect(str(db_path)) as conn:
                conn.execute("CREATE TABLE failure_queue (failure_id TEXT PRIMARY KEY)")
                conn.execute("CREATE TABLE replay_runs (replay_id TEXT PRIMARY KEY)")
                conn.commit()

            ok, details = run_p0_workpackage._validate_replay_store(
                "sqlite://" + str(db_path.relative_to(Path(tmp_dir).parent)) + "#failure_queue",
                "sqlite://" + str(db_path.relative_to(Path(tmp_dir).parent)) + "#replay_runs",
                project_root=Path(tmp_dir).parent,
            )
            self.assertFalse(ok)
            self.assertEqual(details["failure_queue_rows"], 0)
            self.assertEqual(details["replay_runs_rows"], 0)


if __name__ == "__main__":
    unittest.main()
