import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.agent_runtime_store import AgentRuntimeStore
from tools.process_db_api import ProcessDBApi
from src.control_plane.services import ConfirmationWorkflowService, OperationAuditService, PublishService


class ControlPlaneServicesTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="cp_services_ut_")
        self.db_path = str(Path(self._tmpdir) / "agent_runtime.db")
        self.base_dir = str(Path(self._tmpdir) / "runtime_store")
        self.store = AgentRuntimeStore(db_path=self.db_path, base_dir=self.base_dir)
        self.drafts = {}
        self.db_api = ProcessDBApi(runtime_store=self.store, process_design_drafts=self.drafts)
        self.audit = OperationAuditService(runtime_store=self.store)
        self.publish = PublishService(runtime_store=self.store, process_db_api=self.db_api, process_design_drafts=self.drafts)
        self.confirm = ConfirmationWorkflowService(
            runtime_store=self.store,
            publish_service=self.publish,
            audit_service=self.audit,
            execute_intent_fn=lambda _intent, _params: {"status": "ok"},
            capture_pre_state_fn=lambda _intent, _params: {},
            record_iteration_event_fn=lambda _intent, _params, _result: None,
        )

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_create_pending_confirmation_also_writes_audit(self):
        out = self.confirm.create_pending_confirmation(
            session_id="sess_cp",
            intent="publish_draft",
            params={"draft_id": "draft_cp", "reason": "cp test"},
            expires_in_sec=600,
            source="cp_test",
        )
        self.assertEqual(out.get("status"), "pending_confirmation")
        cid = out.get("confirmation_id")
        self.assertTrue(str(cid).startswith("confirm_"))
        rec = self.store.get_confirmation_record(cid)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["confirmation_status"], "pending")

        audits = self.store.list_operation_audits(confirmation_id=cid, limit=10)
        self.assertTrue(len(audits) >= 1)
        self.assertEqual(audits[0]["operation_status"], "pending_confirmation")


if __name__ == "__main__":
    unittest.main()
