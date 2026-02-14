import shutil
import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.agent_runtime_store import AgentRuntimeStore

if "tools.agent_cli" not in sys.modules:
    agent_cli_stub = types.ModuleType("tools.agent_cli")
    agent_cli_stub.load_config = lambda *_args, **_kwargs: {}
    agent_cli_stub.parse_plan_from_answer = lambda *_args, **_kwargs: {}
    agent_cli_stub.run_requirement_query = lambda *_args, **_kwargs: {"answer": ""}
    sys.modules["tools.agent_cli"] = agent_cli_stub

import tools.agent_server as agent_server
from tools.process_db_api import ProcessDBApi


class ProcessIterationEventTests(unittest.TestCase):
    def setUp(self):
        self.db_path = PROJECT_ROOT / "database" / "agent_runtime_iteration_test.db"
        self.base_dir = PROJECT_ROOT / "runtime_store_iteration_test"
        if self.db_path.exists():
            self.db_path.unlink()
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
        self.store = AgentRuntimeStore(db_path=str(self.db_path), base_dir=str(self.base_dir))

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)

    def test_record_and_list_iteration_event(self):
        proc = self.store.get_released_process("ADDR_GOVERNANCE")
        self.assertIsNotNone(proc)

        event_id = self.store.record_process_iteration_event(
            process_definition_id=str(proc["process_definition_id"]),
            from_version_id=str(proc["process_version_id"]),
            from_version=str(proc["version"]),
            to_version_id="procver_target",
            to_version="2.0.0",
            trigger_type="create_version",
            reason="unit-test",
            strategy_patch={"key": "value"},
        )
        self.assertTrue(event_id.startswith("iter_"))

        events = self.store.list_process_iteration_events(str(proc["process_definition_id"]), limit=10)
        self.assertGreaterEqual(len(events), 1)
        latest = events[0]
        self.assertEqual(latest["trigger_type"], "create_version")
        self.assertEqual(latest["from_version"], str(proc["version"]))
        self.assertEqual(latest["to_version"], "2.0.0")
        self.assertEqual(latest["reason"], "unit-test")
        self.assertEqual(latest["strategy_patch"].get("key"), "value")

    def test_agent_server_records_create_version_event(self):
        proc = self.store.get_released_process("ADDR_GOVERNANCE")
        self.assertIsNotNone(proc)
        process_definition_id = str(proc["process_definition_id"])

        next_patch = len(self.store.list_process_versions(process_definition_id)) + 10
        new_version = self.store.create_process_version(
            process_definition_id=process_definition_id,
            version=f"1.0.{next_patch}",
            goal="test",
            steps=[{"step_code": "S1", "name": "步骤1", "tool_name": "tool", "process_type": "自动化"}],
            publish=True,
            created_by="test_case",
            tool_bundle_version="bundle-address@1.0.2",
            engine_version="factory-engine@1.1.0",
            engine_compatibility={"min_engine_version": "1.0.0", "max_engine_version": "1.1.x"},
        )
        versions = self.store.list_process_versions(process_definition_id)
        self.assertEqual(versions[0]["tool_bundle_version"], "bundle-address@1.0.2")
        self.assertEqual(versions[0]["engine_version"], "factory-engine@1.1.0")
        self.assertEqual(versions[0]["engine_compatibility"]["max_engine_version"], "1.1.x")

        original_store = agent_server.runtime_store
        try:
            agent_server.runtime_store = self.store
            event_id = agent_server._record_iteration_event_if_needed(
                intent="create_version",
                params={
                    "process_definition_id": process_definition_id,
                    "reason": "create version by test",
                    "_from_version_id": str(proc["process_version_id"]),
                    "_from_version": str(proc["version"]),
                },
                tool_result={"status": "ok", "intent": "create_version", "process_version": new_version},
            )
        finally:
            agent_server.runtime_store = original_store

        self.assertIsNotNone(event_id)
        events = self.store.list_process_iteration_events(process_definition_id, limit=5, trigger_type="create_version")
        self.assertGreaterEqual(len(events), 1)
        latest = events[0]
        self.assertEqual(latest["from_version"], str(proc["version"]))
        self.assertEqual(latest["to_version"], str(new_version["version"]))
        self.assertEqual(latest["reason"], "create version by test")

    def test_agent_server_records_publish_draft_event(self):
        proc = self.store.get_released_process("ADDR_GOVERNANCE")
        self.assertIsNotNone(proc)
        process_definition_id = str(proc["process_definition_id"])

        original_store = agent_server.runtime_store
        try:
            agent_server.runtime_store = self.store
            event_id = agent_server._record_iteration_event_if_needed(
                intent="publish_draft",
                params={
                    "process_definition_id": process_definition_id,
                    "reason": "publish draft by test",
                    "_from_version_id": str(proc["process_version_id"]),
                    "_from_version": str(proc["version"]),
                },
                tool_result={
                    "status": "ok",
                    "intent": "publish_draft",
                    "process_version": {"id": "procver_publish_ut", "version": "2.0.0"},
                },
            )
        finally:
            agent_server.runtime_store = original_store

        self.assertIsNotNone(event_id)
        events = self.store.list_process_iteration_events(process_definition_id, limit=5, trigger_type="publish_draft")
        self.assertGreaterEqual(len(events), 1)
        latest = events[0]
        self.assertEqual(latest["from_version"], str(proc["version"]))
        self.assertEqual(latest["to_version"], "2.0.0")
        self.assertEqual(latest["reason"], "publish draft by test")

    def test_publish_draft_returns_publish_audit(self):
        draft_id = "draft_publish_audit_ut"
        self.store.upsert_process_draft(
            draft_id=draft_id,
            session_id="sess_audit",
            process_code="PROC_AUDIT_UT",
            process_name="audit ut",
            domain="address_governance",
            requirement="r",
            goal="g",
            plan={"k": "v"},
            process_doc_markdown="doc",
            llm_answer="ans",
            status="editable",
        )

        original_store = agent_server.runtime_store
        original_db_api = agent_server.process_db_api
        original_drafts = dict(agent_server.process_design_drafts)
        try:
            agent_server.runtime_store = self.store
            agent_server.process_design_drafts[draft_id] = {
                "draft_id": draft_id,
                "process_code": "PROC_AUDIT_UT",
                "process_name": "audit ut",
                "domain": "address_governance",
                "goal": "g",
                "requirement": "r",
                "plan": {"k": "v"},
            }
            agent_server.process_db_api = ProcessDBApi(
                runtime_store=self.store,
                process_design_drafts=agent_server.process_design_drafts,
            )
            result = agent_server._publish_draft(
                draft_id=draft_id,
                reason="audit reason",
                operator="ut_operator",
                source="ut_source",
            )
        finally:
            agent_server.runtime_store = original_store
            agent_server.process_db_api = original_db_api
            agent_server.process_design_drafts.clear()
            agent_server.process_design_drafts.update(original_drafts)

        self.assertEqual(result.get("status"), "ok")
        audit = result.get("publish_audit") or {}
        self.assertEqual(audit.get("operator"), "ut_operator")
        self.assertEqual(audit.get("source"), "ut_source")
        self.assertEqual(audit.get("reason"), "audit reason")

    def test_attach_publish_audit_with_confirmation_fields(self):
        base = {
            "status": "ok",
            "intent": "publish_draft",
            "draft_id": "draft_x",
            "process_version_id": "procver_x",
        }
        out = agent_server._attach_publish_audit(
            tool_result=base,
            draft_id="draft_x",
            reason="r",
            operator="op",
            source="src",
            confirmation_id="confirm_x",
            confirmer_user_id="u1",
            latency_ms=12,
        )
        audit = out.get("publish_audit") or {}
        self.assertEqual(audit.get("confirmation_id"), "confirm_x")
        self.assertEqual(audit.get("confirmer_user_id"), "u1")
        self.assertEqual(audit.get("latency_ms"), 12)


if __name__ == "__main__":
    unittest.main()
