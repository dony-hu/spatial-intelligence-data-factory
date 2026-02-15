from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestNextIterationGaps(unittest.TestCase):
    def test_write_intents_always_pending_confirmation(self) -> None:
        from tools.agent_server import WRITE_INTENTS

        self.assertIn("create_process", WRITE_INTENTS)
        self.assertIn("create_version", WRITE_INTENTS)
        self.assertIn("publish_draft", WRITE_INTENTS)

    def test_data_generation_tool_mapping_exists(self) -> None:
        from tools.process_compiler.tool_generator import ToolGenerator

        mapping = ToolGenerator.TOOL_GENERATORS
        self.assertIn("DATA_GENERATION", mapping)

    def test_output_persist_generator_uses_runtime_table_name(self) -> None:
        from tools.process_compiler.tool_templates.persisters import generate_db_persister

        result = generate_db_persister("address_governance", {"table_name": "x"})
        code = result["code"]
        self.assertIn("{self.table_name}", code)

    def test_authoritative_registry_missing_endpoint_degrades(self) -> None:
        from tools.address_verification import AddressVerificationOrchestrator, UNVERIFIABLE_ONLINE

        orchestrator = AddressVerificationOrchestrator()
        result = orchestrator.verify(
            record_id="r1",
            input_item={"raw": "上海市浦东新区世纪大道100号"},
            cleaning_output={"standardized_address": "上海市浦东新区世纪大道100号"},
        )

        self.assertIn("attempted_sources", result)
        self.assertTrue(any(item.get("source") == "authoritative_registry" for item in result["attempted_sources"]))
        self.assertIn(result["verification_status"], {UNVERIFIABLE_ONLINE, "VERIFIED_EXISTS", "VERIFIED_NOT_EXISTS"})


if __name__ == "__main__":
    unittest.main()
