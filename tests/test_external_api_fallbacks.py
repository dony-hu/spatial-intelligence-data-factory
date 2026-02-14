import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.agent_runtime_store import AgentRuntimeStore
from tools.external_apis.review_platform import ReviewPlatformClient
from tools.external_apis.web_search import WebSearchClient


class ExternalAPIFallbackTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="ext_api_test_")
        self.db_path = str(Path(self._tmpdir) / "agent_runtime.db")
        self.base_dir = str(Path(self._tmpdir) / "runtime_store")
        self.store = AgentRuntimeStore(db_path=self.db_path, base_dir=self.base_dir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_web_search_fallback_returns_non_blocking_payload(self):
        client = WebSearchClient(runtime_store=self.store, config={})
        result = client.search_address_evidence(address="上海市浦东新区世纪大道100号", business_name="测试商户", limit=3)
        self.assertIn("found", result)
        self.assertIn("results", result)
        self.assertIsInstance(result["results"], list)

    def test_review_platform_fallback_returns_non_blocking_payload(self):
        client = ReviewPlatformClient(runtime_store=self.store, config={})
        result = client.query_business_info(
            business_name="测试商户",
            city="上海",
            address="上海市浦东新区世纪大道100号",
        )
        self.assertIn("found", result)
        self.assertIn("verification_source", result)
        self.assertEqual(result["verification_source"], "review_platform")


if __name__ == "__main__":
    unittest.main()
