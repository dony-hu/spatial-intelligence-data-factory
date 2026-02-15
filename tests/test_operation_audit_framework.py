import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.agent_runtime_store import AgentRuntimeStore


class OperationAuditFrameworkTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="op_audit_ut_")
        self.db_path = str(Path(self._tmpdir) / "agent_runtime.db")
        self.base_dir = str(Path(self._tmpdir) / "runtime_store")
        self.store = AgentRuntimeStore(db_path=self.db_path, base_dir=self.base_dir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_list_confirmation_records_filters(self):
        c1 = self.store.create_confirmation_record(
            session_id="sess_1",
            operation_type="publish_draft",
            operation_params={"draft_id": "d1"},
            draft_id="d1",
        )
        c2 = self.store.create_confirmation_record(
            session_id="sess_2",
            operation_type="create_version",
            operation_params={"process_definition_id": "p1"},
        )
        self.store.update_confirmation_status(c1, "confirmed", "u1")
        self.store.update_confirmation_status(c2, "rejected", "u2")

        confirmed = self.store.list_confirmation_records(confirmation_status="confirmed", limit=20)
        rejected = self.store.list_confirmation_records(confirmation_status="rejected", limit=20)
        publish = self.store.list_confirmation_records(operation_type="publish_draft", limit=20)

        self.assertTrue(any(x["confirmation_id"] == c1 for x in confirmed))
        self.assertTrue(any(x["confirmation_id"] == c2 for x in rejected))
        self.assertTrue(any(x["confirmation_id"] == c1 for x in publish))

    def test_log_and_list_operation_audit(self):
        aid1 = self.store.log_operation_audit(
            operation_type="publish_draft",
            operation_status="ok",
            actor="u1",
            source="console",
            confirmation_id="confirm_1",
            confirmer_user_id="u1",
            draft_id="d1",
            process_definition_id="procdef_1",
            process_version_id="procver_1",
            detail={"k": "v"},
        )
        aid2 = self.store.log_operation_audit(
            operation_type="publish_draft",
            operation_status="rejected",
            actor="u2",
            source="confirmation_endpoint",
            confirmation_id="confirm_2",
            confirmer_user_id="u2",
            draft_id="d2",
            detail={"reason": "manual reject"},
        )

        self.assertTrue(aid1.startswith("audit_"))
        self.assertTrue(aid2.startswith("audit_"))

        only_ok = self.store.list_operation_audits(operation_type="publish_draft", operation_status="ok", limit=20)
        by_confirm = self.store.list_operation_audits(confirmation_id="confirm_2", limit=20)

        self.assertEqual(len(only_ok), 1)
        self.assertEqual(only_ok[0]["operation_status"], "ok")
        self.assertEqual(only_ok[0]["detail"].get("k"), "v")
        self.assertEqual(len(by_confirm), 1)
        self.assertEqual(by_confirm[0]["confirmer_user_id"], "u2")

    def test_bulk_update_confirmation_status(self):
        c1 = self.store.create_confirmation_record(
            session_id="sess_b1",
            operation_type="publish_draft",
            operation_params={"draft_id": "d1"},
        )
        c2 = self.store.create_confirmation_record(
            session_id="sess_b2",
            operation_type="publish_draft",
            operation_params={"draft_id": "d2"},
        )
        affected = self.store.bulk_update_confirmation_status([c1, c2], "rejected", "batch_user")
        self.assertEqual(affected, 2)
        r1 = self.store.get_confirmation_record(c1)
        r2 = self.store.get_confirmation_record(c2)
        self.assertEqual(r1["confirmation_status"], "rejected")
        self.assertEqual(r2["confirmation_status"], "rejected")
        self.assertEqual(r1["confirmer_user_id"], "batch_user")

    def test_expire_pending_confirmations(self):
        expired_ts = (datetime.now() - timedelta(seconds=60)).isoformat()
        future_ts = (datetime.now() + timedelta(seconds=3600)).isoformat()
        c1 = self.store.create_confirmation_record(
            session_id="sess_e1",
            operation_type="publish_draft",
            operation_params={"draft_id": "d1"},
            expires_at=expired_ts,
        )
        _ = self.store.create_confirmation_record(
            session_id="sess_e2",
            operation_type="publish_draft",
            operation_params={"draft_id": "d2"},
            expires_at=future_ts,
        )
        affected = self.store.expire_pending_confirmations()
        self.assertEqual(affected, 1)
        r1 = self.store.get_confirmation_record(c1)
        self.assertEqual(r1["confirmation_status"], "expired")


if __name__ == "__main__":
    unittest.main()
