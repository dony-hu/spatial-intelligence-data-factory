import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.agent_runtime_store import AgentRuntimeStore


class ProcessDraftListingTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="draft_list_ut_")
        self.db_path = str(Path(self._tmpdir) / "agent_runtime.db")
        self.base_dir = str(Path(self._tmpdir) / "runtime_store")
        self.store = AgentRuntimeStore(db_path=self.db_path, base_dir=self.base_dir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_list_process_drafts_with_status_filter(self):
        self.store.upsert_process_draft(
            draft_id="draft_ut_1",
            session_id="sess_1",
            process_code="PROC_UT_1",
            process_name="ut1",
            domain="address_governance",
            requirement="r1",
            goal="g1",
            plan={"a": 1},
            process_doc_markdown="doc1",
            llm_answer="ans1",
            status="editable",
        )
        self.store.upsert_process_draft(
            draft_id="draft_ut_2",
            session_id="sess_2",
            process_code="PROC_UT_2",
            process_name="ut2",
            domain="address_governance",
            requirement="r2",
            goal="g2",
            plan={"a": 2},
            process_doc_markdown="doc2",
            llm_answer="ans2",
            status="published",
        )

        editable = self.store.list_process_drafts(status="editable", limit=20)
        published = self.store.list_process_drafts(status="published", limit=20)
        all_items = self.store.list_process_drafts(limit=20)

        self.assertEqual(len(editable), 1)
        self.assertEqual(editable[0]["draft_id"], "draft_ut_1")
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]["draft_id"], "draft_ut_2")
        self.assertGreaterEqual(len(all_items), 2)


if __name__ == "__main__":
    unittest.main()
